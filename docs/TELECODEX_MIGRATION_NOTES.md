# Telecodex Migration Notes

This repo packages the marketing-video workflow into a standalone CLI instead of depending on the full Telecodex app tree.

The original local workflow used:

- `hype-video` to stage and compile launch videos.
- `imovie-reel-stager` to build narration audio and image bundles.
- `codovox` backed by local Speaches/Kokoro for TTS.
- A polished vertical-card pass for final 1080x1920 social videos.

The standalone package keeps the useful public-facing pieces:

- Plain JSON/YAML specs.
- `media/source-images/` for source visuals.
- `media/generated/` for generated bundles and final MP4s.
- Speaches-compatible TTS.
- macOS `say` fallback.
- ffmpeg H.264/AAC MP4 export.
- Repeatable card rendering without iMovie.

Paths from the original machine, such as `/Applications/Telecodex30` or `/Volumes/EXT/Applications/Marketing`, should not appear in specs that are meant to be shared on GitHub. Use repo-relative paths through `--source-root media` instead.
