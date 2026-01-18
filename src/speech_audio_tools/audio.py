import os
import re
from glob import glob
import json
import hashlib
from pydub import AudioSegment
from collections import OrderedDict

PARENT_DIR = os.path.dirname(os.path.realpath(__file__))
# Pre-bundled number audio lives in-package under number_audio (1-100).
NUMBER_AUDIO_DIR = os.path.join(PARENT_DIR, "number_audio")
NUMBER_AUDIO_MAX_BUILTIN = 100


def speed_change(sound, speed=1.0):
    """Adjust playback speed while keeping frame_rate consistent."""
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={"frame_rate": int(sound.frame_rate * speed)})
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)


def speed_change_file(file_path, speed=1.0):
    sound = AudioSegment.from_file(file_path, "mp3")
    sound = speed_change(sound, speed)
    sound.export(file_path, format="mp3")


def _combine_QA(file_Q, file_A, speed, repeat_question, pause_duration=500, end_duration=2000):
    seg_Q = AudioSegment.from_file(file_Q, "mp3")
    seg_A = AudioSegment.from_file(file_A, "mp3")
    pause = AudioSegment.silent(duration=pause_duration)
    if speed[0] != 1.0:
        seg_Q = speed_change(seg_Q, speed[0])
    if speed[1] != 1.0:
        seg_A = speed_change(seg_A, speed[1])
    seg = seg_Q
    if repeat_question:
        seg += pause + seg_Q
    seg += pause + seg_A + AudioSegment.silent(duration=end_duration)
    return seg


def _collect_ordinal_numbers(input_directory):
    """parse filenames '<number>-Q-<voice>.mp3' in a directory and collect 'number's."""
    numbers_set = set()
    for question_file in glob(os.path.join(input_directory, "*-Q-*.mp3")):
        number_match_pattern = os.path.join(input_directory, r"(\d+)-Q-(.+).mp3")
        m = re.match(number_match_pattern, question_file)
        if not m:
            print("WARN: Unexpected file", question_file)
            continue
        numbers_set.add(m.group(1))
    return sorted(list(numbers_set))


def _find_mp3_file(input_directory, number, pattern):
    glob_pattern = os.path.join(input_directory, number + pattern + ".mp3")
    files = glob(glob_pattern)
    if len(files) < 1:
        return None
    return files[0]


def _find_question_file(input_directory, number):
    return _find_mp3_file(input_directory, number, "-Q-*")


def _find_answer_file(input_directory, number):
    return _find_mp3_file(input_directory, number, "-A-*")


def _combine_audio_list(audio_list):
    seg = AudioSegment.empty()
    for a in audio_list:
        seg = seg + a
    return seg


def _make_number_audio(number):
    from .tts import SimpleTTS

    lang = "en-US"
    number = int(number)
    if number < 1:
        raise ValueError("Number audio is defined for positive integers.")

    os.makedirs(NUMBER_AUDIO_DIR, exist_ok=True)
    filename = os.path.join(NUMBER_AUDIO_DIR, f"{number}.mp3")

    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        # Ship 1-100 with the package; synthesize anything missing (including >100) on the fly.
        SimpleTTS(lang).make_audio_file(str(number), filename)
    return filename


def make_section_mp3_files(
    input_directory,
    output_directory,
    speed=(1.0, 1.0),
    gain=0.0,
    repeat_question=True,
    pause_duration=500,
    add_number_audio=False,
    section_unit=10,
    artist="Homebrew",
):
    """Make section mp3 files by combining raw Q & A mp3 files made by TTS."""
    signatures = SignatureList(output_directory)
    numbers = _collect_ordinal_numbers(input_directory)

    # separate numbers into sections
    for i in range(0, len(numbers), section_unit):
        numbers_in_section = numbers[i : i + section_unit]
        start, end = numbers_in_section[0], numbers_in_section[-1]
        section_filename = os.path.join(output_directory, "{}-{}.mp3".format(start, end))
        section_audio_QA_files = []
        section_audio_files = []
        for number in numbers_in_section:
            file_Q = _find_question_file(input_directory, number)
            file_A = _find_answer_file(input_directory, number)
            if not (file_Q and file_A):
                print("WARN: Corresponding files not found for ", number)
                continue
            section_audio_QA_files.append((file_Q, file_A))
            section_audio_files.extend([file_Q, file_A])
        section_updated = signatures.updated(section_filename, section_audio_files)
        if os.path.exists(section_filename):
            if section_updated:
                print(f"Removing outdated file: {section_filename}")
                os.remove(section_filename)
            else:
                continue
        section_audio_segments = []
        if add_number_audio:
            os.makedirs(NUMBER_AUDIO_DIR, exist_ok=True)
            number = int(start)
            number_filename = _make_number_audio(number)
            number_audio = AudioSegment.from_file(number_filename)
            pause = AudioSegment.silent(duration=500)
            section_audio_segments.append(number_audio + pause)
        for (file_Q, file_A) in section_audio_QA_files:
            file_QA = _combine_QA(file_Q, file_A, speed, repeat_question, pause_duration)
            section_audio_segments.append(file_QA)

        if not section_audio_segments:
            continue

        section_audio = _combine_audio_list(section_audio_segments)
        if gain != 0.0:
            section_audio = section_audio.apply_gain(gain)
        album = os.path.basename(output_directory).replace("_", " ").replace("-", " ").title()
        tags = {"title": "{}-{} {}".format(start, end, album), "album": album, "artist": artist}
        section_audio.export(section_filename, format="mp3", tags=tags, id3v2_version="3")
        print('Created "{}"'.format(section_filename))

        cleanup_glob_pattern = os.path.join(output_directory, "{}-*.mp3".format(start))
        for target_file in glob(cleanup_glob_pattern):
            if target_file != section_filename:
                os.remove(target_file)
                print('Removed "{}"'.format(target_file))
    signatures.save()


def join_files(filenames, output_filename, title, album, artist, silence):
    silent_segment = None
    if silence > 0:
        silent_segment = AudioSegment.silent(duration=silence)

    audio_segments = []
    for file in filenames:
        print(file)
        audio_segments.append(AudioSegment.from_file(file))
        if os.path.splitext(file)[0].endswith("+"):
            continue
        if silent_segment:
            audio_segments.append(silent_segment)

    audio = _combine_audio_list(audio_segments)
    tags = {"title": title, "album": album, "artist": artist}
    audio.export(output_filename, format="mp3", tags=tags, id3v2_version="3")


class SignatureList:
    _SIGNATURE_FILENAME = ".signatures.json"

    def __init__(self, output_dir):
        self.signature_filename = os.path.join(output_dir, self._SIGNATURE_FILENAME)
        if os.path.exists(self.signature_filename):
            with open(self.signature_filename) as f:
                self.signatures_dict = json.load(f)
        else:
            self.signatures_dict = {}

    def updated(self, filename, content_files):
        filename = os.path.basename(filename)
        signature = self._calc_signature(content_files)
        if filename in self.signatures_dict:
            if self.signatures_dict[filename] == signature:
                return False
        self.signatures_dict[filename] = signature
        return True

    def save(self):
        with open(self.signature_filename, "w") as f:
            json.dump(self.signatures_dict, f, indent=4)

    @staticmethod
    def _calc_signature(file_list):
        hasher = hashlib.md5()
        for file_name in file_list:
            with open(file_name, "rb") as file:
                while True:
                    buf = file.read(1024)
                    if not buf:
                        break
                    hasher.update(buf)
        return hasher.hexdigest()
