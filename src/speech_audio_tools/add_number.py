import os
import sys
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2
from .audio import _make_number_audio


def process_audio_files(input_dir, output_dir):
    audio_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".mp3")])
    number = 1
    for file in audio_files:
        file_path = os.path.join(input_dir, file)
        number_filename = _make_number_audio(number)
        number_audio_segment = AudioSegment.from_file(number_filename)
        pause = AudioSegment.silent(duration=500)
        original_audio = AudioSegment.from_file(file_path)
        combined_audio = number_audio_segment + pause + original_audio
        audio_file = MP3(file_path, ID3=ID3)
        if audio_file.tags is None:
            audio_file.add_tags()
        original_title = audio_file.tags.get("TIT2")
        new_title = f"{number:02d} {original_title.text[0]}" if original_title else f"{number:02d} Unknown Title"
        audio_file.tags["TIT2"] = TIT2(encoding=3, text=new_title)
        tag_dict = {tag.FrameID: tag.text[0] for tag in audio_file.tags.values()}
        file_path_out = os.path.join(output_dir, file)
        combined_audio.export(file_path_out, format="mp3", tags=tag_dict, id3v2_version="3")
        print(f"Created {file_path_out}")
        number += 1

