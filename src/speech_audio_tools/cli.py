from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, List

import typer
from dotenv import load_dotenv

from . import __version__
from .tts import list_speakers, synthesize_speech
from .audio import make_section_mp3_files, join_files
from .change_speed import process_speed
from .split_audio import split_by_silence, split_by_duration
from .trim_audio import clip_audio
from .trim_silence import trim_with_ffmpeg
from .add_number import process_audio_files
from .tag_album import tag_album
from .beep import make_beep
from .transcribe_openai import DEFAULT_MODEL as OPENAI_DEFAULT_MODEL, transcribe_file
from .transcribe_aws import (
    list_s3_objects,
    upload_file,
    delete_file,
    transcribe_s3_object,
)


app = typer.Typer(help="Speech & audio utilities (TTS + post-processing).", add_completion=False)
tts_app = typer.Typer(help="Text-to-speech helpers.")
audio_app = typer.Typer(help="Audio processing helpers.")
transcribe_app = typer.Typer(help="Speech-to-text helpers (OpenAI/AWS).")

app.add_typer(tts_app, name="tts")
app.add_typer(audio_app, name="audio")
app.add_typer(transcribe_app, name="transcribe")


def _parse_speed_pair(speed_str: str) -> Tuple[float, float]:
    if ":" in speed_str:
        left, right = speed_str.split(":")
        return float(left), float(right)
    value = float(speed_str)
    return value, value


#
# TTS commands
#
@tts_app.command("speakers")
def tts_speakers(
    lang: str = typer.Option(..., "--lang", "-l", help="Language code, e.g., en-US"),
    engine: str = typer.Option("neural", "--engine", help="Engine name (neural, long-form, openai-tts-1, etc.)"),
    env_file: Path = typer.Option(".env", "--env-file", exists=False, help="Environment file to load"),
):
    load_dotenv(env_file, override=True)
    speakers = list_speakers(lang, engine)
    for s in speakers:
        typer.echo(s)


@tts_app.command("synthesize")
def tts_synthesize(
    lang: str = typer.Option(..., "--lang", "-l"),
    input_file: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", dir_okay=False),
    speaker: Optional[str] = typer.Option(None, "--speaker"),
    engine: str = typer.Option("neural", "--engine"),
    speed: Optional[float] = typer.Option(None, "--speed"),
    gain: float = typer.Option(0.0, "--gain"),
    env_file: Path = typer.Option(".env", "--env-file", exists=False),
):
    load_dotenv(env_file, override=True)
    output = output_file or Path(input_file).with_suffix(".mp3")
    synthesize_speech(lang, speaker, input_file, output, engine, speed, gain)
    typer.echo(f"Created {output}")


#
# Transcribe commands
#
@transcribe_app.command("openai")
def transcribe_openai_file(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", dir_okay=False),
    language: Optional[str] = typer.Option(None, "--language", "-l"),
    model: str = typer.Option(OPENAI_DEFAULT_MODEL, "--model"),
    env_file: Path = typer.Option(Path(".env"), "--env-file", exists=False),
):
    """Transcribe a local audio file using OpenAI Whisper."""

    load_dotenv(env_file, override=True)
    out_path = transcribe_file(input_file, language=language, model=model, output_path=output_file)
    typer.echo(f"Created {out_path}")


@transcribe_app.command("aws-list")
def transcribe_aws_s3_list(
    bucket: str = typer.Option(..., "--bucket"),
    prefix: str = typer.Option(..., "--prefix"),
    env_file: Path = typer.Option(Path(".env"), "--env-file", exists=False),
):
    """List objects under an S3 prefix."""

    load_dotenv(env_file, override=True)
    for obj in list_s3_objects(bucket, prefix):
        typer.echo(obj)


