from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter


TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def resize_to_16_9(img: Image.Image, width: int = TARGET_WIDTH, height: int = TARGET_HEIGHT) -> Image.Image:
    """Crops and resizes an image to exactly 16:9 aspect ratio (default 1280x720)."""
    target_ratio = width / height
    orig_w, orig_h = img.size
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        # Image is wider than 16:9 - crop sides
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img_cropped = img.crop((left, 0, left + new_w, orig_h))
    else:
        # Image is taller than 16:9 - crop top/bottom
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img_cropped = img.crop((0, top, orig_w, top + new_h))

    return img_cropped.resize((width, height), Image.Resampling.LANCZOS)


def _get_font(size: int) -> ImageFont.ImageFont:
    """Attempts to load standard system fonts, falling back to PIL default font."""
    font_names = [
        "arialbd.ttf",  # Windows Arial Bold
        "impact.ttf",   # Impact
        "arial.ttf",    # Arial
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def compose_thumbnail(
    image_path: Path,
    output_path: Path,
    headline_text: str,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
) -> Path:
    """
    Takes an input frame, crops to 1280x720, overlays high-contrast bold headline text
    with a dark gradient/banner backdrop for maximum legibility, and saves to disk.
    """
    with Image.open(image_path) as orig_img:
        img = orig_img.convert("RGBA")
        img = resize_to_16_9(img, width, height)

        if headline_text and headline_text.strip():
            # Format text: uppercase, max 6 words per line if long
            text = headline_text.strip()
            words = text.split()
            if len(words) > 6:
                mid = len(words) // 2
                text = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])

            # Create an overlay layer for text and background badge
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # Determine font size dynamically
            font_size = 56 if len(text) < 30 else 44
            font = _get_font(font_size)

            # Calculate text size using multiline_textbbox
            bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # Banner padding and position (placed in lower third of thumbnail)
            pad_x = 30
            pad_y = 20
            margin_bottom = 50

            box_w = text_w + (pad_x * 2)
            box_h = text_h + (pad_y * 2)

            box_x1 = (width - box_w) // 2
            box_y1 = height - margin_bottom - box_h
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h

            # Draw dark translucent rounded rectangle for contrast
            badge_color = (0, 0, 0, 180)  # 70% opacity black
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=15, fill=badge_color)

            # Draw text with subtle shadow
            text_x = box_x1 + pad_x
            text_y = box_y1 + pad_y

            # Shadow offset
            draw.multiline_text((text_x + 2, text_y + 2), text, font=font, fill=(0, 0, 0, 255), align="center")
            # Primary bold white text
            draw.multiline_text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255), align="center")

            # Composite text overlay onto thumbnail image
            img = Image.alpha_composite(img, overlay)

        # Convert back to RGB for JPEG saving
        rgb_img = img.convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rgb_img.save(output_path, format="JPEG", quality=92)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Circle-crop helpers (used by thumbnail_template.py)
# ─────────────────────────────────────────────────────────────────────────────

def crop_to_circle(img: Image.Image, size: int) -> Image.Image:
    """
    Resizes `img` to `size × size` and applies a circular alpha mask.
    Returns an RGBA image where pixels outside the circle are transparent.
    """
    # Resize to square, maintaining centre crop to avoid stretching
    src = img.convert("RGBA")
    src_w, src_h = src.size
    short = min(src_w, src_h)
    left = (src_w - short) // 2
    top = (src_h - short) // 2
    src = src.crop((left, top, left + short, top + short))
    src = src.resize((size, size), Image.Resampling.LANCZOS)

    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)

    # Apply mask
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(src, (0, 0), mask)
    return result


def paste_circle_image(
    base: Image.Image,
    circle_img: Image.Image,
    center_x: int,
    center_y: int,
    border_color: Tuple[int, int, int] = (255, 255, 255),
    border_width: int = 6,
) -> Image.Image:
    """
    Pastes a pre-cropped circular RGBA image onto `base` (RGBA) at the given
    centre coordinates. Draws a solid coloured ring border around the circle.
    Returns the composited RGBA image.
    """
    base = base.convert("RGBA")
    size = circle_img.size[0]
    radius = size // 2

    draw = ImageDraw.Draw(base)

    # Draw border ring (slightly larger ellipse)
    bx1 = center_x - radius - border_width
    by1 = center_y - radius - border_width
    bx2 = center_x + radius + border_width
    by2 = center_y + radius + border_width
    draw.ellipse([bx1, by1, bx2, by2], fill=(*border_color, 255))

    # Paste circular tutor image
    paste_x = center_x - radius
    paste_y = center_y - radius
    base.paste(circle_img, (paste_x, paste_y), circle_img)

    return base
