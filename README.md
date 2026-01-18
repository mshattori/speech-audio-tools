# speech-audio-tools (sat)

CLI utilities for generating TTS audio and doing light post-processing.

## Install (local)

```bash
uv sync
uv run sat --help
```

## CLI overview

- `sat tts speakers` — list voices for engine/lang
- `sat tts synth` — single text file to mp3
- `sat audio combine` — combine raw Q/A into section mp3
- `sat audio speed` — change speed (atempo) and optional pitch
- `sat audio split-silence` / `split-duration` — split audio into chunks
- `sat audio trim` / `trim-silence` — clip by offset or silence
- `sat audio join` — concatenate files with optional gaps
- `sat audio add-number` — prepend spoken numbers to mp3 list
- `sat audio tag-album` — set title/album tags for directory
- `sat audio beep` — generate reference beep tone
- `sat transcribe openai` — transcribe a local audio file with OpenAI Whisper
- `sat transcribe aws-upload` — upload a file to S3
- `sat transcribe aws-list` — list objects under a prefix
- `sat transcribe aws-transcribe` — run AWS Transcribe on an S3 object and fetch text
- `sat transcribe aws-delete` — delete an object from S3

## Notes

- FFmpeg must be installed and on PATH for many commands.
- AWS credentials (.env) needed for Polly; OPENAI_API_KEY for OpenAI TTS.
- For local tool-style install: `uv tool install .` then run `sat ...`.

## Testing & Development

### Prerequisites

- FFmpeg is on `PATH`.
- `uv` is available.
- For online TTS checks, put AWS/OPENAI keys in `.env`.

### Offline E2E Smoke (recommended)

Runs the CLI end to end without external APIs.

```bash
# Run at project root
uv sync --extra test        # installs pytest
uv run pytest tests/test_sat_offline.py -q
```

What it covers:
- `sat audio beep` generates an mp3.
- `sat audio trim` removes leading audio.
- `sat audio speed` applies `atempo`.
- `sat audio join` concatenates multiple files.
- `sat audio split-duration` splits by duration.
- `sat audio trim-silence` runs FFmpeg `silenceremove`.

### Online TTS Smoke (optional)

Quick API sanity check; optional because it can incur costs.

```bash
echo "Hello from sat" > /tmp/sat_sample.txt
uv run sat tts speakers --lang en-US --engine neural --env-file .env | head -n 3
uv run sat tts synth --lang en-US -i /tmp/sat_sample.txt -o /tmp/sat_sample.mp3 --engine openai-tts-1 --env-file .env
```

### Transcribe (STT)

OpenAI (local file):

```bash
uv run sat transcribe openai sample.m4a --language ja --env-file .env
```

AWS Transcribe (S3 object):

```bash
# upload
uv run sat transcribe aws-upload --bucket my-bucket --prefix audio/ sample.m4a --env-file .env

# run job and fetch transcript
uv run sat transcribe aws-transcribe --bucket my-bucket --prefix audio --languages ja-JP,en-US --media-format m4a sample.m4a --env-file .env
```

Notes:
- Defaults: OpenAI model `gpt-4o-mini-transcribe`, AWS region `ap-northeast-1`.
- `--output` writes transcript to a file; otherwise prints to stdout.

### Cleanup

```bash
rm -rf /tmp/sat_sample.txt /tmp/sat_sample.mp3
```

### Troubleshooting

- Missing FFmpeg: `brew install ffmpeg`
- `uv` fails due to cache permissions: set `UV_CACHE_DIR` to a writable path or rerun with appropriate permissions.
