from __future__ import annotations

import io
import json
import os
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import sleep
from typing import Iterable, List, Optional
from urllib.parse import urlparse

import boto3

# Small replacements to normalize transcript wording (carried from callan-transcribe)
_REPLACE_LIST = [
    ("Less than", "Lesson"),
    ("less than", "Lesson"),
    ("et cetera", "etc"),
    ("etcetera", "etc"),
]


def list_s3_objects(bucket: str, prefix: str, *, s3_client=None) -> List[str]:
    s3 = s3_client or boto3.client("s3")
    resp = s3.list_objects(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents", [])
    return [f"s3://{bucket}/{obj['Key']}" for obj in contents if obj["Key"] != prefix]


def upload_file(bucket: str, prefix: str, filename: str, *, s3_client=None) -> str:
    if not os.path.exists(filename):
        raise FileNotFoundError(filename)
    basename = os.path.basename(filename)
    s3 = s3_client or boto3.client("s3")
    key = os.path.join(prefix, basename)
    s3.upload_file(filename, bucket, key)
    return key


def delete_file(bucket: str, prefix: str, filename: str, *, s3_client=None) -> None:
    s3 = s3_client or boto3.client("s3")
    s3.delete_object(Bucket=bucket, Key=os.path.join(prefix, filename))


def _encode_filename(filename: str) -> str:
    replacer = lambda match: hex(ord(match.group(0)))[2:]
    return re.sub(r"[^0-9a-zA-Z._-]", replacer, filename)


def start_transcription_job(
    *,
    job_name: str,
    languages: Iterable[str],
    media_file_uri: str,
    media_format: str,
    output_bucket: str,
    output_key_prefix: str,
    region: str,
    transcribe_client=None,
):
    client = transcribe_client or boto3.client("transcribe", region_name=region)
    languages = list(languages)
    kwargs = {
        "TranscriptionJobName": job_name,
        "MediaFormat": media_format,
        "Media": {"MediaFileUri": media_file_uri},
        "OutputBucketName": output_bucket,
        "OutputKey": output_key_prefix,
        "Settings": {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 2,
        },
    }
    if len(languages) == 1:
        kwargs["LanguageCode"] = languages[0]
    elif len(languages) >= 2:
        kwargs["IdentifyMultipleLanguages"] = True
        kwargs["LanguageOptions"] = languages

    return client.start_transcription_job(**kwargs)


def wait_for_job(job_name: str, *, region: str, wait_seconds: int = 5, transcribe_client=None):
    client = transcribe_client or boto3.client("transcribe", region_name=region)
    while True:
        resp = client.get_transcription_job(TranscriptionJobName=job_name)
        status = resp["TranscriptionJob"]["TranscriptionJobStatus"]
        if status == "COMPLETED":
            client.delete_transcription_job(TranscriptionJobName=job_name)
            return resp
        if status == "FAILED":
            raise RuntimeError(f"Transcription job failed: {resp['TranscriptionJob'].get('FailureReason')}")
        sleep(wait_seconds)


def fetch_transcript(transcript_uri: str, *, s3_client=None) -> dict:
    s3 = s3_client or boto3.client("s3")
    path_components = urlparse(transcript_uri).path.split("/")
    bucket = path_components[1]
    transcript_path = "/".join(path_components[2:])

    with io.BytesIO() as buf:
        s3.download_fileobj(bucket, transcript_path, buf)
        return json.loads(buf.getvalue().decode("utf-8"))


def _make_items_dict(data: dict) -> dict:
    items_dict = {}
    for item in data["results"]["items"]:
        if item["type"] == "punctuation":
            # append punctuation to previous token content
            punctuation = item["alternatives"][0]["content"]
            if not items_dict:
                continue
            last_key = list(items_dict.keys())[-1]
            items_dict[last_key]["content"] = items_dict[last_key]["content"] + punctuation
        else:
            start_time = item["start_time"]
            contents = [alt["content"] for alt in item["alternatives"]]
            item["content"] = " ".join(contents)
            items_dict[start_time] = item
    return items_dict


def _get_segment_content_from_items(segment: dict, items: dict) -> str:
    contents = [items[itm["start_time"]]["content"] for itm in segment["items"]]
    content = " ".join(contents)
    for src, dst in _REPLACE_LIST:
        content = content.replace(src, dst)
    return content


def prepare_segments(data: dict) -> List[dict]:
    items = _make_items_dict(data)
    segments = deepcopy(data["results"]["speaker_labels"]["segments"])

    speakers = Counter()
    for seg in segments:
        speakers[seg["speaker_label"]] += 1
    labels = list(speakers.keys())
    if not labels:
        return []
    teacher = labels[0]
    student = labels[1] if len(labels) > 1 else labels[0]

    prev_teacher_seg = None
    for seg in segments:
        content = _get_segment_content_from_items(seg, items)
        seg["content"] = content
        seg["speaker_label"] = "teacher" if seg["speaker_label"] == teacher else "student"
        seg.pop("items", None)

        if seg["speaker_label"] == "student":
            if len(content.split()) >= 3:
                if prev_teacher_seg is not None:
                    if "QnA" not in prev_teacher_seg:
                        prev_teacher_seg["QnA"] = prev_teacher_seg["content"] + " := " + content
                    else:
                        prev_teacher_seg["QnA"] = prev_teacher_seg["QnA"] + content
        else:
            prev_teacher_seg = seg
    return segments


def print_segments(segments: List[dict]) -> str:
    if not segments:
        return ""
    lines = ["# " + segments[0]["content"]]
    queue: List[str] = []

    for seg in segments[1:]:
        if "QnA" in seg:
            if queue:
                lines.append("# " + ", ".join(queue))
                queue.clear()
            lines.append(seg["QnA"])
        elif seg["speaker_label"] == "teacher" or len(seg["content"].split()) < 3:
            queue.append(seg["content"].rstrip(".,?"))

    if queue:
        lines.append("# " + ", ".join(queue))
    return "\n".join(lines)


def _stitch_multi_language_items(items: List[dict]) -> str:
    text_parts: List[str] = []
    current_lang: Optional[str] = None
    buffer: List[str] = []

    for item in items:
        lang = item.get("language_code")
        if lang != current_lang:
            if buffer:
                text_parts.append("".join(buffer))
                buffer = []
            current_lang = lang
        for alt in item.get("alternatives", []):
            token = alt.get("content", "")
            if lang not in ("ja-JP", "ko-KR", "zh-CN") and item.get("type") == "pronunciation" and buffer:
                buffer.append(" ")
            buffer.append(token)
    if buffer:
        text_parts.append("".join(buffer))
    return "\n".join(text_parts)


def transcribe_s3_object(
    *,
    bucket: str,
    prefix: str,
    object_name: str,
    languages: Iterable[str],
    media_format: str,
    region: str = "ap-northeast-1",
    wait_seconds: int = 5,
    transcribe_client=None,
    s3_client=None,
) -> str:
    languages = [lang.strip() for lang in languages if lang.strip()]
    output_prefix = f"{prefix.rstrip('/')}-transcript/"
    media_file = f"s3://{bucket}/{prefix}/{object_name}"
    job_name = "transcribe-job-" + _encode_filename(object_name.replace(" ", "_"))

    start_transcription_job(
        job_name=job_name,
        languages=languages,
        media_file_uri=media_file,
        media_format=media_format,
        output_bucket=bucket,
        output_key_prefix=output_prefix,
        region=region,
        transcribe_client=transcribe_client,
    )

    resp = wait_for_job(job_name, region=region, wait_seconds=wait_seconds, transcribe_client=transcribe_client)
    transcript_uri = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

    transcript_data = fetch_transcript(transcript_uri, s3_client=s3_client)
    if len(languages) == 1:
        scripts = transcript_data.get("results", {}).get("transcripts", [])
        return "\n".join(script.get("transcript", "") for script in scripts)

    items = transcript_data.get("results", {}).get("items", [])
    return _stitch_multi_language_items(items)
