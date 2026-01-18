import boto3
from openai import OpenAI
import os
import random
import io
from contextlib import closing
from pydub import AudioSegment

POLLY_MAX_CHARS = 1000  # Max characters per chunk for Amazon Polly


def _split_text_into_chunks(text, max_chars):
    """Split text into <max_chars chunks; naive sentence-aware split for JP/EN."""
    chunks = []
    current_chunk = ""
    sentences = text.replace("！", "!").replace("？", "?").split(".")
    for sentence in sentences:
        if not sentence:
            continue
        sentence = sentence.strip()
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += sentence + "."
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + "."
            while len(current_chunk) > max_chars:
                chunks.append(current_chunk[:max_chars])
                current_chunk = current_chunk[max_chars:]
    if current_chunk:
        chunks.append(current_chunk.strip())
    return [c for c in chunks if c]


class AmazonPollyEngine(object):
    EXCLUDE_VOICES = ("Ivy", "Justin", "Kevin", "Matthew")

    def __init__(self, engine="neural"):
        self.polly = boto3.client("polly")
        self.engine = engine

    def text_to_audio(self, text, lang, voice, speed=None):
        if speed:
            speed = self._convert_to_percentage(speed)
            text = f'<speak><prosody rate="{speed}">{text}</prosody></speak>'
            text_type = "ssml"
        else:
            text_type = "text"
        resp = self.polly.synthesize_speech(
            Engine=self.engine,
            LanguageCode=lang,
            OutputFormat="mp3",
            Text=text,
            TextType=text_type,
            VoiceId=voice,
        )
        with closing(resp["AudioStream"]) as stream:
            audio_content = stream.read()
        return AudioSegment.from_file(io.BytesIO(audio_content), format="mp3")

    def get_speakers(self, lang):
        resp = self.polly.describe_voices(Engine=self.engine, LanguageCode=lang)
        voices = [voice["Name"] for voice in resp["Voices"]]
        voices = list(filter(lambda v: v not in self.EXCLUDE_VOICES, voices))
        random.shuffle(voices)
        return voices

    @staticmethod
    def _convert_to_percentage(value):
        """
        Converts any decimal value between 0 and 1 to a percentage string.
        """
        try:
            float_value = float(value)
            if 0 <= float_value <= 1:
                percentage = int(float_value * 100)
                return f"{percentage}%"
            return value
        except ValueError:
            return value


class OpenAISpeechEngine(object):
    def __init__(self, engine="tts-1"):
        self.engine = engine
        self.openai = OpenAI()

    def text_to_audio(self, text, lang, voice, speed=None):
        if speed and isinstance(speed, str):
            try:
                speed = float(speed)
            except ValueError:
                speed = None
        response = self.openai.audio.speech.create(
            model=self.engine,
            input=text,
            voice=voice,
            response_format="mp3",
            speed=speed or 1.0,
        )

        audio_content = io.BytesIO(response.content)
        return AudioSegment.from_file(audio_content, format="mp3")

    def get_speakers(self, lang):
        return [
            "alloy",
            "ash",
            "coral",
            "echo",
            "fable",
            "onyx",
            "nova",
            "sage",
            "shimmer",
        ]


def init_tts_engine(engine):
    if engine in ("standard", "neural", "long-form", "generative"):
        return AmazonPollyEngine(engine)
    if engine.startswith("openai-") and engine.split("-", maxsplit=1)[1] in (
        "tts-1",
        "tts-1-hd",
        "gpt-4o-mini-tts",
    ):
        engine = engine.split("-", maxsplit=1)[1]
        return OpenAISpeechEngine(engine)
    raise ValueError(f'Invalid engine: "{engine}"')


class SimpleTTS(object):
    def __init__(self, lang, speaker=None, engine="neural"):
        self.engine = init_tts_engine(engine)
        self.lang = lang
        if speaker:
            self.speaker = speaker
        else:
            self.speaker = self.engine.get_speakers(lang)[0]

    def make_audio_file(self, text, output_filename, speed=None, gain=0.0):
        if os.path.exists(output_filename):
            print('Skip existing file "{}"'.format(output_filename))
            return
        parent_dir = os.path.dirname(output_filename)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        text_chunks = _split_text_into_chunks(text, POLLY_MAX_CHARS)

        combined_audio = AudioSegment.empty()
        for i, chunk in enumerate(text_chunks):
            print(
                f"Synthesizing chunk {i+1}/{len(text_chunks)} for '{os.path.basename(output_filename)}'"
            )
            audio_segment = self.engine.text_to_audio(chunk, self.lang, self.speaker, speed)
            combined_audio += audio_segment

def list_speakers(lang, engine):
    tts_engine = init_tts_engine(engine)
    speakers = tts_engine.get_speakers(lang)
    return speakers


def synthesize_speech(lang, speaker, input_file, output_file, engine=None, speed=None, gain=0.0):
    with open(input_file, "r") as f:
        text = ""
        for line in f.readlines():
            if line.strip().startswith("#"):
                continue
            text += line
    SimpleTTS(lang, speaker, engine or "neural").make_audio_file(text, output_file, speed, gain)
