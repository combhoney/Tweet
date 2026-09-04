# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def crop_tweet_card_strict(pil_img):
    """টুইট কার্ডের চারপাশের সমস্ত সাদা বা খালি অংশ কেটে নিখুঁত কার্ড বের করে"""
    try:
        rgb_img = pil_img.convert("RGB")
        arr = np.array(rgb_img)
        is_card = np.any(arr < 230, axis=-1)
        rows = np.where(np.any(is_card, axis=1))[0]
        cols = np.where(np.any(is_card, axis=0))[0]
        if len(rows) > 30 and len(cols) > 30:
            y1, y2 = max(0, rows[0] - 2), min(arr.shape[0], rows[-1] + 2)
            x1, x2 = max(0, cols[0] - 2), min(arr.shape[1], cols[-1] + 2)
            if (x2 - x1) > 180 and (y2 - y1) > 100:
                return rgb_img.crop((x1, y1, x2, y2))
    except Exception: pass
    return pil_img.convert("RGB")

def get_minimal_font(font_size=64):
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

def generate_dynamic_thumbnail(tweet_img_path, output_path, slogan_text):
    """
    মিনিমালিস্ট ডিজাইন: উপরে মূল টুইটের বড় ছবি এবং নিচে স্লিক ফ্লোটিং টেক্সট বক্স
    """
    W, H = 1920, 1080
    
    # ১. টুইটের ছবি লোড ও নিখুঁত ক্রপ
    if tweet_img_path and os.path.exists(tweet_img_path):
        raw_tweet = Image.open(tweet_img_path).convert("RGB")
        cropped_tweet = crop_tweet_card_strict(raw_tweet)
    else:
        cropped_tweet = Image.new("RGB", (1200, 600), "#15202b")

    # ২. ব্যাকগ্রাউন্ড: শান্ত ও গভীর ডার্ক ব্লার ক্যানভাস
    bg = cropped_tweet.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=40))
    dark_overlay = Image.new("RGB", (W, H), "#070a0f")
    bg = Image.blend(bg, dark_overlay, alpha=0.55)
    draw = ImageDraw.Draw(bg)

    # ৩. উপরে মূল টুইট কার্ডটি প্লেস করা (Y: 45 থেকে 830)
    top_area_h = 780
    avail_w = W - 180          # 1740px
    avail_h = top_area_h - 40  # 740px

    scale = min(avail_w / cropped_tweet.width, avail_h / cropped_tweet.height)
    card_w = int(cropped_tweet.width * scale)
    card_h = int(cropped_tweet.height * scale)

    fg_card = cropped_tweet.resize((card_w, card_h), Image.LANCZOS)
    offset_x = (W - card_w) // 2
    offset_y = 45 + ((avail_h - card_h) // 2)

    # টুইট কার্ডের চারপাশে আধুনিক মিনিমালিস্ট বর্ডার
    border_box = [offset_x - 3, offset_y - 3, offset_x + card_w + 3, offset_y + card_h + 3]
    draw.rounded_rectangle(border_box, radius=8, outline="#2d3748", width=2)
    bg.paste(fg_card, (offset_x, offset_y))

    # ৪. নিচে স্লোগান টেক্সট বক্স (Y: 860 থেকে 1040)
    slogan = str(slogan_text).upper().strip()
    font_size = 66
    font = get_minimal_font(font_size)

    # ফন্ট সাইজ স্বয়ংক্রিয়ভাবে বক্সে ফিট করা
    max_text_w = W - 260
    while font_size > 36:
        font = get_minimal_font(font_size)
        bbox = font.getbbox(slogan)
        if (bbox[2] - bbox[0]) <= max_text_w:
            break
        font_size -= 2

    bbox = font.getbbox(slogan)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # ফ্লোটিং ক্যাপসুল বক্সের মাপ
    box_pad_x = 44
    box_pad_y = 20
    box_w = min(tw + box_pad_x * 2, W - 160)
    box_h = th + box_pad_y * 2
    box_center_y = 955

    box_x1 = (W - box_w) // 2
    box_y1 = box_center_y - (box_h // 2)
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h

    # মিনিমালিস্ট ডার্ক অবসিডিয়ান বক্স + প্রিমিয়াম গোল্ডেন আউটলাইন
    draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2],
        radius=18,
        fill="#0d1117",
        outline="#ffcc00",
        width=3
    )

    # ক্রিস্প হোয়াইট আধুনিক টেক্সট
    draw.text((W // 2, box_center_y), slogan, font=font, fill="#ffffff", anchor="mm")

    bg.save(output_path, "JPEG", quality=100)
    print(f"🎨 [THUMBNAIL] Generated Minimalist Thumbnail (Image Top, Slogan Bottom): '{slogan}'")
