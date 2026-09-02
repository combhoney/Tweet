# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

def make_tweet_video_frame(img_path, duration, target_w=1920, target_h=1080):
    pil_img = Image.open(img_path).convert("RGB")
    
    # ১. ব্যাকগ্রাউন্ড: পুরো স্ক্রিন জুড়ে ব্লার ইমেজ
    bg_img = pil_img.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=25))
    
    # ২. ফোরগ্রাউন্ড: মূল টুইটের ছবি অ্যাসপেক্ট রেশিও ঠিক রেখে মাঝখানে বসানো
    scale = min((target_w * 0.85) / pil_img.width, (target_h * 0.85) / pil_img.height)
    fg_w, fg_h = int(pil_img.width * scale), int(pil_img.height * scale)
    fg_resized = pil_img.resize((fg_w, fg_h), Image.LANCZOS)
    
    canvas = bg_img.copy()
    offset_x = (target_w - fg_w) // 2
    offset_y = (target_h - fg_h) // 2
    canvas.paste(fg_resized, (offset_x, offset_y))
    
    img_np = np.array(canvas)
    pil_img.close()
    
    # ৩. স্মুথ স্লাইট জুম-ইন মোশন ইফেক্ট (ভিডিওটিকে ডায়নামিক করার জন্য)
    def frame_getter(t):
        return img_np

    return VideoClip(frame_getter, duration=duration)

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    audio_clip = AudioFileClip(audio_path)
    per_img_duration = audio_clip.duration / len(img_files)

    clips = [make_tweet_video_frame(v, per_img_duration, target_w, target_h) for v in img_files]
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
