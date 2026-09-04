# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips

def get_subtitle_font(font_size=46):
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

def crop_tweet_card_strict(pil_img):
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

def prepare_subtitle_cues(script_text, total_duration):
    """স্ক্রিপ্টটিকে কথার গতির সাথে মিলিয়ে ৪-৫ শব্দের ছোট ছোট সাবটাইটেল অংশে ভাগ করে"""
    words = script_text.strip().split()
    if not words or total_duration <= 0:
        return []

    cues = []
    chunk_size = 5
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    total_words = len(words)
    current_time = 0.0

    for chunk in chunks:
        chunk_len = len(chunk.split())
        dur = (chunk_len / total_words) * total_duration
        cues.append({
            "start": current_time,
            "end": current_time + dur,
            "text": chunk
        })
        current_time += dur
    return cues

def draw_subtitle(canvas, current_text, font, target_w, target_h):
    """হলুদ টেক্সট এবং কালো ওভারলে বক্স দিয়ে সাবটাইটেল আঁকে"""
    if not current_text:
        return

    draw = ImageDraw.Draw(canvas)
    bbox = font.getbbox(current_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x = 24
    pad_y = 12
    box_w = tw + pad_x * 2
    box_h = th + pad_y * 2

    # সাবটাইটেল বক্সের পজিশন (স্ক্রিনের একদম নিচের দিকে, Y = 980)
    box_center_y = 980
    box_x1 = (target_w - box_w) // 2
    box_y1 = box_center_y - (box_h // 2)
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h

    # ১. কালো ব্যাকগ্রাউন্ড ওভারলে (রাউন্ডেড পিল বক্স)
    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=14, fill="#080c10", outline="#000000", width=2)

    # ২. উজ্জ্বল হলুদ সাবটাইটেল টেক্সট
    draw.text((target_w // 2, box_center_y), current_text, font=font, fill="#FFE600", anchor="mm")

def make_sliding_tweet_frame(img_path, duration, script_text="", target_w=1920, target_h=1080, direction="right_to_left"):
    raw_img = Image.open(img_path)
    cropped_card = crop_tweet_card_strict(raw_img)

    # ১. ব্যাকগ্রাউন্ড: ব্লার ক্যানভাস
    bg_img = cropped_card.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    dark_overlay = Image.new("RGB", (target_w, target_h), "#06090e")
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.40)

    # ২. ফোরগ্রাউন্ড: মূল টুইট কার্ডটি স্কেল করা (যাতে নিচে সাবটাইটেলের জন্য ১৫০px সম্পূর্ণ ফাঁকা থাকে)
    max_card_h = int(target_h * 0.74) # সর্বোচ্চ ৮০০ পিক্সেল উচ্চতা
    scale = min((target_w * 0.85) / cropped_card.width, max_card_h / cropped_card.height)
    base_w = int(cropped_card.width * scale)
    base_h = int(cropped_card.height * scale)
    fg_card = cropped_card.resize((base_w, base_h), Image.LANCZOS)
    
    raw_img.close()
    cropped_card.close()

    # কার্ডটিকে ওপরের অংশে সেন্টারে রাখা (Y: 40 থেকে 880 এর মধ্যে), নিচে সাবটাইটেলের সাথে কখনো ঠেকবে না
    card_y = 45 + ((860 - base_h) // 2)
    max_drift = 90

    sub_font = get_subtitle_font(44)
    subtitle_cues = prepare_subtitle_cues(script_text, duration)

    def frame_getter(t):
        progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        if direction == "right_to_left":
            x_shift = int((0.5 - progress) * max_drift)
        else:
            x_shift = int((progress - 0.5) * max_drift)

        canvas = bg_img.copy()
        offset_x = ((target_w - base_w) // 2) + x_shift
        canvas.paste(fg_card, (offset_x, card_y))

        # বর্তমান সময় অনুযায়ী সাবটাইটেল টেক্সট খুঁজে আঁকা
        active_text = ""
        for cue in subtitle_cues:
            if cue["start"] <= t <= cue["end"]:
                active_text = cue["text"]
                break

        if active_text:
            draw_subtitle(canvas, active_text, sub_font, target_w, target_h)

        return np.array(canvas)

    return VideoClip(frame_getter, duration=duration)

def render_synchronized_video(paired_slides, out_file):
    """
    paired_slides = [ (img_path, aud_path, script_text), ... ]
    """
    target_w, target_h = 1920, 1080
    video_clips = []

    for idx, item in enumerate(paired_slides):
        if len(item) == 3:
            img_path, aud_path, script_text = item
        else:
            img_path, aud_path = item
            script_text = ""

        audio_clip = AudioFileClip(aud_path)
        seg_duration = audio_clip.duration
        
        direction = "right_to_left" if (idx % 2 == 0) else "left_to_right"
        v_clip = make_sliding_tweet_frame(img_path, seg_duration, script_text=script_text, target_w=target_w, target_h=target_h, direction=direction)
        v_clip = v_clip.set_audio(audio_clip)
        video_clips.append(v_clip)

    final_video = concatenate_videoclips(video_clips)
    final_video.write_videofile(
        out_file, fps=30, codec="libx264", audio_codec="aac",
        audio_bitrate="192k", threads=4, preset="ultrafast",
        ffmpeg_params=["-g", "60", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None
    )
    final_video.close()
    for c in video_clips: c.close()
