"""Change playback speed (and optional pitch) using FFmpeg atempo chain."""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List

from pydub.utils import mediainfo


def ensure_ffmpeg(binary: str) -> None:
    if shutil.which(binary) is None:
        raise SystemExit(
            f"FFmpeg binary '{binary}' was not found. Install FFmpeg or pass --ffmpeg with the correct path."
        )


def read_sample_rate(path: Path) -> int:
    info = mediainfo(str(path))
    if "sample_rate" not in info:
        raise SystemExit(f"Could not determine sample rate for {path} via ffprobe.")
    return int(info["sample_rate"])


def _split_tempo_factor(value: float) -> List[float]:
    if value <= 0:
        raise ValueError("Tempo factor must be greater than zero.")
    factors: List[float] = []
    remaining = value
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    if not math.isclose(remaining, 1.0, rel_tol=1e-9):
        factors.append(remaining)
    return factors


def build_speed_filters(speed: float) -> List[str]:
    if speed <= 0:
        raise SystemExit("--speed must be greater than 0.")
    return [f"atempo={f:.8f}" for f in _split_tempo_factor(speed)] or ["atempo=1.0"]


def build_pitch_filters(pitch_shift: float, sample_rate: int) -> List[str]:
    if math.isclose(pitch_shift, 0.0, abs_tol=1e-9):
        return []
    pitch_factor = 2 ** (pitch_shift / 12.0)
    filters: List[str] = [f"asetrate={sample_rate * pitch_factor:.6f}", f"aresample={sample_rate}"]
    tempo_comp = 1.0 / pitch_factor
    filters.extend(f"atempo={f:.8f}" for f in _split_tempo_factor(tempo_comp))
    return filters


def run_ffmpeg(ffmpeg_binary: str, input_path: Path, output_path: Path, filters: Iterable[str]) -> None:
    filter_arg = ",".join(filters)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "info",
        "-y",
        "-i",
        str(input_path),
        "-filter:a",
        filter_arg,
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def process_speed(
    input_path: Path,
    output_dir: Path,
    speed: float,
    pitch_shift: float = 0.0,
    ffmpeg_binary: str = "ffmpeg",
) -> Path:
    ensure_ffmpeg(ffmpeg_binary)
    if not input_path.exists():
        raise SystemExit(f"Input file {input_path} does not exist.")
    sample_rate = read_sample_rate(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / input_path.name
    filters: List[str] = []
    filters.extend(build_speed_filters(speed))
    filters.extend(build_pitch_filters(pitch_shift, sample_rate))
    run_ffmpeg(ffmpeg_binary, input_path, output_path, filters)
    return output_path

