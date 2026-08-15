"""
thumbnail_template.py — V4.1 Branded Educational Thumbnail Generator

Generates a deterministic 1280×720 YouTube thumbnail using Pillow.
The AI provides content (class, subject, topic, etc.); this module
handles all visual rendering — no image-generation API required.

Layout:
    ┌──────────────────────────────────────────────┐
    │  [BG COLOR + SUBTLE PATTERN]                 │
    │                                              │
    │  CLASS IX              ┌─────────────────┐   │
    │  MATHS                 │   TUTOR PHOTO   │   │
    │                        │    (circle)     │   │
    │  LINEAR                └─────────────────┘   │
    │  POLYNOMIALS                                 │
    │                                              │
    │  [ NCERT EXERCISE ]              [52:49]     │
    └──────────────────────────────────────────────┘
"""

import math
import random
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from utils.image_utils import crop_to_circle, paste_circle_image

# ─────────────────────────────────────────────────────────────────────────────
# Canvas dimensions
# ─────────────────────────────────────────────────────────────────────────────
W, H = 1280, 720

# ─────────────────────────────────────────────────────────────────────────────
# Subject colour system — configurable in ONE place
# Keys are lowercase stripped subject strings.
# Each value: (bg_dark, bg_light, accent_yellow, text_white)
# bg_dark   → left-side deep colour
# bg_light  → right-side lighter gradient colour
# accent    → series badge / highlight colour (usually yellow/gold)
# ─────────────────────────────────────────────────────────────────────────────
SUBJECT_COLORS: dict[str, dict] = {
    "maths": {
        "bg_dark":  (15,  55, 140),   # deep navy blue
        "bg_light": (30,  90, 200),   # brighter blue
        "accent":   (255, 210,  0),   # golden yellow
        "pattern":  "geometry",
    },
    "mathematics": {
        "bg_dark":  (15,  55, 140),
        "bg_light": (30,  90, 200),
        "accent":   (255, 210,  0),
        "pattern":  "geometry",
    },
    "biology": {
        "bg_dark":  (10, 100,  40),   # deep forest green
        "bg_light": (25, 155,  60),   # medium green
        "accent":   (255, 230,  50),
        "pattern":  "organic",
    },
    "physics": {
        "bg_dark":  (130,  20,  20),  # deep red
        "bg_light": (200,  50,  30),  # orange-red
        "accent":   (255, 200,   0),
        "pattern":  "rays",
    },
    "chemistry": {
        "bg_dark":  (90,  10, 120),   # deep purple
        "bg_light": (140,  30, 180),  # violet
        "accent":   (255, 220,  20),
        "pattern":  "circles",
    },
    "science": {
        "bg_dark":  (10,  80, 120),   # teal-blue
        "bg_light": (20, 130, 170),
        "accent":   (255, 215,   0),
        "pattern":  "circles",
    },
    "english": {
        "bg_dark":  (60,  40,  10),   # warm dark brown
        "bg_light": (110,  75,  25),
        "accent":   (255, 200,  50),
        "pattern":  "lines",
    },
    "history": {
        "bg_dark":  (80,  40,   5),
        "bg_light": (130,  75,  20),
        "accent":   (255, 200,  60),
        "pattern":  "lines",
    },
    "geography": {
        "bg_dark":  (0,   90,  80),
        "bg_light": (0,  140, 120),
        "accent":   (255, 220,   0),
        "pattern":  "circles",
    },
    "default": {
        "bg_dark":  (20,  80, 100),   # teal
        "bg_light": (35, 130, 155),
        "accent":   (255, 210,   0),
        "pattern":  "circles",
    },
}


def _get_subject_colors(subject: Optional[str]) -> dict:
    """Returns colour config for the given subject (case-insensitive, with fallback)."""
    if not subject:
        return SUBJECT_COLORS["default"]
    key = subject.strip().lower()
    return SUBJECT_COLORS.get(key, SUBJECT_COLORS["default"])


