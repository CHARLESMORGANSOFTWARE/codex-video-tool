#!/usr/bin/env python3
# CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


TOOL_NAME = "codex-video"
DISPLAY_NAME = "Codex Video Tool"
DESCRIPTION = "Turn a script, a shot spec, source images, and TTS audio into a vertical MP4."
SIGNATURE = "CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
DEFAULT_OUTPUT_DIR = Path("media/generated")
DEFAULT_BRAND = "Telethryve"
DEFAULT_TAGLINE = "Text the work. Leave the desk. Get the result back."
DEFAULT_SPEACHES_URL = "http://127.0.0.1:8000/v1"
DEFAULT_SPEACHES_MODEL = "speaches-ai/Kokoro-82M-v1.0-ONNX"
DEFAULT_SPEACHES_VOICE = "af_heart"

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class ToolError(RuntimeError):
    """Expected user-facing error."""


@dataclass
class ShotSpec:
    index: int
    headline: str
    body: str
    narration: str
    prompt: str
    source_image: str


@dataclass
class VideoSpec:
    project_name: str
    narration_text: str
    shots: List[ShotSpec]
    output_name: str
    brand: str
    tagline: str
    spec_path: Optional[Path]


_FONT_CACHE: Dict[Tuple[int, bool], ImageFont.FreeTypeFont] = {}


