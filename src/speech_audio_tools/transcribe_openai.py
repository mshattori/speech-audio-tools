from __future__ import annotations

from pathlib import Path
from typing import Optional

from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_RESPONSE_FORMAT = "text"


def transcribe_file(
    input_file: Path,
    *,
    language: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    response_format: str = DEFAULT_RESPONSE_FORMAT,
    output_path: Optional[Path] = None,
    client: Optional[OpenAI] = None,
    **kwargs,
) -> Path:
    """Transcribe a local audio file with OpenAI Whisper API and save text.

    Returns the path to the written transcript file.
    """

    if not input_file.exists():
        raise FileNotFoundError(input_file)

    client = client or OpenAI()
    request_kwargs = {
        "model": model,
        "file": open(input_file, "rb"),
        "response_format": response_format,
    }
    if language:
        request_kwargs["language"] = language
    request_kwargs.update(kwargs)

    try:
        result = client.audio.transcriptions.create(**request_kwargs)
    finally:
        request_kwargs["file"].close()

    # For response_format="text" the SDK returns a plain string; otherwise expect .text
    if isinstance(result, str):
        text = result
    else:
        text = getattr(result, "text", str(result))

    out_path = output_path or input_file.with_suffix(".txt")
    out_path.write_text(text)
    return out_path
