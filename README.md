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

## Notes

- FFmpeg must be installed and on PATH for many commands.
- AWS credentials (.env) needed for Polly; OPENAI_API_KEY for OpenAI TTS.
- For local tool-style install: `uv tool install .` then run `sat ...`.

---

# テストと開発 (Testing & Development)

## 前提

- ffmpeg が PATH にあること。
- uv が使えること。
- オンライン TTS テストを行う場合は `.env` に AWS/OPENAI のキーを設定。

## オフライン E2E スモークテスト（推奨）

コード／CLI だけで完結し、外部 API なしで sat を一通り通します。

```bash
# プロジェクトルートで実行
uv sync --extra test        # pytest をインストール
uv run pytest tests/test_sat_offline.py -q
```

テスト内容（簡易）：
- `sat audio beep` で mp3 生成
- `sat audio trim` で先頭カット
- `sat audio speed` で atempo 変換
- `sat audio join` で複数ファイル連結
- `sat audio split-duration` で分割
- `sat audio trim-silence` で FFmpeg の silenceremove 実行

## オンライン TTS スモーク（オプション）

実際に音声 API を叩く簡易チェック。環境に課金リスクがあるため任意。

```bash
echo "Hello from sat" > /tmp/sat_sample.txt
uv run sat tts speakers --lang en-US --engine neural --env-file .env | head -n 3
uv run sat tts synth --lang en-US -i /tmp/sat_sample.txt -o /tmp/sat_sample.mp3 --engine openai-tts-1 --env-file .env
```

## クリーニング

```bash
rm -rf /tmp/sat_sample.txt /tmp/sat_sample.mp3
```

## トラブルシュート

- FFmpeg がない: `brew install ffmpeg`
- キャッシュ権限で uv が失敗: `UV_CACHE_DIR` を書き込み可能な場所に設定するか、必要に応じて権限付きで再実行。
