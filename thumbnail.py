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

def get_bold_font(font_size=90):
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

def fit_slogan_lines(slogan, max_w):
    """
    🌟 লেখা কখনোই ছোট হবে না:
    লেখা ১ লাইনে ফিট হলে বড় ফন্টে (১০৫px) আসবে, বড় হলে সুন্দরভাবে ২ লাইনে (৮৫-৯৫px) ভাগ হয়ে যাবে
    """
    words = slogan.split()
    
    # ১. প্রথমে ১ লাইনে বড় ফন্টে ট্রাই করা (১০৫px থেকে ৮৫px)
    for fs in range(105, 84, -3):
        font = get_bold_font(fs)
        bbox = font.getbbox(slogan)
        if (bbox[2] - bbox[0]) <= max_w:
            return [slogan], font, fs

    # ২. ১ লাইনে না ধরলে ২ লাইনে বড় ফন্টে ট্রাই করা (৯৫px থেকে ৭০px)
    mid = len(words) // 2
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])
    
    for fs in range(95, 68, -3):
        font = get_bold_font(fs)
        w1 = font.getbbox(line1)[2] - font.getbbox(line1)[0]
        w2 = font.getbbox(line2)[2] - font.getbbox(line2)[0]
        if max(w1, w2) <= max_w:
            return [line1, line2], font, fs

    # ফলব্যাক
    font = get_bold_font(70)
    return [slogan], font, 70

def generate_dynamic_thumbnail(tweet_img_path, output_path, slogan_text):
    """
    মডার্ন মিনিমালিস্ট থাম্বনেইল: উপরে মূল টুইটের বড় ছবি এবং নিচে বিশাল বোল্ড টেক্সট বক্স
    """
    W, H = 1920, 1080
    
    # ১. টুইটের ছবি লোড ও নিখুঁত ক্রপ
    if tweet_img_path and os.path.exists(tweet_img_path):
        raw_tweet = Image.open(tweet_img_path).convert("RGB")
        cropped_tweet = crop_tweet_card_strict(raw_tweet)
    else:
        cropped_tweet = Image.new("RGB", (1200, 600), "#15202b")

    # ২. ব্যাকগ্রাউন্ড: গাঢ় ও আকর্ষণীয় ব্লার ক্যানভাস
    bg = cropped_tweet.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=40))
    dark_overlay = Image.new("RGB", (W, H), "#06090e")
    bg = Image.blend(bg, dark_overlay, alpha=0.52)
    draw = ImageDraw.Draw(bg)

    # ৩. নিচে লেখার মাপ ও ফন্ট নির্ধারণ (বিশাল সাইজ)
    slogan = str(slogan_text).upper().strip()
    max_box_text_w = W - 220 # 1700px
    lines, font, final_font_size = fit_slogan_lines(slogan, max_box_text_w)

    # লাইনের উচ্চতা ও প্যাডিং হিসাব
    sample_bbox = font.getbbox("AY")
    line_h = sample_bbox[3] - sample_bbox[1]
    line_spacing = 16
    total_text_h = (line_h * len(lines)) + (line_spacing * (len(lines) - 1))

    box_pad_x = 50
    box_pad_y = 24
    
    # টেক্সটের সর্বোচ্চ প্রস্থ মেপে বক্সের সাইজ করা
    max_measured_w = max([font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines])
    box_w = min(max_measured_w + (box_pad_x * 2), W - 140)
    box_h = total_text_h + (box_pad_y * 2)

    # নিচে বক্সের অবস্থান নির্ধারণ
    box_center_y = 960 if len(lines) == 1 else 940
    box_x1 = (W - box_w) // 2
    box_y1 = box_center_y - (box_h // 2)
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h

    # ৪. উপরে মূল টুইট কার্ড প্লেস করা (বক্সের সাথে যাতে না ঠেকে)
    top_avail_h = box_y1 - 50 # বক্সের ঠিক ওপর পর্যন্ত খালি জায়গা (~720px)
    top_avail_w = W - 180

    scale = min(top_avail_w / cropped_tweet.width, top_avail_h / cropped_tweet.height)
    card_w = int(cropped_tweet.width * scale)
    card_h = int(cropped_tweet.height * scale)

    fg_card = cropped_tweet.resize((card_w, card_h), Image.LANCZOS)
    offset_x = (W - card_w) // 2
    offset_y = 35 + ((top_avail_h - card_h) // 2)

    # কার্ডের চারপাশে প্রিমিয়াম স্লিক বর্ডার
    border_box = [offset_x - 3, offset_y - 3, offset_x + card_w + 3, offset_y + card_h + 3]
    draw.rounded_rectangle(border_box, radius=8, outline="#334155", width=2)
    bg.paste(fg_card, (offset_x, offset_y))

    # ৫. নিচে মিনিমালিস্ট ডার্ক ম্যাট বক্স আঁকা
    draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2],
        radius=20,
        fill="#0b0f17",      # ডিপ ম্যাট অবসিডিয়ান ব্যাকগ্রাউন্ড
        outline="#ffcc00",   # গোল্ডেন-অ্যাকসেন্ট আউটলাইন
        width=3
    )

    # ৬. বিশাল বড় ও স্পষ্ট টেক্সট আঁকা
    start_y = box_y1 + box_pad_y + (line_h // 2)
    for i, line in enumerate(lines):
        cur_y = start_y + (i * (line_h + line_spacing))
        # উজ্জ্বল হলুদ টেক্সট (#FFE600) যা সবচেয়ে বেশি দূর থেকে ও মোবাইলে দ্রুত চোখে পড়ে
        draw.text((W // 2, cur_y), line, font=font, fill="#FFE600", anchor="mm")

    bg.save(output_path, "JPEG", quality=100)
    print(f"🎨 [THUMBNAIL] Generated Big-Font Thumbnail ({final_font_size}px): '{slogan}'")
