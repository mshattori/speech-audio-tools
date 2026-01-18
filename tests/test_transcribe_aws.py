from pathlib import Path
from unittest import mock

import pytest

from speech_audio_tools import transcribe_aws as ta


def _fake_items():
    return [
        {"start_time": "0.0", "type": "pronunciation", "alternatives": [{"content": "Hello"}], "language_code": "en-US"},
        {"type": "punctuation", "alternatives": [{"content": ","}]},
        {"start_time": "1.0", "type": "pronunciation", "alternatives": [{"content": "世界"}], "language_code": "ja-JP"},
    ]


def test_stitch_multi_language_items():
    text = ta._stitch_multi_language_items(_fake_items())
    assert "Hello" in text
    assert "世界" in text


def test_prepare_segments_handles_empty_labels():
    data = {
        "results": {
            "speaker_labels": {"segments": []},
            "items": [],
        }
    }
    assert ta.prepare_segments(data) == []


def test_list_s3_objects_happy_path():
    fake_client = mock.MagicMock()
    fake_client.list_objects.return_value = {
        "Contents": [
            {"Key": "prefix/"},
            {"Key": "prefix/file.mp3"},
        ]
    }
    objs = ta.list_s3_objects("bucket", "prefix/", s3_client=fake_client)
    assert objs == ["s3://bucket/prefix/file.mp3"]


@pytest.mark.parametrize("languages,expected_multi", [(["en-US"], False), (["en-US", "ja-JP"], True)])
@mock.patch("speech_audio_tools.transcribe_aws.wait_for_job")
@mock.patch("speech_audio_tools.transcribe_aws.start_transcription_job")
@mock.patch("speech_audio_tools.transcribe_aws.fetch_transcript")
@mock.patch("speech_audio_tools.transcribe_aws.boto3")
@mock.patch("speech_audio_tools.transcribe_aws._stitch_multi_language_items")
@mock.patch("speech_audio_tools.transcribe_aws._encode_filename", return_value="job")
def test_transcribe_s3_object_calls(mock_encode, mock_stitch, mock_boto3, mock_fetch, mock_start, mock_wait, languages, expected_multi):
    mock_wait.return_value = {"TranscriptionJob": {"Transcript": {"TranscriptFileUri": "s3://b/out.json"}}}
    mock_fetch.return_value = {
        "results": {
            "transcripts": [{"transcript": "mono"}],
            "items": _fake_items(),
        }
    }
    ta.transcribe_s3_object(
        bucket="b",
        prefix="p",
        object_name="f.mp3",
        languages=languages,
        media_format="mp3",
    )

    mock_start.assert_called_once()
    mock_wait.assert_called_once()
    mock_fetch.assert_called_once()
    if expected_multi:
        mock_stitch.assert_called_once()
    else:
        mock_stitch.assert_not_called()
