import os
import shutil
from pathlib import Path
from typing import Iterable, Optional

from mutagen import File


SUPPORTED_EXTS = {".mp3", ".m4a", ".wav"}


def _iter_audio_files(input_path: Path) -> Iterable[Path]:
    if input_path.is_dir():
        for name in sorted(os.listdir(input_path)):
            path = input_path / name
            if path.suffix.lower() in SUPPORTED_EXTS and path.is_file():
                yield path
    else:
        yield input_path


def _resolve_target(src: Path, output_dir: Optional[Path]) -> Path:
    if output_dir is None:
        return src
    output_dir.mkdir(parents=True, exist_ok=True)
    dst = output_dir / src.name
    shutil.copy2(src, dst)
    return dst


def _set_tags(filepath: Path, album: str, artist: str, title_override: Optional[str]) -> bool:
    audio = File(filepath, easy=True)
    if audio is None:
        print(f"Skipping unsupported file: {filepath}")
        return False

    existing_title = None
    if audio.tags and "title" in audio.tags:
        values = audio.tags.get("title")
        if values:
            existing_title = values[0]

    resolved_title = title_override or existing_title or filepath.stem

    if audio.tags is None:
        audio.add_tags()

    audio["title"] = [resolved_title]
    audio["album"] = [album]
    audio["artist"] = [artist]

    audio.save()
    return True


def tag_album(input_path: str, album: str, output_dir: Optional[str] = None, title: Optional[str] = None, artist: str = "Homebrew"):
    path = Path(input_path)
    if not path.exists():
        raise ValueError(f'"{input_path}" does not exist')

    if title and path.is_dir():
        raise ValueError("--title is only supported when tagging a single file")

    output_path = Path(output_dir) if output_dir else None

    processed = 0
    for src in _iter_audio_files(path):
        if src.suffix.lower() not in SUPPORTED_EXTS:
            print(f"Skipping unsupported extension: {src}")
            continue
        dest = _resolve_target(src, output_path)
        if _set_tags(dest, album=album, artist=artist, title_override=title):
            if output_path is None:
                print(f"Tagged in-place: {dest}")
            else:
                print(f"Copied and tagged: {dest}")
            processed += 1

    if processed == 0:
        raise ValueError("No audio files processed; ensure extensions are supported (.mp3, .m4a, .wav)")
