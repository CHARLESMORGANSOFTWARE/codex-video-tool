# Codex Video Tool

CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA

A small, Codex-friendly app for turning a GPT-written script, a shot list, source images, and generated voiceover into a vertical marketing video.

The workflow is simple: GPT drafts the spec, you place images in `media/source-images/`, Codex runs this tool, and the finished MP4 lands in `media/generated/`.

For the simplest guide, read `USER_MANUAL.md`.
For pure copy/paste commands, read `CLI_COPY_PASTE.md`.

## Requirements

- Python 3.9+
- ffmpeg and ffprobe
- Python packages from `pyproject.toml`
- Optional: local Speaches/Kokoro TTS at `http://127.0.0.1:8000/v1`

Install locally:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Install ffmpeg on macOS:

```bash
brew install ffmpeg
```

## Quick Demo

Create demo images:

```bash
python3 scripts/create_demo_assets.py
```

Build a silent demo video:

```bash
python3 -m codex_video make --spec examples/demo-spec.json --media-dir . --output media/generated/demo.mp4 --tts-provider silent
```

Build with Speaches TTS:

```bash
python3 -m codex_video make --spec examples/demo-spec.json --media-dir . --output media/generated/demo.mp4 --tts-provider speaches --tts-voice af_heart
```

Build with macOS `say`:

```bash
python3 -m codex_video make --spec examples/demo-spec.json --media-dir . --output media/generated/demo.mp4 --tts-provider say --tts-voice Samantha
```

## Easiest Real Use

Put your voiceover in `media/script.txt`.
Put images in `media/source-images/`.
Optionally put music at `media/music.mp3` or in `media/music/`.
Then run:

```bash
python3 -m codex_video make
```

Choose an output file:

```bash
python3 -m codex_video make --output media/generated/final-video.mp4
```

Music is balanced automatically: narration is normalized, music ducks under speech, and the final mix is limited.

## Media Layout

```text
media/
  source-images/    raw screenshots, product images, generated stills
  generated/        bundles, cards, narration audio, final MP4s
```

Generated media is ignored by Git so the repo can stay light. Commit specs, docs, and reusable examples. Keep large outputs out of Git unless you intentionally want sample renders.

## Spec Format

See `docs/SPEC.md`. The short version:

```json
{
  "project_name": "My Launch Video",
  "narration_text": "Full voiceover script...",
  "shots": [
    {
      "headline": "Start With One Message",
      "body": "A concise benefit statement.",
      "source_image": "source-images/scene-01.png"
    }
  ]
}
```

## Codex Usage

Give Codex the spec path, image folder, desired output path, and TTS preference. A good instruction is in `docs/CODEX_WORKFLOW.md`.

The main command:

```bash
python3 -m codex_video make --output media/generated/my-video.mp4
```

## What The Tool Produces

- `narration.txt`
- generated or attached narration audio
- `001.png`, `002.png`, etc. vertical cards
- `concat.txt`
- final H.264/AAC MP4
- `manifest.json` with source paths, timing, and validation results

## Original Telecodex Workflow

This package is distilled from the Telecodex marketing-video process: specs and source images go in, TTS narration and polished vertical cards come out, then ffmpeg compiles a finished social video. Migration notes live in `docs/TELECODEX_MIGRATION_NOTES.md`.
