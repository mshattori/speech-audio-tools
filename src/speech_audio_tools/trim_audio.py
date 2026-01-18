import os
from pydub import AudioSegment


def clip_audio(input_file, output_file, offset, tail_offset):
    """Clip an audio file by removing parts from the beginning and end."""
    audio = AudioSegment.from_file(input_file)
    if offset > 0:
        audio = audio[offset:]
    if tail_offset > 0:
        audio = audio[:-tail_offset]
    audio.export(output_file, format="mp3")

