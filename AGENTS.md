# Codex Instructions

CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA

When the user asks you to make a video with this repo:

1. Look in `media/`.
2. Use `media/video-spec.json` if it exists.
3. Otherwise use `media/script.txt` or another script/narration text file.
4. Use images from `media/source-images/`.
5. If `media/music.mp3`, `media/music.m4a`, or a file in `media/music/` exists, let the tool use it automatically.
6. Run the simplest command:

```bash
python3 -m codex_video make --output media/generated/final-video.mp4
```

If the user asks for Speaches/Kokoro voice:

```bash
python3 -m codex_video make --tts-provider speaches --tts-voice af_heart --output media/generated/final-video.mp4
```

If Speaches is not running and the user is on macOS, use:

```bash
python3 -m codex_video make --tts-provider say --tts-voice Samantha --output media/generated/final-video.mp4
```

After building, verify with:

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height:format=duration,size -of compact=p=0:nk=1 media/generated/final-video.mp4
```

Music is balanced automatically. The mixer normalizes narration, ducks music under speech, and limits the final output.
