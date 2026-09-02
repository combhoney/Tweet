# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont

def get_bold_font(font_size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, font_size)
            except Exception: pass
    return ImageFont.load_default()

def draw_centered_text(draw, center_x, center_y, text, font, fill_color):
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((center_x - (w // 2), center_y - (h // 2)), text, font=font, fill=fill_color)

def generate_dynamic_thumbnail(output_path, thumb_meta=None):
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#0f141c") # প্রিমিয়াম ডার্ক থিম
    draw = ImageDraw.Draw(img)

    if not thumb_meta: thumb_meta = {}
    top_text = thumb_meta.get("top_text", "BREAKING NEWS").upper()
    row1_text = thumb_meta.get("row1_text", "VIRAL ALERT").upper()
    row2_text = thumb_meta.get("row2_text", "Internet Shocked")
    bot_text = thumb_meta.get("bot_text", "FULL BREAKDOWN").upper()

    # ১. টপ বার (রেড ব্রেকিং নিউজ বার: 0-190px)
    draw.rectangle([0, 0, W, 190], fill="#cc0000")
    draw_centered_text(draw, W // 2, 95, top_text, get_bold_font(110), "#ffffff")

    # ২. মিডল সেকশন (১৯০-৮৮০px)
    draw.rectangle([0, 190, W, 890], fill="#ffffff")
    
    # রো ১: বোল্ড রেড হুক লাইন
    draw_centered_text(draw, W // 2, 410, row1_text, get_bold_font(210), "#d40000")
    # রো ২: বোল্ড ব্ল্যাক সাব-লাইন
    draw_centered_text(draw, W // 2, 670, row2_text, get_bold_font(150), "#000000")

    # ৩. বটম বার (৮৯০-১০৮০px)
    draw.rectangle([0, 890, W, H], fill="#0a0a0a")
    draw_centered_text(draw, W // 2, 985, bot_text, get_bold_font(105), "#ffd700")

    img.save(output_path, "JPEG", quality=100)
    print(f"🎨 [THUMBNAIL] Generated High-CTR Thumbnail: {output_path}")
