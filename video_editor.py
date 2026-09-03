# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips

def crop_tweet_card_strict(pil_img):
    """
    টুইট কার্ডের চারপাশের সমস্ত সাদা ও খালি অংশ পিক্সেল স্ক্যান করে ১০০% কেটে ফেলে
    শুধুমাত্র আসল ডার্ক টুইট কার্ডটিকে নিখুঁতভাবে বের করে আনে
    """
    try:
        rgb_img = pil_img.convert("RGB")
        arr = np.array(rgb_img)
        
        # সাদা বা অতি হালকা ব্যাকগ্রাউন্ড পিক্সেল (Brightness > 235) ফিল্টার করা
        is_card = np.any(arr < 235, axis=-1)
        rows = np.where(np.any(is_card, axis=1))[0]
        cols = np.where(np.any(is_card, axis=0))[0]
        
        if len(rows) > 40 and len(cols) > 40:
            y1, y2 = max(0, rows[0] - 4), min(arr.shape[0], rows[-1] + 4)
            x1, x2 = max(0, cols[0] - 4), min(arr.shape[1], cols[-1] + 4)
            if (x2 - x1) > 200 and (y2 - y1) > 120:
                return rgb_img.crop((x1, y1, x2, y2))
    except Exception: pass
    return pil_img.convert("RGB")

def make_sliding_tweet_frame(img_path, duration, target_w=1920, target_h=1080, direction="right_to_left"):
    """
    টুইট কার্ডটিকে স্ক্রিনে বড় করে বসিয়ে স্মুথ Right-to-Left অথবা Left-to-Right স্লাইডিং করায়
    """
    raw_img = Image.open(img_path)
    cropped_card = crop_tweet_card_strict(raw_img)

    # ১. ব্যাকগ্রাউন্ড: পুরো ১৯২০x১০৮০ জুড়ে ব্লার ডার্ক ক্যানভাস
    bg_img = cropped_card.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    dark_overlay = Image.new("RGB", (target_w, target_h), "#06090e")
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.40)

    # ২. ফোরগ্রাউন্ড: মূল টুইট কার্ডটিকে স্ক্রিনের ৮৫% বড় আকারে রিসাইজ করা
    scale = min((target_w * 0.85) / cropped_card.width, (target_h * 0.85) / cropped_card.height)
    base_w = int(cropped_card.width * scale)
    base_h = int(cropped_card.height * scale)
    fg_card = cropped_card.resize((base_w, base_h), Image.LANCZOS)
    
    raw_img.close()
    cropped_card.close()

    # স্লাইডিং ড্রিফট রেঞ্জ (১২০ পিক্সেল স্মুথ প্যানিং)
    max_drift = 120

    def frame_getter(t):
        # সময় অনুযায়ী নিখুঁত প্রগ্রেস (০.০ থেকে ১.০)
        progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))

        if direction == "right_to_left":
            # ডান থেকে শুরু হয়ে ধীরে ধীরে বামে স্লাইড করবে
            x_shift = int((0.5 - progress) * max_drift)
        else:
            # বাম থেকে শুরু হয়ে ধীরে ধীরে ডানে স্লাইড করবে
            x_shift = int((progress - 0.5) * max_drift)

        canvas = bg_img.copy()
        offset_x = ((target_w - base_w) // 2) + x_shift
        offset_y = (target_h - base_h) // 2
        canvas.paste(fg_card, (offset_x, offset_y))
        
        return np.array(canvas)

    return VideoClip(frame_getter, duration=duration)

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    audio_clip = AudioFileClip(audio_path)
    
    # সবগুলো স্লাইডের মধ্যে অডিও সময় সমানভাবে ভাগ করা
    per_img_duration = audio_clip.duration / len(img_files)
    
    clips = []
    for idx, img_p in enumerate(img_files):
        # পর্যায়ক্রমে Right-to-Left এবং Left-to-Right অল্টারনেট হবে
        direction = "right_to_left" if (idx % 2 == 0) else "left_to_right"
        clip = make_sliding_tweet_frame(img_p, per_img_duration, target_w, target_h, direction=direction)
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
