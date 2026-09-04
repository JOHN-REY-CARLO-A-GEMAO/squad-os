#!/usr/bin/env python3
"""
Generates assets/social-preview.png — the 1280x640 repo card image.

Usage:
    python assets/make_social_preview.py

Requires: Pillow (pip install Pillow)
Output:   assets/social-preview.png
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
BG_TOP = (7, 11, 24)        # #070B18
BG_BOTTOM = (15, 30, 62)    # #0F1E3E
ACCENT = (34, 211, 238)     # cyan
VIOLET = (139, 92, 246)     # violet
GREEN = (52, 211, 153)      # green
TEXT = (240, 244, 255)
MUTED = (148, 163, 184)
SOFT = (199, 210, 254)      # indigo-200

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "social-preview.png")
REPO_URL = "github.com/JOHN-REY-CARLO-A-GEMAO/squad-os"


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Load DejaVu with sensible fallbacks so the script works anywhere."""
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        "/usr/share/fonts/truetype/dejavu/" + name,
        "/usr/share/fonts/dejavu/" + name,
        "/Library/Fonts/" + name,
        os.path.join(os.path.dirname(__file__), name),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def vertical_gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=color)
    return img


def draw_network(draw, seed=7):
    """A subtle node-graph motif suggesting DAG orchestration."""
    rnd = random.Random(seed)
    nodes = []
    for x in range(60, W - 40, 64):
        for y in range(40, H - 40, 64):
            if rnd.random() < 0.42:
                nodes.append((x + rnd.randint(-18, 18), y + rnd.randint(-18, 18)))

    for i, (x, y) in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            nx, ny = nodes[j]
            dist = math.hypot(nx - x, ny - y)
            if dist < 95:
                alpha = int(70 * (1 - dist / 95))
                draw.line([(x, y), (nx, ny)], fill=(ACCENT[0], ACCENT[1], ACCENT[2], alpha), width=1)

    for x, y in nodes:
        color = GREEN if (x + y) % 3 == 0 else (ACCENT if (x + y) % 3 == 1 else VIOLET)
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)


def chip(draw, x, y, text, font_big, font_small):
    text_font = font_small if len(text) > 22 else font_big
    pad_x, pad_y = 26, 14
    w = draw.textlength(text, font=text_font) + pad_x * 2
    h = text_font.size + pad_y * 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=(18, 28, 54, 255),
                           outline=(ACCENT[0] // 3, ACCENT[1] // 3, ACCENT[2] // 3), width=2)
    draw.text((x + pad_x, y + pad_y), text, font=text_font, fill=SOFT)
    return w


def main():
    img = vertical_gradient(BG_TOP, BG_BOTTOM).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw_network(draw)
    img = Image.alpha_composite(img, layer)

    draw = ImageDraw.Draw(img)

    # Wordmark
    big = font(128)
    draw.text((76, 84), "SquadOS", font=big, fill=TEXT)
    draw.rectangle([80, 236, 80 + 150, 244], fill=ACCENT)

    # Tagline
    draw.text((76, 268), "The OS for AI agent squads", font=font(42), fill=SOFT)

    # Feature chips
    chip_font_big = font(27)
    chip_font_small = font(24)
    cx, cy = 76, 352
    for label in (".sqad Agent Store", "DAG Orchestration"):
        w = chip(draw, cx, cy, label, chip_font_big, chip_font_small)
        cx += w + 20
    cx, cy = 76, 436
    for label in ("30+ Sandboxed Tools", "Local-first · Ollama"):
        w = chip(draw, cx, cy, label, chip_font_big, chip_font_small)
        cx += w + 20

    # GitHub link block (star mark + URL)
    def star(cx, cy, r, color):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        draw.polygon(pts, fill=color)

    star(95, 556, 22, ACCENT)
    draw.text((130, 540), REPO_URL, font=font(22), fill=ACCENT)
    draw.text((130, 572), "Apache-2.0  ·  Python 3.10+  ·  LiteLLM / Ollama",
              font=font(18, bold=False), fill=MUTED)

    img.convert("RGB").save(OUT, "PNG")
    print(f"Wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
