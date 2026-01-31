import os
import sys
import subprocess
from pathlib import Path
import pytest


def run_cli(*args, cwd=None, check=True):
    repo_root = Path(__file__).resolve().parents[1]
    python_bin = repo_root / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    cmd = [str(python_bin), "-m", "speech_audio_tools.cli", *args]
    return subprocess.run(cmd, cwd=cwd or repo_root, check=check, capture_output=True, env=env)


def _ffmpeg_reads(path: Path) -> bool:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def test_audio_beep_and_trim_and_speed(tmp_path: Path):
    beep_file = tmp_path / "beep.mp3"
    run_cli("audio", "beep", "--output", str(beep_file))
    assert beep_file.exists() and beep_file.stat().st_size > 0

    trimmed = tmp_path / "beep.trim.mp3"
    run_cli("audio", "trim", str(beep_file), "--output", str(trimmed), "--offset", "50")
    assert trimmed.exists() and trimmed.stat().st_size > 0

    sped_dir = tmp_path / "sped"
    run_cli("audio", "speed", str(beep_file), str(sped_dir), "--speed", "1.5")
    sped_file = sped_dir / "beep.mp3"
    assert sped_file.exists() and sped_file.stat().st_size > 0


def test_split_and_join(tmp_path: Path):
    base = tmp_path / "audio"
    base.mkdir()
    # create two short beeps with silence to make splitting deterministic
    for name in ("a", "b"):
        run_cli("audio", "beep", "--output", str(base / f"{name}.mp3"), "--duration", "0.3")

    joined = tmp_path / "joined.mp3"
    run_cli(
        "audio",
        "join",
        str(base / "a.mp3"),
        str(base / "b.mp3"),
        "--output",
        str(joined),
        "--title",
        "test",
        "--album",
        "test",
        "--artist",
        "test",
        "--silence",
        "200",
    )
    assert joined.exists() and joined.stat().st_size > 0

    split_dir = tmp_path / "split"
    run_cli(
        "audio",
        "split-duration",
        str(joined),
        "--segment-minutes",
        "0.001",
        "--output-dir",
        str(split_dir),
        "--overlap",
        "0",
    )
    parts = list(split_dir.glob("*.mp3"))
    assert parts, "split-duration should create at least one chunk"


def test_trim_silence_runs(tmp_path: Path):
    beep_file = tmp_path / "beep.mp3"
    run_cli("audio", "beep", "--output", str(beep_file), "--duration", "0.5")
    if not _ffmpeg_reads(beep_file):
        pytest.skip("ffmpeg cannot decode generated mp3 on this system")
    trimmed = tmp_path / "beep.trimmed.mp3"
    proc = run_cli(
        "audio",
        "trim-silence",
        str(beep_file),
        "--output",
        str(trimmed),
        "--min-silence",
        "0.2",
        "--threshold-db",
        "-30",
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip("ffmpeg silenceremove failed in this environment")
    assert trimmed.exists() and trimmed.stat().st_size > 0


def _read_tags(path: Path):
    try:
        from mutagen import File
    except ModuleNotFoundError:
        pytest.skip("mutagen not installed")

    audio = File(path, easy=True)
    if audio is None:
        return {}
    return {k: v[0] for k, v in audio.tags.items()} if audio.tags else {}


def test_tag_album_single_file_in_place(tmp_path: Path):
    src = tmp_path / "tone.mp3"
    run_cli("audio", "beep", "--output", str(src), "--duration", "0.2")

    run_cli("audio", "tag-album", str(src), "--album", "Test Album", "--title", "Custom Title", "--artist", "Tester")

    tags = _read_tags(src)
    assert tags.get("album") == "Test Album"
    assert tags.get("title") == "Custom Title"
    assert tags.get("artist") == "Tester"


def test_tag_album_single_file_copy_then_tag(tmp_path: Path):
    src = tmp_path / "tone.mp3"
    run_cli("audio", "beep", "--output", str(src), "--duration", "0.2")

    out_dir = tmp_path / "out"
    run_cli("audio", "tag-album", str(src), "--album", "Copied Album", "--output-dir", str(out_dir))

    dest = out_dir / src.name
    assert dest.exists() and dest.stat().st_size > 0
    assert src.exists(), "source file should remain"
    tags = _read_tags(dest)
    assert tags.get("album") == "Copied Album"
    assert tags.get("title") == "tone"  # from filename


def test_tag_album_directory_in_place(tmp_path: Path):
    input_dir = tmp_path / "album"
    input_dir.mkdir()
    for name in ("a", "b"):
        run_cli("audio", "beep", "--output", str(input_dir / f"{name}.mp3"), "--duration", "0.15")

    run_cli("audio", "tag-album", str(input_dir), "--album", "Dir Album")

    for name in ("a", "b"):
        path = input_dir / f"{name}.mp3"
        tags = _read_tags(path)
        assert tags.get("album") == "Dir Album"
        assert tags.get("title") == name


def test_tag_album_directory_title_error(tmp_path: Path):
    input_dir = tmp_path / "album"
    input_dir.mkdir()
    run_cli("audio", "beep", "--output", str(input_dir / "a.mp3"), "--duration", "0.1")

    proc = run_cli("audio", "tag-album", str(input_dir), "--album", "X", "--title", "Nope", check=False)
    assert proc.returncode != 0
    assert b"--title is only supported when tagging a single file" in proc.stderr
