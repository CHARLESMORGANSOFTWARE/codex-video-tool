# Video Spec

The tool reads JSON or YAML. A spec is intentionally plain so GPT can draft it and Codex can adjust it.

```json
{
  "project_name": "Launch Video 01",
  "output_name": "launch-video-01",
  "brand": "Your Product",
  "tagline": "Short footer line.",
  "narration_text": "Full voiceover text for the video.",
  "shots": [
    {
      "headline": "Scene Headline",
      "body": "A concise benefit statement for the lower panel.",
      "narration": "Optional per-scene narration used if narration_text is omitted.",
      "prompt": "Optional image prompt or planning note.",
      "source_image": "source-images/scene-01.png"
    }
  ]
}
```

## Fields

- `project_name`: Human-readable project title.
- `output_name`: Optional slug for generated MP4 names.
- `brand`: Optional text in the top header pill.
- `tagline`: Optional footer line.
- `narration_text`: Full voiceover script. If omitted, the tool joins each shot's `narration`.
- `shots`: Ordered scene records. Each scene becomes one vertical card.
- `source_image`: Absolute path, path relative to the spec file, or path relative to `--source-root`.

## Image Rules

Use screenshots, product images, generated stills, or simple visual plates. The renderer creates the final vertical social-video card, so source images do not need to be 9:16.

If `source_image` is blank, the tool creates a text placeholder card. That is useful for drafts, but final videos should use real images.
