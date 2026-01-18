import os
import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence


def split_by_silence(input_file, output_dir, min_silence_len, silence_thresh, album=None, title_prefix=None):
    """Split audio into chunks by silence."""
    os.makedirs(output_dir, exist_ok=True)
    audio = AudioSegment.from_file(input_file)
    audio_chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=True,
    )
    stemname = os.path.splitext(os.path.basename(input_file))[0]
    padding = len(str(len(audio_chunks)))
    outputs = []
    for index, chunk in enumerate(audio_chunks):
        if title_prefix:
            title = f"{title_prefix}-{index+1:0{padding}d}"
        else:
            title = f"{stemname}-{index+1:0{padding}d}"
        output_filename = os.path.join(output_dir, f"{title}.mp3")
        tags = {"title": title, "album": album, "artist": "Homebrew"}
        chunk.export(output_filename, format="mp3", tags=tags, id3v2_version="3")
        outputs.append(output_filename)
        print(f"Created {output_filename}")
    return outputs


def split_by_duration(input_file, segment_minutes, output_dir, overlap=5, album=None, title_prefix=None):
    """Split audio into fixed-length chunks (minutes)."""
    if segment_minutes <= 0:
        raise ValueError("Segment length must be greater than zero minutes.")
    if overlap < 0:
        raise ValueError("Overlap must be non-negative.")
    os.makedirs(output_dir, exist_ok=True)
    audio = AudioSegment.from_file(input_file)
    segment_duration_ms = segment_minutes * 60 * 1000
    overlap_ms = overlap * 1000
    total_segments = 1
    temp_start = 0
    while temp_start < len(audio):
        temp_start += segment_duration_ms - overlap_ms
        if temp_start < len(audio):
            total_segments += 1
    padding = len(str(total_segments))
    stemname = os.path.splitext(os.path.basename(input_file))[0]
    start_ms = 0
    index = 1
    outputs = []
    while start_ms < len(audio):
        end_ms = min(start_ms + segment_duration_ms, len(audio))
        segment = audio[start_ms:end_ms]
        if title_prefix:
            title = f"{title_prefix}-{index:0{padding}d}"
        else:
            title = f"{stemname}-{index:0{padding}d}"
        output_filename = os.path.join(output_dir, f"{title}.mp3")
        tags = {"title": title, "album": album, "artist": "Homebrew"}
        segment.export(output_filename, format="mp3", tags=tags, id3v2_version="3")
        print(f"Created {output_filename}: start={start_ms}, end={end_ms}")
        outputs.append(output_filename)
        start_ms += segment_duration_ms - overlap_ms
        index += 1
    return outputs