# ─────────────────────────────────────────────────────────────────────────────
# Font helpers
# ─────────────────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    "arialbd.ttf",          # Windows — Arial Bold
    "impact.ttf",           # Windows — Impact
    "arial.ttf",            # Windows — Arial
    "DejaVuSans-Bold.ttf",  # Linux
    "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf",
]

_FONT_REGULAR_CANDIDATES = [
    "arial.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
]


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Loads the best available system font at the requested size."""
    candidates = _FONT_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    # Ultimate fallback — PIL default (fixed size, ignores `size`)
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _draw_gradient_background(draw: ImageDraw.ImageDraw, dark: tuple, light: tuple) -> None:
    """Draws a left-to-right horizontal gradient from dark to light colour."""
    for x in range(W):
        ratio = x / W
        r = int(dark[0] + (light[0] - dark[0]) * ratio)
        g = int(dark[1] + (light[1] - dark[1]) * ratio)
        b = int(dark[2] + (light[2] - dark[2]) * ratio)
        draw.line([(x, 0), (x, H)], fill=(r, g, b))


def _draw_geometry_pattern(draw: ImageDraw.ImageDraw, color: tuple) -> None:
    """Subtle geometry circles and arcs for Maths."""
    c = (*color, 25)  # very low opacity
    # Large background circles
    for cx, cy, r in [(950, 150, 200), (1100, 500, 150), (750, 620, 100), (200, 600, 80)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 40), width=2)
    # Grid dots
    for gx in range(700, W, 60):
        for gy in range(0, H, 60):
            draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(*color, 30))


def _draw_organic_pattern(draw: ImageDraw.ImageDraw, color: tuple) -> None:
    """Subtle organic arcs for Biology."""
    for i, (cx, cy, r) in enumerate([(900, 200, 180), (1050, 450, 130), (800, 580, 90)]):
        draw.arc([cx - r, cy - r, cx + r, cy + r], start=i * 60, end=i * 60 + 200,
                 fill=(*color, 35), width=3)
    for cx, cy, r in [(950, 120, 60), (1100, 580, 45)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 30), width=2)


def _draw_rays_pattern(draw: ImageDraw.ImageDraw, color: tuple) -> None:
    """Subtle ray lines for Physics."""
    cx, cy = 1000, 360
    for angle_deg in range(0, 360, 20):
        angle = math.radians(angle_deg)
        ex = cx + int(math.cos(angle) * 350)
        ey = cy + int(math.sin(angle) * 350)
        draw.line([(cx, cy), (ex, ey)], fill=(*color, 20), width=1)
    draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], outline=(*color, 40), width=2)


def _draw_circles_pattern(draw: ImageDraw.ImageDraw, color: tuple) -> None:
    """Concentric circles for Chemistry/Science/default."""
    for cx, cy, r in [(960, 360, 250), (960, 360, 180), (960, 360, 110), (1150, 150, 100)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 30), width=1)


def _draw_lines_pattern(draw: ImageDraw.ImageDraw, color: tuple) -> None:
    """Diagonal lines for English/History."""
    for x in range(600, W + 200, 60):
        draw.line([(x, 0), (x - 200, H)], fill=(*color, 20), width=1)


def _draw_background_pattern(draw: ImageDraw.ImageDraw, pattern: str, light_color: tuple) -> None:
    dispatch = {
        "geometry": _draw_geometry_pattern,
        "organic":  _draw_organic_pattern,
        "rays":     _draw_rays_pattern,
        "circles":  _draw_circles_pattern,
        "lines":    _draw_lines_pattern,
    }
    fn = dispatch.get(pattern, _draw_circles_pattern)
    fn(draw, light_color)


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    max_height: int,
    color: tuple,
    max_font_size: int = 90,
    min_font_size: int = 28,
    bold: bool = True,
    line_spacing: int = 10,
) -> int:
    """
    Draws `text` starting at (x, y), constrained to max_width × max_height.
    Automatically wraps words and reduces font size until it fits.
    Returns the bottom Y coordinate of the drawn text block.
    """
    font_size = max_font_size

    while font_size >= min_font_size:
        font = _load_font(font_size, bold=bold)

        # Word-wrap
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Measure total height
        line_bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
        line_heights = [bb[3] - bb[1] for bb in line_bboxes]
        total_height = sum(line_heights) + line_spacing * max(0, len(lines) - 1)

        if total_height <= max_height:
            break  # It fits!

        font_size -= 4  # Try smaller

    # Draw all lines
    cur_y = y
    for i, (line, bbox) in enumerate(zip(lines, line_bboxes)):
        line_h = bbox[3] - bbox[1]
        # Subtle drop shadow
        draw.text((x + 2, cur_y + 2), line, font=font, fill=(0, 0, 0, 150))
        draw.text((x, cur_y), line, font=font, fill=color)
        cur_y += line_h + line_spacing

    return cur_y  # bottom Y of text block


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    bg_color: tuple,
    text_color: tuple = (0, 0, 0),
    font_size: int = 28,
    radius: int = 10,
    pad_x: int = 22,
    pad_y: int = 10,
) -> None:
    """Draws a rounded-rectangle badge with centred text."""
    font = _load_font(font_size, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=radius, fill=(*bg_color, 230))
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=text_color)


def _draw_duration_badge(draw: ImageDraw.ImageDraw, duration: str) -> None:
    """Draws the dark duration badge in the bottom-right corner."""
    if not duration:
        return
    font = _load_font(30, bold=True)
    bbox = draw.textbbox((0, 0), duration, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 18, 8
    margin = 18
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    x = W - bw - margin
    y = H - bh - margin
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=8, fill=(0, 0, 0, 210))
    draw.text((x + pad_x, y + pad_y), duration, font=font, fill=(255, 255, 255, 255))


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_branded_thumbnail(
    class_name: Optional[str],
    subject: Optional[str],
    topic: str,
    series_label: Optional[str],
    duration: Optional[str],
    tutor_image_path: Optional[Path],
    output_path: Path,
) -> Path:
    """
    Generates a 1280×720 branded educational YouTube thumbnail.

    Args:
        class_name:       e.g. "CLASS IX"
        subject:          e.g. "MATHS"
        topic:            e.g. "LINEAR POLYNOMIALS"
        series_label:     e.g. "NCERT EXERCISE" (optional)
        duration:         e.g. "52:49" or "01:06:59" (optional)
        tutor_image_path: Path to tutor PNG/JPG (optional — circle region left empty if None)
        output_path:      Where to save the final JPEG

    Returns:
        Path to the saved thumbnail.
    """
    colors = _get_subject_colors(subject)
    bg_dark  = colors["bg_dark"]
    bg_light = colors["bg_light"]
    accent   = colors["accent"]
    pattern  = colors["pattern"]

    # ── 1. Base canvas ──────────────────────────────────────────────────────
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    _draw_gradient_background(draw, bg_dark, bg_light)
    _draw_background_pattern(draw, pattern, bg_light)

    # ── 2. Vertical accent bar on the left edge ──────────────────────────────
    draw.rectangle([0, 0, 10, H], fill=(*accent, 200))

    # ── 3. Layout zones ──────────────────────────────────────────────────────
    # Left text zone: x 40→720, y 60→660
    TEXT_X       = 50
    TEXT_Y_START = 70
    TEXT_MAX_W   = 660
    TEXT_MAX_H   = 560

    # Tutor circle: centred at (960, 310), radius 195
    TUTOR_CX = 960
    TUTOR_CY = 310
    TUTOR_R  = 195
    TUTOR_SIZE = TUTOR_R * 2  # diameter

    # ── 4. Text content ──────────────────────────────────────────────────────
    WHITE  = (255, 255, 255, 255)
    YELLOW = (*accent, 255)

    cur_y = TEXT_Y_START

    # 4a. CLASS NAME (e.g. "CLASS IX") — smaller, slightly muted
    if class_name:
        class_text = class_name.strip().upper()
        font_class = _load_font(52, bold=True)
        # Semi-transparent white
        draw.text((TEXT_X + 2, cur_y + 2), class_text, font=font_class, fill=(0, 0, 0, 100))
        draw.text((TEXT_X, cur_y), class_text, font=font_class, fill=(220, 220, 220, 255))
        bbox = draw.textbbox((TEXT_X, cur_y), class_text, font=font_class)
        cur_y = bbox[3] + 8

    # 4b. SUBJECT (e.g. "MATHS") — large, accent yellow
    if subject:
        subj_text = subject.strip().upper()
        font_subj = _load_font(80, bold=True)
        draw.text((TEXT_X + 3, cur_y + 3), subj_text, font=font_subj, fill=(0, 0, 0, 130))
        draw.text((TEXT_X, cur_y), subj_text, font=font_subj, fill=YELLOW)
        bbox = draw.textbbox((TEXT_X, cur_y), subj_text, font=font_subj)
        cur_y = bbox[3] + 18

    # 4c. Horizontal divider line
    draw.rectangle([TEXT_X, cur_y, TEXT_X + 400, cur_y + 3], fill=(*accent, 160))
    cur_y += 18

    # 4d. TOPIC — auto-wrapping + auto font-size reduction (largest text block)
    topic_text = topic.strip().upper() if topic else "VIDEO LESSON"
    remaining_h = H - 130 - cur_y  # leave room for series badge + bottom margin
    cur_y = _draw_fitted_text(
        draw=draw,
        text=topic_text,
        x=TEXT_X,
        y=cur_y,
        max_width=TEXT_MAX_W,
        max_height=max(remaining_h, 120),
        color=WHITE,
        max_font_size=96,
        min_font_size=30,
        bold=True,
        line_spacing=8,
    )
    cur_y += 20

    # 4e. SERIES LABEL badge (e.g. "NCERT EXERCISE")
    if series_label:
        _draw_badge(
            draw,
            text=series_label.strip().upper(),
            x=TEXT_X,
            y=min(cur_y, H - 100),
            bg_color=accent,
            text_color=(10, 10, 10),
            font_size=28,
            radius=8,
            pad_x=20,
            pad_y=9,
        )

    # ── 5. Tutor photo circle ────────────────────────────────────────────────
    if tutor_image_path and Path(tutor_image_path).exists():
        try:
            with Image.open(tutor_image_path) as tutor_raw:
                circle = crop_to_circle(tutor_raw, TUTOR_SIZE)
            canvas = paste_circle_image(
                base=canvas,
                circle_img=circle,
                center_x=TUTOR_CX,
                center_y=TUTOR_CY,
                border_color=accent,
                border_width=8,
            )
            draw = ImageDraw.Draw(canvas)  # refresh draw after paste
        except Exception:
            # If anything goes wrong, draw a placeholder circle
            _draw_placeholder_circle(draw, TUTOR_CX, TUTOR_CY, TUTOR_R, accent)
    else:
        _draw_placeholder_circle(draw, TUTOR_CX, TUTOR_CY, TUTOR_R, accent)

    # ── 6. Subtle right-side vignette (darkens extreme right for contrast) ───
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(80):
        alpha = int(i * 1.2)
        vd.rectangle([W - 80 + i, 0, W - 80 + i + 1, H], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, vignette)
    draw = ImageDraw.Draw(canvas)

    # ── 7. Duration badge ────────────────────────────────────────────────────
    if duration:
        _draw_duration_badge(draw, duration)

    # ── 8. Save ──────────────────────────────────────────────────────────────
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, format="JPEG", quality=93)

    return output_path


def _draw_placeholder_circle(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    accent: tuple,
) -> None:
    """Draws an empty placeholder circle when no tutor photo is available."""
    # Outer ring
    draw.ellipse(
        [cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8],
        outline=(*accent, 180),
        width=6,
    )
    # Inner fill (semi-transparent)
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(255, 255, 255, 18),
    )
    # Icon text
    font = _load_font(48, bold=False)
    label = "TUTOR"
    bbox = draw.textbbox((0, 0), label, font=font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - lw // 2, cy - lh // 2), label, font=font, fill=(255, 255, 255, 120))
