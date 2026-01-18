#!/usr/bin/env python3
"""
Regenerate bundled number audio (1-100) using the internal _make_number_audio helper.

Requirements: AWS/Polly or other TTS creds compatible with the project's SimpleTTS default,
and network access if your engine needs it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_audio_tools.audio import _make_number_audio, NUMBER_AUDIO_DIR  # noqa: E402


def main() -> int:
    generated = []
    errors = []
    Path(NUMBER_AUDIO_DIR).mkdir(parents=True, exist_ok=True)
    for n in range(1, 101):
        try:
            target = Path(NUMBER_AUDIO_DIR) / f"{n}.mp3"
            if target.exists():
                continue
            path = _make_number_audio(n)
            generated.append(str(Path(path).resolve()))
        except Exception as exc:  # noqa: BLE001
            errors.append((n, str(exc)))
    if generated:
        print("Generated/verified:", ", ".join(str(Path(p).name) for p in generated))
    if errors:
        for n, msg in errors:
            print(f"Failed {n}: {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
