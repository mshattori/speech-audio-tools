# Repository Guidelines

## Project Structure & Module Organization
- CLI entrypoint `sat` lives in `src/speech_audio_tools/cli.py` with Typer commands grouped by feature (tts, audio, split, trim, join, tagging).
- Core audio helpers sit in `src/speech_audio_tools/audio.py`; feature files such as `trim_audio.py`, `join_audio.py`, `change_speed.py`, `trim_silence.py`, and `tts.py` implement individual subcommands.
- Tests are in `tests/`; current smoke coverage is in `tests/test_sat_offline.py`.
- Temporary artifacts (mp3/wav) are generally written to `/tmp`; keep repo clean and avoid committing generated audio.

## Build, Test, and Development Commands
- `uv sync` — install runtime deps; add `--extra test` to include pytest.
- `uv run sat --help` — list available CLI commands.
- `uv run sat tts speakers --lang en-US --engine neural --env-file .env` — quick API connectivity check (needs creds).
- `uv run pytest tests/test_sat_offline.py -q` — offline end-to-end smoke using only FFmpeg.
- Optional local install: `uv tool install .` then call `sat ...` globally.

## Coding Style & Naming Conventions
- Python 3.9+; prefer type hints and 4-space indentation; keep functions small and CLI-friendly.
- Follow Typer/Click patterns: command modules expose `app = Typer(...)` or `@app.command` functions.
- Naming: verbs for command modules (`trim_audio.py`, `change_speed.py`), nouns for data holders; use snake_case for functions and variables.
- No formatter is enforced in tooling; mirror existing style and run a formatter (e.g., `ruff format` or `black`) only if introduced consistently.

## Testing Guidelines
- Primary framework: `pytest` (installed via `uv sync --extra test`).
- Add targeted unit tests under `tests/` mirroring command names, e.g., `test_join_audio.py`.
- For offline coverage, prefer fixtures that operate on tiny mp3/wav snippets and avoid network calls; stub AWS/OpenAI if added.
- Keep tests idempotent and `/tmp`-scoped; clean up generated files within tests.

## Commit & Pull Request Guidelines
- Commit messages: favor short imperative lines (e.g., `Add join fade option`). If you prefer a convention, use Conventional Commits (`feat:`, `fix:`) for clarity.
- PRs should include: brief description of behavior change, CLI examples (`sat ...`), and testing notes (`uv run pytest ...`). Add screenshots or sample audio hashes if UX/regressions are relevant.

## Security & Configuration Tips
- FFmpeg must be available on PATH; install via `brew install ffmpeg` on macOS.
- API keys live in `.env` for AWS Polly or OpenAI TTS; do not commit secrets. Use `--env-file .env` when invoking commands.
- Large audio files belong outside the repo; store in object storage or `/tmp` during local runs.
