# Source Images

Put source visuals here before asking Codex to build a video.

Recommended naming:

```text
scene-01.png
scene-02.png
scene-03.png
```

Then reference them from a spec with repo-relative media paths such as:

```json
"source_image": "source-images/scene-01.png"
```

When building from a spec stored in `media/`, use `--source-root media`.
