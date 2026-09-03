# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips

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

def make_sliding_tweet_frame(img_path, duration, target_w=1920, target_h=1080, direction="right_to_left"):
    raw_img = Image.open(img_path)
    cropped_card = crop_tweet_card_strict(raw_img)

    bg_img = cropped_card.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    dark_overlay = Image.new("RGB", (target_w, target_h), "#06090e")
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.40)

    scale = min((target_w * 0.85) / cropped_card.width, (target_h * 0.85) / cropped_card.height)
    base_w = int(cropped_card.width * scale)
    base_h = int(cropped_card.height * scale)
    fg_card = cropped_card.resize((base_w, base_h), Image.LANCZOS)
    
    raw_img.close()
    cropped_card.close()

    max_drift = 100

    def frame_getter(t):
        progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        if direction == "right_to_left":
            x_shift = int((0.5 - progress) * max_drift)
        else:
            x_shift = int((progress - 0.5) * max_drift)

        canvas = bg_img.copy()
        offset_x = ((target_w - base_w) // 2) + x_shift
        offset_y = (target_h - base_h) // 2
        canvas.paste(fg_card, (offset_x, offset_y))
        return np.array(canvas)

    return VideoClip(frame_getter, duration=duration)

def render_synchronized_video(paired_slides, out_file):
    """
    🌟 প্রতিটি স্লাইডের ছবির সাথে তার নিজস্ব অডিওর দৈর্ঘ্যের ১০০% ম্যাচিং করে ভিডিও বানায়
    paired_slides = [ (image_path, audio_path), (image_path, audio_path), ... ]
    """
    target_w, target_h = 1920, 1080
    video_clips = []

    for idx, (img_path, aud_path) in enumerate(paired_slides):
        audio_clip = AudioFileClip(aud_path)
        seg_duration = audio_clip.duration
        
        direction = "right_to_left" if (idx % 2 == 0) else "left_to_right"
        v_clip = make_sliding_tweet_frame(img_path, seg_duration, target_w, target_h, direction=direction)
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
