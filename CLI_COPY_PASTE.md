# CLI Copy/Paste Instructions

CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA

## 1. Install

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd codex-video-tool
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## 2. Install ffmpeg

macOS:

```bash
brew install ffmpeg
```

Ubuntu/Linux:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

## 3. Put In Your Inputs

```bash
mkdir -p media/source-images media/generated
```

Put your voiceover here:

```text
media/script.txt
```

Put your images here:

```text
media/source-images/
```

Optional music:

```text
media/music.mp3
```

## 4. Make The Video

Easiest command:

```bash
python3 -m codex_video make
```

Use Speaches:

```bash
python3 -m codex_video make --tts-provider speaches --tts-voice af_heart
```

Use macOS `say`:

```bash
python3 -m codex_video make --tts-provider say --tts-voice Samantha
```

Choose the output file:

```bash
python3 -m codex_video make --output media/generated/final-video.mp4
```

Add music manually:

```bash
python3 -m codex_video make --music-file media/music.mp3 --output media/generated/final-video.mp4
```

Lower the music:

```bash
python3 -m codex_video make --music-volume 0.10 --output media/generated/final-video.mp4
```

Use an existing narration audio file:

```bash
python3 -m codex_video make --audio-file media/narration.mp3
```

Render without voice for testing:

```bash
python3 -m codex_video make --tts-provider silent
```

## 5. Demo Test

```bash
python3 scripts/create_demo_assets.py
python3 -m codex_video make --spec examples/demo-spec.json --media-dir . --output media/generated/demo.mp4 --tts-provider silent
```

## 6. Check The Video

```bash
ffprobe -v error \
  -show_entries stream=codec_type,codec_name,width,height:format=duration,size \
  -of compact=p=0:nk=1 \
  media/generated/demo.mp4
```

Expected:

```text
h264|video|1080|1920
aac|audio
```

## Codex Prompt

```text
Use the Codex Video Tool in this repo.

Inputs:
- media/script.txt
- media/source-images/
- optional media/music.mp3

Output:
- media/generated/final-video.mp4

Run the simplest command:
python3 -m codex_video make --output media/generated/final-video.mp4

If music is present, the tool should use it and keep it balanced under the voice.
```