@transcribe_app.command("aws-upload")
def transcribe_aws_s3_upload(
    bucket: str = typer.Option(..., "--bucket"),
    prefix: str = typer.Option(..., "--prefix"),
    filename: Path = typer.Argument(..., exists=True, dir_okay=False),
    env_file: Path = typer.Option(Path(".env"), "--env-file", exists=False),
):
    """Upload a local file to S3 under prefix."""

    load_dotenv(env_file, override=True)
    key = upload_file(bucket, prefix, str(filename))
    typer.echo(f"Uploaded to s3://{bucket}/{key}")


@transcribe_app.command("aws-transcribe")
def transcribe_aws_s3_transcribe(
    bucket: str = typer.Option(..., "--bucket"),
    prefix: str = typer.Option(..., "--prefix"),
    object_name: str = typer.Argument(...),
    languages: str = typer.Option(..., "--languages", help="Comma separated (e.g. ja-JP,en-US)"),
    media_format: str = typer.Option(..., "--media-format", help="e.g. mp3, wav, m4a"),
    region: str = typer.Option("ap-northeast-1", "--region"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", dir_okay=False),
    wait_seconds: int = typer.Option(5, "--wait-seconds", help="Polling interval"),
    env_file: Path = typer.Option(Path(".env"), "--env-file", exists=False),
):
    """Start AWS Transcribe on an S3 object and fetch transcript."""

    load_dotenv(env_file, override=True)
    langs = [lang.strip() for lang in languages.split(",") if lang.strip()]
    transcript = transcribe_s3_object(
        bucket=bucket,
        prefix=prefix,
        object_name=object_name,
        languages=langs,
        media_format=media_format,
        region=region,
        wait_seconds=wait_seconds,
    )
    if output_file:
        output_file.write_text(transcript)
        typer.echo(f"Created {output_file}")
    else:
        typer.echo(transcript)


@transcribe_app.command("aws-delete")
def transcribe_aws_s3_delete(
    bucket: str = typer.Option(..., "--bucket"),
    prefix: str = typer.Option(..., "--prefix"),
    object_name: str = typer.Argument(...),
    env_file: Path = typer.Option(Path(".env"), "--env-file", exists=False),
):
    """Delete an object from S3."""

    load_dotenv(env_file, override=True)
    delete_file(bucket, prefix, object_name)
    typer.echo(f"Deleted s3://{bucket}/{prefix}/{object_name}")


#
# Audio commands
#
@audio_app.command("combine")
def audio_combine(
    raw_directory: Path = typer.Argument(..., dir_okay=True, exists=True),
    output_directory: Path = typer.Argument(..., dir_okay=True),
    speed: str = typer.Option("1.0:1.0", "--speed", help="Q:A speed"),
    gain: float = typer.Option(0.0, "--gain"),
    repeat_question: bool = typer.Option(False, "--repeat-question"),
    pause_duration: int = typer.Option(500, "--pause-duration"),
    add_number_audio: bool = typer.Option(False, "--add-number-audio"),
    section_unit: int = typer.Option(10, "--section-unit"),
    artist: str = typer.Option("Homebrew", "--artist"),
):
    output_directory.mkdir(parents=True, exist_ok=True)
    speed_q, speed_a = _parse_speed_pair(speed)
    make_section_mp3_files(
        str(raw_directory),
        str(output_directory),
        speed=(speed_q, speed_a),
        gain=gain,
        repeat_question=repeat_question,
        pause_duration=pause_duration,
        add_number_audio=add_number_audio,
        section_unit=section_unit,
        artist=artist,
    )
    typer.echo(f"Combined into {output_directory}")


@audio_app.command("speed")
def audio_speed(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_directory: Path = typer.Argument(..., dir_okay=True),
    speed: float = typer.Option(..., "--speed", help="Playback speed multiplier"),
    pitch_shift: float = typer.Option(0.0, "--pitch-shift", help="Semitones after speed change"),
    ffmpeg: str = typer.Option("ffmpeg", "--ffmpeg"),
):
    out = process_speed(input_file, output_directory, speed, pitch_shift, ffmpeg)
    typer.echo(f"Created {out}")


@audio_app.command("split-silence")
def audio_split_silence(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(Path.cwd() / "split_audio_files", "--output-dir", "-d"),
    min_silence_len: int = typer.Option(800, "--min-silence-len"),
    silence_thresh: int = typer.Option(-20, "--silence-thresh"),
    album: str = typer.Option("Split audio", "--album"),
    title: Optional[str] = typer.Option(None, "--title"),
):
    split_by_silence(input_file, output_dir, min_silence_len, silence_thresh, album, title)


@audio_app.command("split-duration")
def audio_split_duration(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    segment_minutes: float = typer.Option(..., "--segment-minutes", "-m"),
    output_dir: Path = typer.Option(Path.cwd() / "split_audio_files", "--output-dir", "-d"),
    overlap: int = typer.Option(5, "--overlap"),
    album: str = typer.Option("Split audio", "--album"),
    title: Optional[str] = typer.Option(None, "--title"),
):
    split_by_duration(input_file, segment_minutes, output_dir, overlap, album, title)


@audio_app.command("trim")
def audio_trim(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o"),
    offset: int = typer.Option(0, "--offset", help="ms to trim from start"),
    tail_offset: int = typer.Option(0, "--tail-offset", help="ms to trim from end"),
):
    out = output_file or input_file.with_suffix(".clipped.mp3")
    clip_audio(input_file, out, offset, tail_offset)
    typer.echo(f"Created {out}")


@audio_app.command("trim-silence")
def audio_trim_silence(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o"),
    min_silence: float = typer.Option(1.0, "--min-silence"),
    threshold_db: int = typer.Option(-20, "--threshold-db"),
):
    out = output_file or input_file.with_suffix(".trimmed.mp3")
    trim_with_ffmpeg(str(input_file), str(out), min_silence=min_silence, threshold_db=threshold_db)
    typer.echo(f"Created {out}")


@audio_app.command("join")
def audio_join(
    inputs: List[Path] = typer.Argument(..., exists=True, dir_okay=False),
    output_filename: Path = typer.Option(..., "--output", "-o", dir_okay=False),
    title: str = typer.Option(..., "--title"),
    album: str = typer.Option(..., "--album"),
    artist: str = typer.Option(..., "--artist"),
    silence: int = typer.Option(0, "--silence", "-s", help="Silence between tracks (ms)"),
):
    join_files([str(p) for p in inputs], str(output_filename), title, album, artist, silence)
    typer.echo(f"Created {output_filename}")


@audio_app.command("add-number")
def audio_add_number(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    output_dir: Path = typer.Argument(..., file_okay=False),
):
    output_dir.mkdir(parents=True, exist_ok=True)
    process_audio_files(str(input_dir), str(output_dir))


@audio_app.command("tag-album")
def audio_tag_album(
    dirname: Path = typer.Argument(..., exists=True, file_okay=False),
    album: str = typer.Option(..., "--album", "-a"),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-o"),
):
    tag_album(str(dirname), album, str(output_dir))


@audio_app.command("beep")
def audio_beep(
    output_file: Path = typer.Option(Path("beep.mp3"), "--output", "-o"),
    frequency: int = typer.Option(880, "--frequency"),
    duration: float = typer.Option(0.25, "--duration"),
    amplitude: float = typer.Option(0.5, "--amplitude"),
    sampling_rate: int = typer.Option(44100, "--sampling-rate"),
    gain_db: float = typer.Option(10.0, "--gain-db"),
):
    out = make_beep(
        output_file=str(output_file),
        frequency=frequency,
        duration=duration,
        amplitude=amplitude,
        sampling_rate=sampling_rate,
        gain_db=gain_db,
    )
    typer.echo(f"Created {out}")


def main():
    app()


if __name__ == "__main__":
    main()
