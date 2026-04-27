# CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from codex_video import cli


def make_image(path: Path, color=(20, 80, 140)) -> None:
    image = Image.new("RGB", (640, 480), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 560, 400), outline=(120, 220, 255), width=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def make_music(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-ac",
            "2",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def make_spec(tmp_path: Path) -> Path:
    image_dir = tmp_path / "source-images"
    make_image(image_dir / "scene-01.png")
    make_image(image_dir / "scene-02.png", color=(80, 40, 120))
    spec = {
        "project_name": "Test Video",
        "narration_text": "This is a short generated test video. It verifies cards and compile behavior.",
        "shots": [
            {
                "headline": "First Scene",
                "body": "The first source image renders into a vertical card.",
                "source_image": "source-images/scene-01.png",
            },
            {
                "headline": "Second Scene",
                "body": "The second source image renders into a vertical card.",
                "source_image": "source-images/scene-02.png",
            },
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def test_load_video_spec(tmp_path: Path) -> None:
    spec_path = make_spec(tmp_path)
    spec = cli.load_video_spec(spec_path)
    assert spec.project_name == "Test Video"
    assert len(spec.shots) == 2
    assert spec.narration_text.startswith("This is a short")


def test_render_cards(tmp_path: Path) -> None:
    spec_path = make_spec(tmp_path)
    spec = cli.load_video_spec(spec_path)
    cards = cli.render_cards(
        spec,
        output_dir=tmp_path / "cards",
        source_root=tmp_path,
        brand="Test",
        tagline="Render the result.",
    )
    assert len(cards) == 2
    rendered = Image.open(cards[0]["output_path"])
    assert rendered.size == (cli.VIDEO_WIDTH, cli.VIDEO_HEIGHT)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg is required")
def test_build_silent_video(tmp_path: Path) -> None:
    spec_path = make_spec(tmp_path)
    output_path = tmp_path / "generated" / "test.mp4"
    args = cli.build_parser().parse_args(
        [
            "build",
            "--spec",
            str(spec_path),
            "--source-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output",
            str(output_path),
            "--tts-provider",
            "silent",
            "--seconds-per-scene",
            "0.75",
            "--format",
            "json",
        ]
    )
    payload = cli.build_video(args)
    assert output_path.exists()
    assert payload["validation"]["ok"] is True
    assert payload["audio"]["provider"] == "silent"


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg is required")
def test_make_from_media_folder(tmp_path: Path) -> None:
    media = tmp_path / "media"
    image_dir = media / "source-images"
    make_image(image_dir / "image-01.png")
    make_image(image_dir / "image-02.png", color=(80, 40, 120))
    (media / "script.txt").write_text(
        "The first scene introduces the video.\n\nThe second scene shows the result.",
        encoding="utf-8",
    )
    output_path = media / "generated" / "final.mp4"
    args = cli.build_parser().parse_args(
        [
            "make",
            "--media-dir",
            str(media),
            "--output",
            str(output_path),
            "--tts-provider",
            "silent",
            "--seconds-per-scene",
            "0.75",
            "--format",
            "json",
        ]
    )
    payload = cli.make_video_action(args)
    assert output_path.exists()
    assert payload["action"] == "make"
    assert payload["auto_generated_spec"] is True
    assert payload["validation"]["ok"] is True


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg is required")
def test_make_auto_discovers_and_ducks_music(tmp_path: Path) -> None:
    media = tmp_path / "media"
    image_dir = media / "source-images"
    make_image(image_dir / "image-01.png")
    make_image(image_dir / "image-02.png", color=(80, 40, 120))
    make_music(media / "music" / "theme.wav")
    (media / "script.txt").write_text(
        "The first scene introduces the video.\n\nThe second scene shows the result.",
        encoding="utf-8",
    )
    output_path = media / "generated" / "with-music.mp4"
    args = cli.build_parser().parse_args(
        [
            "make",
            "--media-dir",
            str(media),
            "--output",
            str(output_path),
            "--tts-provider",
            "silent",
            "--seconds-per-scene",
            "0.75",
            "--format",
            "json",
        ]
    )
    payload = cli.make_video_action(args)
    assert output_path.exists()
    assert payload["auto_discovered_music"] is True
    assert payload["audio"]["music"]["enabled"] is True
    assert payload["audio"]["music"]["ducking"] is True
    assert Path(payload["audio"]["music"]["mixed_output_path"]).exists()
