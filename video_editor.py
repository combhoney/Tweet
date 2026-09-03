# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter, ImageChops
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips

def auto_crop_tweet_card(pil_img):
    """টুইট কার্ডের চারপাশের অতিরিক্ত ফাঁকা বা কালো বর্ডার স্বয়ংক্রিয়ভাবে কেটে ফেলে"""
    try:
        # ব্যাকগ্রাউন্ডের সাথে পার্থক্য বের করে মূল কার্ডের Bounding Box পাওয়া
        bg = Image.new(pil_img.mode, pil_img.size, pil_img.getpixel((5, 5)))
        diff = ImageChops.difference(pil_img, bg)
        bbox = diff.getbbox()
        if bbox:
            w, h = pil_img.size
            x1, y1 = max(0, bbox[0] - 15), max(0, bbox[1] - 15)
            x2, y2 = min(w, bbox[2] + 15), min(h, bbox[3] + 15)
            if (x2 - x1) > 250 and (y2 - y1) > 180:
                return pil_img.crop((x1, y1, x2, y2))
    except Exception: pass
    return pil_img

def make_cinematic_tweet_frame(img_path, duration, target_w=1920, target_h=1080, effect_type="zoom_in"):
    """
    টুইট কার্ডটিকে স্ক্রিনের ৮০-৮৫% জুড়ে বড় করে এবং স্মুথ Ken Burns (Zoom/Pan) মোশন যোগ করে
    """
    raw_img = Image.open(img_path).convert("RGB")
    cropped_card = auto_crop_tweet_card(raw_img)

    # ১. ব্যাকগ্রাউন্ড: পুরো ১৯২০x১০৮০ ক্যানভাস জুড়ে প্রিমিয়াম ডার্ক ব্লার ইফেক্ট
    bg_img = cropped_card.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    # হালকা ডার্ক টিন্ট যোগ করা যাতে ফোরগ্রাউন্ড আরও পপ করে
    dark_overlay = Image.new("RGB", (target_w, target_h), "#000000")
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.35)

    # ২. ফোরগ্রাউন্ড: মূল টুইট কার্ডটিকে স্ক্রিনে বড় (৮২% উচ্চতা ও প্রস্থ) আকারে সাইজ করা
    scale_base = min((target_w * 0.85) / cropped_card.width, (target_h * 0.85) / cropped_card.height)
    base_w = int(cropped_card.width * scale_base)
    base_h = int(cropped_card.height * scale_base)
    fg_card = cropped_card.resize((base_w, base_h), Image.LANCZOS)
    
    raw_img.close()
    cropped_card.close()

    def frame_getter(t):
        progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        
        # 🌟 স্মুথ জুম-ইন এবং জুম-আউট (১.০ থেকে ১.০৯ মোশন)
        if effect_type == "zoom_in":
            current_scale = 1.0 + (0.09 * progress)
            y_shift = int(15 * progress)
        elif effect_type == "zoom_out":
            current_scale = 1.09 - (0.09 * progress)
            y_shift = int(-15 * progress)
        else: # subtle pan
            current_scale = 1.04
            y_shift = int(25 * (progress - 0.5))

        cur_w = int(base_w * current_scale)
        cur_h = int(base_h * current_scale)
        
        fg_scaled = fg_card.resize((cur_w, cur_h), Image.BILINEAR)

        canvas = bg_img.copy()
        offset_x = (target_w - cur_w) // 2
        offset_y = ((target_h - cur_h) // 2) + y_shift
        canvas.paste(fg_scaled, (offset_x, offset_y))
        
        return np.array(canvas)

    return VideoClip(frame_getter, duration=duration)

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    audio_clip = AudioFileClip(audio_path)
    
    # সবগুলো স্লাইডের মধ্যে অডিওর সময় সমানভাবে ভাগ করা
    per_img_duration = audio_clip.duration / len(img_files)
    
    effects = ["zoom_in", "zoom_out", "pan"]
    clips = []
    
    for idx, img_p in enumerate(img_files):
        eff = effects[idx % len(effects)]
        clip = make_cinematic_tweet_frame(img_p, per_img_duration, target_w, target_h, effect_type=eff)
        clips.append(clip)

    final_video = concatenate_videoclips(clips).set_audio(audio_clip)

    final_video.write_videofile(
        out_file, 
        fps=30, 
        codec="libx264", 
        audio_codec="aac", 
        audio_bitrate="192k",
        threads=4, 
        preset="ultrafast",
        ffmpeg_params=[
            "-g", "60", 
            "-keyint_min", "60", 
            "-sc_threshold", "0", 
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ],
        logger=None
    )
    final_video.close()
    audio_clip.close()
    for c in clips: c.close()
