# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

def auto_crop_tweet_card(pil_img):
    try:
        bg = Image.new(pil_img.mode, pil_img.size, pil_img.getpixel((5, 5)))
        diff = ImageChops.difference(pil_img, bg)
        bbox = diff.getbbox()
        if bbox:
            w, h = pil_img.size
            x1, y1 = max(0, bbox[0] - 10), max(0, bbox[1] - 10)
            x2, y2 = min(w, bbox[2] + 10), min(h, bbox[3] + 10)
            if (x2 - x1) > 200 and (y2 - y1) > 150:
                return pil_img.crop((x1, y1, x2, y2))
    except Exception: pass
    return pil_img

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

def draw_text_with_outline(draw, pos, text, font, fill_color, outline_color, outline_width=5):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill_color, anchor="mm")

def generate_dynamic_thumbnail(tweet_img_path, output_path, slogan_text):
    """
    টপে একটি মাত্র হাই-সিটিআর স্লোগান এবং নিচে মূল টুইট কার্ডটি সুন্দরভাবে বড় করে বসায়
    """
    W, H = 1920, 1080
    
    # ১. টুইটের ছবি লোড ও ক্রপ করা
    if tweet_img_path and os.path.exists(tweet_img_path):
        raw_tweet = Image.open(tweet_img_path).convert("RGB")
        cropped_tweet = auto_crop_tweet_card(raw_tweet)
    else:
        cropped_tweet = Image.new("RGB", (1200, 600), "#15202b")

    # ২. ব্যাকগ্রাউন্ড: ব্লার ও প্রিমিয়াম ডার্ক টিন্ট
    bg = cropped_tweet.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    dark_overlay = Image.new("RGB", (W, H), "#06090e")
    bg = Image.blend(bg, dark_overlay, alpha=0.40)
    draw = ImageDraw.Draw(bg)

    # ৩. টপ স্লোগান বার (উচ্চতা: ২৪০px)
    banner_h = 230
    draw.rectangle([0, 0, W, banner_h], fill="#cc0000") # হাই-ইম্প্যাক্ট রেড ব্যানার
    draw.line([(0, banner_h), (W, banner_h)], fill="#ffd700", width=8) # গোল্ডেন হাইলাইট লাইন

    # স্লোগান ফন্ট সাইজ অ্যাডজাস্টমেন্ট
    slogan = str(slogan_text).upper().strip()
    font_size = 110
    font = get_bold_font(font_size)
    
    while font_size > 45:
        font = get_bold_font(font_size)
        bbox = font.getbbox(slogan)
        text_w = bbox[2] - bbox[0]
        if text_w <= W - 120:
            break
        font_size -= 4

    # সেন্টারে স্লোগান টেক্সট (বোল্ড হোয়াইট + ব্ল্যাক আউটলাইন)
    draw_text_with_outline(draw, (W // 2, (banner_h // 2) + 5), slogan, font, fill_color="#ffffff", outline_color="#000000", outline_width=5)

    # ৪. মূল টুইট কার্ডটি ব্যানারের নিচে বড় আকারে বসানো
    avail_w = W - 160           # ১৭৬০px চওড়া
    avail_h = H - banner_h - 80 # ~৭৭০px উচ্চতা
    
    scale = min(avail_w / cropped_tweet.width, avail_h / cropped_tweet.height)
    card_w = int(cropped_tweet.width * scale)
    card_h = int(cropped_tweet.height * scale)
    
    fg_card = cropped_tweet.resize((card_w, card_h), Image.LANCZOS)
    
    offset_x = (W - card_w) // 2
    offset_y = banner_h + ((H - banner_h - card_h) // 2)

    # টুইট কার্ডের চারপাশে প্রিমিয়াম গোল্ডেন বর্ডার
    draw.rectangle([offset_x - 6, offset_y - 6, offset_x + card_w + 6, offset_y + card_h + 6], fill="#ffd700")
    bg.paste(fg_card, (offset_x, offset_y))

    bg.save(output_path, "JPEG", quality=100)
    print(f"🎨 [THUMBNAIL] Generated Pro Thumbnail with Main Tweet & Slogan: '{slogan}'")
