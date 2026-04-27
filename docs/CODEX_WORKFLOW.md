# Codex Workflow

This repo is built for the workflow you described:

1. Ask GPT to write the video script and slide or shot plan.
2. Put source images in `media/source-images/`.
3. Put the generated spec in `media/`, or put plain narration in `media/script.txt`.
4. Ask Codex to run the video tool.
5. Review the MP4 in `media/generated/`.

## Prompt To Give Codex

```text
Use this repo's Codex video tool to create a vertical social video.

Inputs:
- Script or spec: media/script.txt or media/video-spec.json
- Images: media/source-images/
- Optional music: media/music.mp3 or media/music/
- Output: media/generated/my-video.mp4

Run:
python3 -m codex_video make --output media/generated/my-video.mp4

If music is present, use it. The tool balances it under the narration automatically.
```

## Build Commands

Simplest:

```bash
python3 -m codex_video make
```

Use local Speaches or another OpenAI-compatible speech endpoint:

```bash
python3 -m codex_video make \
  --output media/generated/my-video.mp4 \
  --tts-provider speaches \
  --tts-voice af_heart
```

Use the built-in macOS voice:

```bash
python3 -m codex_video make \
  --output media/generated/my-video.mp4 \
  --tts-provider say \
  --tts-voice Samantha
```

Render only cards for visual review:

```bash
python3 -m codex_video render-cards \
  --spec media/my-video-spec.json \
  --source-root media \
  --output-dir media/generated/card-preview
```

## Speaches

The default Speaches settings match the Telecodex workflow:

- Base URL: `http://127.0.0.1:8000/v1`
- Model: `speaches-ai/Kokoro-82M-v1.0-ONNX`
- Voice: `af_heart`

Override them with:

```bash
export SPEACHES_BASE_URL=http://127.0.0.1:8000/v1
export SPEACHES_TTS_MODEL=speaches-ai/Kokoro-82M-v1.0-ONNX
export CODEX_VIDEO_TTS_VOICE=af_heart
```