def _slugify(value: object, default: str = "video") -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip()).strip("-").lower()
    while "--" in text:
        text = text.replace("--", "-")
    return text or default


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run(command: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(list(command), capture_output=True, text=True)
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ToolError(detail or "Command failed: " + " ".join(command))
    return completed


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_structured_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ToolError(f"Spec file was not found: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw)
        else:
            payload = json.loads(raw)
    except Exception as exc:
        raise ToolError(f"Invalid spec file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ToolError(f"Spec file must contain an object: {path}")
    return payload


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _headline_from_text(text: str, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9']+", text)
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "your",
    }
    useful = [word for word in words if word.lower() not in stop_words]
    if not useful:
        return fallback
    return " ".join(useful[:5]).title()


def _coerce_shots(raw: Any) -> List[ShotSpec]:
    if not isinstance(raw, list):
        return []
    shots: List[ShotSpec] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str):
            prompt = _normalize_text(item)
            if prompt:
                shots.append(
                    ShotSpec(
                        index=index,
                        headline=_headline_from_text(prompt, f"Scene {index:02d}"),
                        body=prompt,
                        narration="",
                        prompt=prompt,
                        source_image="",
                    )
                )
            continue
        if not isinstance(item, Mapping):
            continue
        headline = _normalize_text(item.get("headline") or item.get("title") or "")
        body = _normalize_text(item.get("body") or item.get("caption") or item.get("copy") or "")
        narration = _normalize_text(item.get("narration") or item.get("voiceover") or item.get("script") or "")
        prompt = _normalize_text(item.get("prompt") or body or narration or headline or "")
        source_image = str(item.get("source_image") or item.get("image") or item.get("image_path") or "").strip()
        if not any([headline, body, narration, prompt, source_image]):
            continue
        if not headline:
            headline = _headline_from_text(prompt or narration or body, f"Scene {index:02d}")
        if not body:
            body = narration or prompt
        shots.append(
            ShotSpec(
                index=index,
                headline=headline,
                body=body,
                narration=narration,
                prompt=prompt,
                source_image=source_image,
            )
        )
    return shots


def _join_narration(shots: Sequence[ShotSpec]) -> str:
    parts = [shot.narration.strip() for shot in shots if shot.narration.strip()]
    return " ".join(parts).strip()


def load_video_spec(path: Path) -> VideoSpec:
    payload = _load_structured_file(path)
    shots = _coerce_shots(payload.get("shots") or payload.get("scenes") or [])
    if not shots:
        raise ToolError("Spec must contain at least one shot in `shots` or `scenes`.")
    narration_text = _normalize_text(payload.get("narration_text") or payload.get("narration") or payload.get("script") or "")
    if not narration_text:
        narration_text = _join_narration(shots)
    if not narration_text:
        raise ToolError("Spec must provide `narration_text` or per-shot `narration`.")
    project_name = _normalize_text(payload.get("project_name") or payload.get("title") or "Codex Video")
    return VideoSpec(
        project_name=project_name,
        narration_text=narration_text,
        shots=shots,
        output_name=_slugify(payload.get("output_name") or project_name),
        brand=_normalize_text(payload.get("brand") or DEFAULT_BRAND),
        tagline=_normalize_text(payload.get("tagline") or DEFAULT_TAGLINE),
        spec_path=path,
    )


def _font_candidates(bold: bool) -> List[Path]:
    if bold:
        names = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        names = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    return [Path(name) for name in names]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _font_candidates(bold):
        if not path.exists():
            continue
        try:
            font = ImageFont.truetype(str(path), size=size)
            _FONT_CACHE[key] = font
            return font
        except OSError:
            continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def _split_long_word(draw: ImageDraw.ImageDraw, word: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    parts: List[str] = []
    current = ""
    for char in word:
        candidate = current + char
        if current and _text_size(draw, candidate, font)[0] > max_width:
            parts.append(current)
            current = char
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts or [word]


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: Optional[int] = None,
) -> List[str]:
    words: List[str] = []
    for word in _normalize_text(text).split(" "):
        if _text_size(draw, word, font)[0] > max_width:
            words.extend(_split_long_word(draw, word, font, max_width))
        else:
            words.append(word)

    lines: List[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and _text_size(draw, candidate, font)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    if max_lines is not None and len(lines) > max_lines:
        kept = lines[: max_lines - 1]
        final = " ".join(lines[max_lines - 1 :])
        while final and _text_size(draw, final + "...", font)[0] > max_width:
            final = final[:-1].rstrip()
        kept.append((final + "...") if final else "...")
        lines = kept
    return lines


def _fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int,
    start_size: int,
    min_size: int,
    *,
    bold: bool,
) -> Tuple[ImageFont.ImageFont, List[str]]:
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(size, bold=bold)
        lines = _wrap_text(draw, text, font, max_width, max_lines=max_lines)
        if len(lines) <= max_lines and all(_text_size(draw, line, font)[0] <= max_width for line in lines):
            return font, lines
    font = _load_font(min_size, bold=bold)
    return font, _wrap_text(draw, text, font, max_width, max_lines=max_lines)


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    lines: Sequence[str],
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
    *,
    line_gap: int,
    shadow: bool = False,
) -> int:
    x, y = xy
    cursor = y
    for line in lines:
        if shadow:
            draw.text((x + 3, cursor + 4), line, font=font, fill=(0, 0, 0, 120))
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += _text_size(draw, line, font)[1] + line_gap
    return cursor


def _cover_image(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    width, height = size
    img = ImageOps.exif_transpose(image).convert("RGB")
    ratio = max(width / img.width, height / img.height)
    resized = img.resize((int(img.width * ratio) + 1, int(img.height * ratio) + 1), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _contain_image(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    img = ImageOps.exif_transpose(image).convert("RGBA")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    return img


def _paste_rounded(base: Image.Image, image: Image.Image, box: Tuple[int, int, int, int], radius: int) -> None:
    x1, y1, x2, y2 = box
    target = Image.new("RGBA", (x2 - x1, y2 - y1), (9, 17, 31, 255))
    contained = _contain_image(image, (x2 - x1, y2 - y1))
    px = (target.width - contained.width) // 2
    py = (target.height - contained.height) // 2
    target.alpha_composite(contained, (px, py))
    mask = Image.new("L", target.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, target.width, target.height), radius=radius, fill=255)
    base.paste(target, (x1, y1), mask)


def _draw_glow(base: Image.Image, ellipse: Tuple[int, int, int, int], color: Tuple[int, int, int, int], blur: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(ellipse, fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def _placeholder_image(shot: ShotSpec, index: int) -> Image.Image:
    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (6, 13, 28))
    draw = ImageDraw.Draw(image)
    for y in range(0, VIDEO_HEIGHT, 16):
        shade = int(20 + 35 * (y / VIDEO_HEIGHT))
        draw.rectangle((0, y, VIDEO_WIDTH, y + 16), fill=(5, 13 + shade // 4, 30 + shade // 3))
    font = _load_font(82, bold=True)
    small = _load_font(34, bold=False)
    headline = shot.headline or f"Scene {index:02d}"
    lines = _wrap_text(draw, headline, font, 760, max_lines=3)
    total_height = sum(_text_size(draw, line, font)[1] for line in lines) + (len(lines) - 1) * 16
    cursor = (VIDEO_HEIGHT - total_height) // 2
    for line in lines:
        width, height = _text_size(draw, line, font)
        draw.text(((VIDEO_WIDTH - width) // 2, cursor), line, font=font, fill=(235, 247, 255))
        cursor += height + 16
    label = "Add a source_image for richer visuals"
    width, _ = _text_size(draw, label, small)
    draw.text(((VIDEO_WIDTH - width) // 2, cursor + 36), label, font=small, fill=(102, 209, 255))
    return image


def _open_image(path: Optional[Path], shot: ShotSpec, index: int) -> Image.Image:
    if path is None:
        return _placeholder_image(shot, index)
    try:
        return Image.open(path)
    except OSError as exc:
        raise ToolError(f"Could not open image {path}: {exc}") from exc


def _resolve_source_image(raw: str, *, spec_dir: Optional[Path], source_root: Optional[Path]) -> Optional[Path]:
    value = str(raw or "").strip()
    if not value:
        return None
    candidate = Path(value).expanduser()
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()

    roots: List[Path] = []
    if source_root is not None:
        roots.append(source_root)
    if spec_dir is not None:
        roots.append(spec_dir)
    roots.append(Path.cwd())
    roots.append(Path.cwd() / "media/source-images")

    for root in roots:
        path = (root / candidate).expanduser().resolve()
        if path.exists():
            return path
    raise ToolError(f"source_image was not found: {raw}")


def render_card(
    *,
    shot: ShotSpec,
    source_path: Optional[Path],
    output_path: Path,
    index: int,
    total: int,
    brand: str,
    tagline: str,
) -> Dict[str, Any]:
    source_image = _open_image(source_path, shot, index)
    background = _cover_image(source_image, (VIDEO_WIDTH, VIDEO_HEIGHT))
    background = background.filter(ImageFilter.GaussianBlur(30))
    background = ImageEnhance.Brightness(background).enhance(0.33)
    background = ImageEnhance.Contrast(background).enhance(1.25)
    canvas = background.convert("RGBA")

    overlay = Image.new("RGBA", canvas.size, (3, 9, 22, 192))
    canvas.alpha_composite(overlay)
    _draw_glow(canvas, (-250, 120, 440, 820), (0, 153, 255, 88), 90)
    _draw_glow(canvas, (690, 340, 1290, 1120), (25, 210, 255, 58), 110)
    _draw_glow(canvas, (-160, 1300, 560, 2140), (0, 105, 230, 56), 120)

    draw = ImageDraw.Draw(canvas)
    accent = (69, 196, 255, 235)
    text_primary = (244, 250, 255, 255)
    text_secondary = (187, 214, 232, 255)
    panel_fill = (4, 14, 31, 218)
    panel_outline = (54, 177, 255, 150)

    draw.rounded_rectangle((64, 62, 1016, 132), radius=35, fill=(4, 17, 39, 216), outline=panel_outline, width=2)
    brand_font = _load_font(34, bold=True)
    scene_font = _load_font(27, bold=False)
    draw.text((94, 82), brand, font=brand_font, fill=text_primary)
    scene_label = f"Scene {index:02d} / {total:02d}"
    scene_width, _ = _text_size(draw, scene_label, scene_font)
    draw.text((986 - scene_width, 86), scene_label, font=scene_font, fill=text_secondary)

    headline_font, headline_lines = _fit_wrapped_text(
        draw,
        shot.headline,
        max_width=936,
        max_lines=3,
        start_size=76,
        min_size=52,
        bold=True,
    )
    headline_bottom = _draw_lines(
        draw,
        (72, 184),
        headline_lines,
        headline_font,
        text_primary,
        line_gap=16,
        shadow=True,
    )
    underline_y = headline_bottom + 14
    draw.rounded_rectangle((72, underline_y, 250, underline_y + 7), radius=4, fill=accent)

    frame = (82, 500, 998, 1262)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((frame[0] + 8, frame[1] + 14, frame[2] + 8, frame[3] + 14), radius=32, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow)
    draw.rounded_rectangle(frame, radius=34, fill=(4, 11, 24, 242), outline=panel_outline, width=3)
    draw.rounded_rectangle((100, 518, 980, 1244), radius=28, fill=(9, 18, 34, 255))
    _paste_rounded(canvas, source_image, (112, 530, 968, 1232), radius=24)

    body_panel = (82, 1324, 998, 1656)
    draw.rounded_rectangle(body_panel, radius=30, fill=panel_fill, outline=(54, 177, 255, 125), width=2)
    body_font, body_lines = _fit_wrapped_text(
        draw,
        shot.body,
        max_width=820,
        max_lines=4,
        start_size=44,
        min_size=32,
        bold=False,
    )
    _draw_lines(draw, (130, 1382), body_lines, body_font, text_secondary, line_gap=14, shadow=False)

    footer_font = _load_font(29, bold=True)
    footer_width, _ = _text_size(draw, tagline, footer_font)
    footer_x = max(54, (VIDEO_WIDTH - footer_width) // 2)
    draw.text((footer_x + 2, 1800 + 3), tagline, font=footer_font, fill=(0, 0, 0, 150))
    draw.text((footer_x, 1800), tagline, font=footer_font, fill=(222, 244, 255, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", optimize=True)
    return {
        "index": index,
        "output_path": str(output_path),
        "source_image": str(source_path) if source_path else "",
        "headline": shot.headline,
        "body": shot.body,
    }


def render_cards(
    spec: VideoSpec,
    *,
    output_dir: Path,
    source_root: Optional[Path],
    brand: str,
    tagline: str,
) -> List[Dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_dir = spec.spec_path.parent if spec.spec_path is not None else None
    cards: List[Dict[str, Any]] = []
    for ordinal, shot in enumerate(spec.shots, start=1):
        source_path = _resolve_source_image(shot.source_image, spec_dir=spec_dir, source_root=source_root)
        output_path = output_dir / f"{ordinal:03d}.png"
        cards.append(
            render_card(
                shot=shot,
                source_path=source_path,
                output_path=output_path,
                index=ordinal,
                total=len(spec.shots),
                brand=brand,
                tagline=tagline,
            )
        )
    return cards


def _ffmpeg_bin() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise ToolError("ffmpeg is required. Install it with Homebrew (`brew install ffmpeg`) or your OS package manager.")
    return binary


def _ffprobe_bin() -> str:
    binary = shutil.which("ffprobe")
    if not binary:
        raise ToolError("ffprobe is required. It is installed with ffmpeg.")
    return binary


def _probe_duration_seconds(path: Path) -> float:
    completed = _run(
        [
            _ffprobe_bin(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    try:
        return max(0.1, float((completed.stdout or "").strip()))
    except ValueError as exc:
        raise ToolError(f"Could not read audio duration for {path}") from exc


def _probe_media(path: Path) -> Dict[str, Any]:
    completed = _run([_ffprobe_bin(), "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)])
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ToolError(f"Could not read media metadata for {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ToolError(f"Unexpected ffprobe payload for {path}")
    return payload


def _copy_audio_file(input_path: Path, output_dir: Path) -> Path:
    if not input_path.exists():
        raise ToolError(f"Audio file was not found: {input_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix or ".m4a"
    output_path = output_dir / f"narration{suffix}"
    shutil.copy2(input_path, output_path)
    return output_path


def _synthesize_with_say(text_file: Path, output_dir: Path, *, voice: str, rate: Optional[int]) -> Path:
    say_bin = shutil.which("say")
    if not say_bin:
        raise ToolError("macOS `say` was not found. Use `--tts-provider speaches`, `--tts-provider silent`, or `--audio-file`.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "narration.aiff"
    command = [say_bin]
    if voice:
        command.extend(["-v", voice])
    if rate is not None:
        command.extend(["-r", str(rate)])
    command.extend(["-f", str(text_file), "-o", str(output_path)])
    _run(command)
    return output_path


def _synthesize_with_speaches(
    text: str,
    output_dir: Path,
    *,
    base_url: str,
    model: str,
    voice: str,
    response_format: str,
    api_key: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_format = response_format.strip().lower() or "mp3"
    output_path = output_dir / f"narration.{clean_format}"
    endpoint = base_url.rstrip("/") + "/audio/speech"
    body = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": clean_format,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(endpoint, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
    try:
        with urlopen(request, timeout=300) as response:
            output_path.write_bytes(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip() or str(exc)
        raise ToolError(f"Speaches TTS failed: {detail}") from exc
    except URLError as exc:
        raise ToolError(f"Speaches TTS failed: {exc}") from exc
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ToolError("Speaches TTS returned an empty audio file.")
    return output_path


def _make_silent_audio(output_dir: Path, duration_seconds: float) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "narration.m4a"
    _run(
        [
            _ffmpeg_bin(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{duration_seconds:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
    )
    return output_path


def prepare_audio(spec: VideoSpec, args: argparse.Namespace, bundle_dir: Path) -> Dict[str, Any]:
    audio_dir = bundle_dir / "assets/audio"
    narration_file = bundle_dir / "narration.txt"
    narration_file.parent.mkdir(parents=True, exist_ok=True)
    narration_file.write_text(spec.narration_text.strip() + "\n", encoding="utf-8")

    if args.audio_file:
        output_path = _copy_audio_file(Path(args.audio_file).expanduser().resolve(), audio_dir)
        provider = "audio-file"
    elif args.tts_provider == "say":
        output_path = _synthesize_with_say(narration_file, audio_dir, voice=args.tts_voice, rate=args.tts_rate)
        provider = "say"
    elif args.tts_provider == "speaches":
        output_path = _synthesize_with_speaches(
            spec.narration_text,
            audio_dir,
            base_url=args.speaches_url,
            model=args.speaches_model,
            voice=args.tts_voice or DEFAULT_SPEACHES_VOICE,
            response_format=args.speaches_format,
            api_key=args.speaches_api_key,
        )
        provider = "speaches"
    elif args.tts_provider == "silent":
        duration = max(args.seconds_per_scene * len(spec.shots), 1.0)
        output_path = _make_silent_audio(audio_dir, duration)
        provider = "silent"
    else:
        raise ToolError(f"Unsupported TTS provider: {args.tts_provider}")

    duration = _probe_duration_seconds(output_path)
    return {
        "provider": provider,
        "output_path": str(output_path),
        "duration_seconds": duration,
        "voice": args.tts_voice or "",
        "rate": args.tts_rate,
        "narration_file": str(narration_file),
    }


def _quote_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _write_concat_file(path: Path, cards: Sequence[Path], seconds_per_card: float) -> None:
    lines: List[str] = []
    for card in cards:
        lines.append(f"file '{_quote_concat_path(card)}'")
        lines.append(f"duration {seconds_per_card:.8f}")
    if cards:
        lines.append(f"file '{_quote_concat_path(cards[-1])}'")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_video(
    *,
    card_paths: Sequence[Path],
    audio_path: Path,
    output_path: Path,
    audio_duration: float,
    work_dir: Path,
) -> Dict[str, Any]:
    if not card_paths:
        raise ToolError("No cards were rendered.")
    if not audio_path.exists():
        raise ToolError(f"Audio path was not found: {audio_path}")
    seconds_per_card = max(audio_duration / len(card_paths), 0.5)
    concat_path = work_dir / "concat.txt"
    _write_concat_file(concat_path, card_paths, seconds_per_card)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            _ffmpeg_bin(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-i",
            str(audio_path),
            "-vf",
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={VIDEO_FPS},setsar=1,format=yuv420p",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-r",
            str(VIDEO_FPS),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-profile:v",
            "high",
            "-level:v",
            "4.0",
            "-movflags",
            "+faststart",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]
    )
    if not output_path.exists():
        raise ToolError("ffmpeg finished without creating a video.")
    metadata = _probe_media(output_path)
    return {
        "output_path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "seconds_per_card": seconds_per_card,
        "metadata": metadata,
    }


def _validate_render_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
    streams = metadata.get("streams") if isinstance(metadata.get("streams"), list) else []
    video = next((stream for stream in streams if isinstance(stream, Mapping) and stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in streams if isinstance(stream, Mapping) and stream.get("codec_type") == "audio"), {})
    checks = [
        {"name": "video_codec", "ok": str(video.get("codec_name") or "").lower() == "h264", "detail": str(video.get("codec_name") or "")},
        {
            "name": "dimensions",
            "ok": int(video.get("width") or 0) == VIDEO_WIDTH and int(video.get("height") or 0) == VIDEO_HEIGHT,
            "detail": f"{video.get('width', 0)}x{video.get('height', 0)}",
        },
        {"name": "pixel_format", "ok": str(video.get("pix_fmt") or "") == "yuv420p", "detail": str(video.get("pix_fmt") or "")},
        {"name": "audio_codec", "ok": str(audio.get("codec_name") or "").lower() == "aac", "detail": str(audio.get("codec_name") or "")},
    ]
    return {"ok": all(item["ok"] for item in checks), "checks": checks}


def build_video(args: argparse.Namespace) -> Dict[str, Any]:
    spec_path = Path(args.spec).expanduser().resolve()
    spec = load_video_spec(spec_path)
    brand = args.brand or spec.brand
    tagline = args.tagline or spec.tagline
    output_root = Path(args.output_dir).expanduser().resolve()
    bundle_name = f"{spec.output_name}-{_timestamp_slug()}"
    bundle_dir = output_root / "bundles" / bundle_name
    cards_dir = bundle_dir / "cards"
    source_root = Path(args.source_root).expanduser().resolve() if args.source_root else None

    audio = prepare_audio(spec, args, bundle_dir)
    cards = render_cards(spec, output_dir=cards_dir, source_root=source_root, brand=brand, tagline=tagline)
    card_paths = [Path(str(item["output_path"])) for item in cards]
    output_path = Path(args.output).expanduser().resolve() if args.output else bundle_dir / f"{spec.output_name}.mp4"
    render = compile_video(
        card_paths=card_paths,
        audio_path=Path(str(audio["output_path"])),
        output_path=output_path,
        audio_duration=float(audio["duration_seconds"]),
        work_dir=bundle_dir,
    )
    validation = _validate_render_metadata(render["metadata"])
    manifest = {
        "tool": TOOL_NAME,
        "action": "build",
        "status": "ok",
        "project_name": spec.project_name,
        "bundle_dir": str(bundle_dir),
        "spec_file": str(spec_path),
        "brand": brand,
        "tagline": tagline,
        "audio": audio,
        "cards": cards,
        "render": {
            key: value for key, value in render.items() if key != "metadata"
        },
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(bundle_dir / "manifest.json", manifest)
    if not validation["ok"]:
        failed = ", ".join(item["name"] for item in validation["checks"] if not item["ok"])
        raise ToolError(f"Video rendered but validation failed: {failed}")
    return manifest


def render_cards_action(args: argparse.Namespace) -> Dict[str, Any]:
    spec_path = Path(args.spec).expanduser().resolve()
    spec = load_video_spec(spec_path)
    output_dir = Path(args.output_dir).expanduser().resolve()
    source_root = Path(args.source_root).expanduser().resolve() if args.source_root else None
    cards = render_cards(
        spec,
        output_dir=output_dir,
        source_root=source_root,
        brand=args.brand or spec.brand,
        tagline=args.tagline or spec.tagline,
    )
    return {
        "tool": TOOL_NAME,
        "action": "render-cards",
        "status": "ok",
        "project_name": spec.project_name,
        "output_dir": str(output_dir),
        "cards": cards,
    }


def validate_spec_action(args: argparse.Namespace) -> Dict[str, Any]:
    spec_path = Path(args.spec).expanduser().resolve()
    spec = load_video_spec(spec_path)
    source_root = Path(args.source_root).expanduser().resolve() if args.source_root else None
    image_checks = []
    if args.check_images:
        spec_dir = spec.spec_path.parent if spec.spec_path is not None else None
        for shot in spec.shots:
            image_path = _resolve_source_image(shot.source_image, spec_dir=spec_dir, source_root=source_root)
            image_checks.append({"index": shot.index, "source_image": str(image_path) if image_path else "", "exists": image_path is None or image_path.exists()})
    return {
        "tool": TOOL_NAME,
        "action": "validate-spec",
        "status": "ok",
        "project_name": spec.project_name,
        "shot_count": len(spec.shots),
        "narration_characters": len(spec.narration_text),
        "image_checks": image_checks,
    }


def _render_text(payload: Mapping[str, Any]) -> str:
    action = payload.get("action", "")
    if action == "build":
        render = payload.get("render") if isinstance(payload.get("render"), Mapping) else {}
        audio = payload.get("audio") if isinstance(payload.get("audio"), Mapping) else {}
        return "\n".join(
            [
                f"{DISPLAY_NAME}: build complete",
                f"Project: {payload.get('project_name', '')}",
                f"Output: {render.get('output_path', '')}",
                f"Cards: {len(payload.get('cards') or [])}",
                f"Audio: {audio.get('provider', '')} ({float(audio.get('duration_seconds') or 0):.2f}s)",
            ]
        )
    if action == "render-cards":
        return "\n".join(
            [
                f"{DISPLAY_NAME}: cards rendered",
                f"Project: {payload.get('project_name', '')}",
                f"Output: {payload.get('output_dir', '')}",
                f"Cards: {len(payload.get('cards') or [])}",
            ]
        )
    if action == "validate-spec":
        return "\n".join(
            [
                f"{DISPLAY_NAME}: spec ok",
                f"Project: {payload.get('project_name', '')}",
                f"Shots: {payload.get('shot_count', 0)}",
                f"Narration characters: {payload.get('narration_characters', 0)}",
            ]
        )
    return json.dumps(dict(payload), indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description=DESCRIPTION)
    subparsers = parser.add_subparsers(dest="action", required=True)

    build = subparsers.add_parser("build", help="Render cards, generate or attach narration, and compile a vertical MP4.")
    build.add_argument("--spec", required=True, help="JSON or YAML video spec.")
    build.add_argument("--source-root", default="", help="Optional image root for relative source_image paths.")
    build.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Root for generated bundles.")
    build.add_argument("--output", default="", help="Optional final MP4 path. Defaults inside the generated bundle.")
    build.add_argument("--brand", default="", help="Override the header brand text.")
    build.add_argument("--tagline", default="", help="Override the footer tagline.")
    build.add_argument("--audio-file", default="", help="Existing narration audio file. Skips TTS when supplied.")
    build.add_argument(
        "--tts-provider",
        choices=("say", "speaches", "silent"),
        default=os.getenv("CODEX_VIDEO_TTS_PROVIDER", "say"),
        help="Narration backend. Use `speaches` for local Kokoro/Speaches, `say` for macOS, or `silent` for tests.",
    )
    build.add_argument("--tts-voice", default=os.getenv("CODEX_VIDEO_TTS_VOICE", ""), help="Voice name/id for the selected TTS provider.")
    build.add_argument("--tts-rate", type=int, default=None, help="macOS say speech rate in words per minute.")
    build.add_argument("--speaches-url", default=os.getenv("SPEACHES_BASE_URL", DEFAULT_SPEACHES_URL), help="OpenAI-compatible Speaches base URL.")
    build.add_argument("--speaches-model", default=os.getenv("SPEACHES_TTS_MODEL", DEFAULT_SPEACHES_MODEL), help="Speaches TTS model id.")
    build.add_argument("--speaches-format", default=os.getenv("SPEACHES_TTS_FORMAT", "mp3"), help="Speaches audio response format.")
    build.add_argument("--speaches-api-key", default=os.getenv("SPEACHES_API_KEY", ""), help="Optional Bearer token for a protected TTS endpoint.")
    build.add_argument("--seconds-per-scene", type=float, default=5.0, help="Scene length used by the silent provider.")
    build.add_argument("--format", choices=("json", "text"), default="text")

    cards = subparsers.add_parser("render-cards", help="Render only the vertical PNG cards.")
    cards.add_argument("--spec", required=True, help="JSON or YAML video spec.")
    cards.add_argument("--source-root", default="", help="Optional image root for relative source_image paths.")
    cards.add_argument("--output-dir", required=True, help="Directory for 001.png, 002.png, etc.")
    cards.add_argument("--brand", default="", help="Override the header brand text.")
    cards.add_argument("--tagline", default="", help="Override the footer tagline.")
    cards.add_argument("--format", choices=("json", "text"), default="text")

    validate = subparsers.add_parser("validate-spec", help="Validate a video spec.")
    validate.add_argument("--spec", required=True, help="JSON or YAML video spec.")
    validate.add_argument("--source-root", default="", help="Optional image root for relative source_image paths.")
    validate.add_argument("--check-images", action="store_true", help="Resolve source_image paths during validation.")
    validate.add_argument("--format", choices=("json", "text"), default="text")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.action == "build":
            payload = build_video(args)
        elif args.action == "render-cards":
            payload = render_cards_action(args)
        elif args.action == "validate-spec":
            payload = validate_spec_action(args)
        else:
            raise ToolError(f"Unsupported action: {args.action}")
        status_code = 0
    except Exception as exc:
        payload = {
            "tool": TOOL_NAME,
            "action": getattr(args, "action", ""),
            "status": "error",
            "error": str(exc),
        }
        status_code = 1

    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if status_code == 0:
            print(_render_text(payload))
        else:
            print(f"{DISPLAY_NAME}: {payload['error']}", file=sys.stderr)
    return status_code


if __name__ == "__main__":
    raise SystemExit(main())
