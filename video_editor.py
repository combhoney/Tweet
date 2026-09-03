# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips

def make_dynamic_tweet_frame(img_path, duration, target_w=1920, target_h=1080, effect_type="zoom_in"):
    """
    টুইটের ছবিকে মাঝখানে রেখে ব্যাকগ্রাউন্ড ব্লার এবং স্মুথ Ken Burns (Pan/Zoom) ইফেক্ট দেয়
    """
    pil_img = Image.open(img_path).convert("RGB")
    
    # ১. ব্যাকগ্রাউন্ড: পুরো স্ক্রিন জুড়ে প্রিমিয়াম ব্লার ক্যানভাস
    bg_img = pil_img.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=30))
    
    # ২. ফোরগ্রাউন্ড: টুইট কার্ডটি ক্রিস্প আকারে সাইজ করা
    scale_base = min((target_w * 0.78) / pil_img.width, (target_h * 0.82) / pil_img.height)
    base_w, base_h = int(pil_img.width * scale_base), int(pil_img.height * scale_base)
    fg_resized = pil_img.resize((base_w, base_h), Image.LANCZOS)
    
    pil_img.close()

    def frame_getter(t):
        # সময় অনুযায়ী স্মুথ প্রগ্রেস (০.০ থেকে ১.০)
        progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        
        # জুম ইন বা জুম আউট স্কেল ফ্যাক্টর (১.০ থেকে ১.০৮ এর মধ্যে স্মুথ মোশন)
        if effect_type == "zoom_in":
            current_scale = 1.0 + (0.08 * progress)
        elif effect_type == "zoom_out":
            current_scale = 1.08 - (0.08 * progress)
        else:
            current_scale = 1.04 # স্থির হালকা স্কেল
            
        cur_w = int(base_w * current_scale)
        cur_h = int(base_h * current_scale)
        
        # বর্তমান স্কেল অনুযায়ী টুইট রিসাইজ
        fg_scaled = fg_resized.resize((cur_w, cur_h), Image.BILINEAR)
        
        # ক্যানভাসে সেন্টারে পেস্ট করা
        canvas = bg_img.copy()
        offset_x = (target_w - cur_w) // 2
        offset_y = (target_h - cur_h) // 2
        canvas.paste(fg_scaled, (offset_x, offset_y))
        
        return np.array(canvas)

    return VideoClip(frame_getter, duration=duration)

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    audio_clip = AudioFileClip(audio_path)
    
    # প্রতিটি ইমেজের জন্য সময় ভাগ করা
    per_img_duration = audio_clip.duration / len(img_files)
    
    effects = ["zoom_in", "zoom_out"]
    clips = []
    
    for idx, img_p in enumerate(img_files):
        eff = effects[idx % len(effects)] # একটার পর একটা ভিন্ন মোশন ইফেক্ট
        clip = make_dynamic_tweet_frame(img_p, per_img_duration, target_w, target_h, effect_type=eff)
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
