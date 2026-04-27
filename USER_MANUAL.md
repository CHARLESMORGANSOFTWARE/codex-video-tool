# Codex Video Tool User Manual

CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA

## What This Tool Does

This tool turns text and images into a vertical social video.

You give it:

- a script or video spec
- images
- optional background music
- optional voice settings

It makes:

- vertical video cards
- narration audio
- balanced background music under the narration
- a finished `.mp4`

## The Simple Way

Put your files here:

```text
media/
  script.txt
  source-images/
    image-01.png
    image-02.png
    image-03.png
  music.mp3
```

Then run:

```bash
python3 -m codex_video make
```

The video will be created here:

```text
media/generated/
```

## Use GPT To Create The Video Inputs

Before running the tool, use GPT to create:

- the voiceover script
- the scene plan
- image prompts
- optional music direction

You can use either the simple `script.txt` workflow or the more controlled `video-spec.json` workflow.

## GPT Prompt For A Simple Script

Copy this into GPT:

```text
Create a vertical social video script for this topic:

[PASTE TOPIC OR PRODUCT HERE]

Make it 45 to 60 seconds long.
Write it as a voiceover script only.
Use 6 to 8 short paragraphs.
Each paragraph should match one visual scene.
Keep the tone clear, direct, and promotional without sounding fake.
End with a simple call to action.
```

Save GPT's answer here:

```text
media/script.txt
```

Then ask GPT for image prompts:

```text
Turn this video script into 6 to 8 image prompts.

For each scene, give me:
- scene number
- short visual description
- image prompt for a vertical 9:16 image

Do not put words, captions, logos, or UI text inside the images.
The video tool will add the headline and text later.

Here is the script:

[PASTE SCRIPT HERE]
```

Generate or collect one image for each prompt and save them here:

```text
media/source-images/image-01.png
media/source-images/image-02.png
media/source-images/image-03.png
```

Use the same order as the script.

## GPT Prompt For A Full Video Spec

For more control, ask GPT to create a full spec.

Copy this into GPT:

```text
Create a JSON video spec for the Codex Video Tool.

Topic:
[PASTE TOPIC OR PRODUCT HERE]

Requirements:
- vertical social video
- 6 to 8 scenes
- 45 to 60 seconds
- concise headlines
- short lower-panel body copy
- full narration_text
- source images named source-images/image-01.png, source-images/image-02.png, etc.
- no markdown, only valid JSON

Use this format:

{
  "project_name": "Video Title",
  "output_name": "video-title",
  "brand": "Brand Name",
  "tagline": "Short footer tagline.",
  "narration_text": "Full voiceover script...",
  "shots": [
    {
      "headline": "Scene Headline",
      "body": "Short benefit line.",
      "narration": "Narration for this scene.",
      "prompt": "Image prompt for this scene.",
      "source_image": "source-images/image-01.png"
    }
  ]
}
```

Save GPT's JSON here:

```text
media/video-spec.json
```

Then use the `prompt` field from each scene to create images. Save them as:

```text
media/source-images/image-01.png
media/source-images/image-02.png
media/source-images/image-03.png
```

Then run:

```bash
python3 -m codex_video make
```

## Image Tips

Good source images:

- product screenshots
- generated campaign images
- real product or location photos
- clean slide images
- simple visual backgrounds

Avoid:

- tiny text inside the image
- busy screenshots that cannot be read on a phone
- random stock images that do not match the script
- mismatched image order

The tool adds the final video headline, body panel, brand header, and footer tagline. The image should be the visual focus, not the whole ad by itself.

## What To Put In `script.txt`

Paste the voiceover text.

Example:

```text
This video introduces our new product.

It starts with the problem customers face every day.

Then it shows how our tool solves the problem with less work.

The final scene gives the viewer a simple next step.
```

The tool will split the script across the images.

## What To Put In `source-images`

Use screenshots, generated images, product photos, slide images, or campaign art.

Recommended names:

```text
image-01.png
image-02.png
image-03.png
image-04.png
```

Images are used in sorted order.

## Add Music

Put a music file here:

```text
media/music.mp3
```

Or here:

```text
media/music/theme.mp3
```

Then run the normal command:

```bash
python3 -m codex_video make
```

The tool automatically:

- keeps the music low
- normalizes the voice
- ducks the music when narration is speaking
- limits the final mix so it does not clip

That means the voice stays in front and the music sits underneath it.

You can ask GPT for music direction too:

```text
Suggest background music direction for this video.

Give me:
- mood
- tempo
- instruments
- what to avoid
- 3 search phrases I can use in a royalty-free music library

Here is the script:

[PASTE SCRIPT HERE]
```

Use music that you own, created yourself, or have permission to use.

You can choose music manually:

```bash
python3 -m codex_video make --music-file media/music/theme.mp3
```

Make the music quieter:

```bash
python3 -m codex_video make --music-volume 0.10
```

Make the music a little louder:

```bash
python3 -m codex_video make --music-volume 0.22
```

## Use A Full Spec Instead

For more control, put this in:

```text
media/video-spec.json
```

Then run the same command:

```bash
python3 -m codex_video make
```

The tool will use the spec instead of guessing from `script.txt`.

## Voice Options

Default:

```bash
python3 -m codex_video make
```

This tries Speaches first, then macOS `say`.

Use Speaches/Kokoro:

```bash
python3 -m codex_video make --tts-provider speaches --tts-voice af_heart
```

Use macOS voice:

```bash
python3 -m codex_video make --tts-provider say --tts-voice Samantha
```

Use an audio file you already made:

```bash
python3 -m codex_video make --audio-file media/narration.mp3
```

## Ask Codex To Run It

Copy this into Codex:

```text
Use this repo's video tool.

Make a vertical video from the text and images in the media folder.
Use media/script.txt for narration.
Use media/source-images for the images.
Put the finished MP4 in media/generated.

Run:
python3 -m codex_video make
```

## Output

The finished video goes to:

```text
media/generated/<project-name>.mp4
```

The tool also creates a bundle with cards, audio, and a manifest:

```text
media/generated/bundles/
```

## If Something Fails

Check these first:

```bash
python3 --version
ffmpeg -version
python3 -m codex_video --help
```

If `ffmpeg` is missing on macOS:

```bash
brew install ffmpeg
```
