from pathlib import Path
from unittest import mock

from speech_audio_tools.transcribe_openai import transcribe_file, DEFAULT_MODEL


def test_transcribe_file_writes_output(tmp_path: Path):
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"dummy")

    mock_client = mock.MagicMock()
    mock_client.audio.transcriptions.create.return_value = "hello"

    out = transcribe_file(audio, client=mock_client)

    mock_client.audio.transcriptions.create.assert_called_once()
    args, kwargs = mock_client.audio.transcriptions.create.call_args
    assert kwargs["model"] == DEFAULT_MODEL
    assert out.read_text() == "hello"


def test_transcribe_file_uses_language(tmp_path: Path):
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"dummy")

    mock_client = mock.MagicMock()
    mock_client.audio.transcriptions.create.return_value = "hola"

    transcribe_file(audio, language="es", client=mock_client)
    _, kwargs = mock_client.audio.transcriptions.create.call_args
    assert kwargs["language"] == "es"
