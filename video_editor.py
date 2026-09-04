# -*- coding: utf-8 -*-
import os, math
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
    if not current_text: return
    draw = ImageDraw.Draw(canvas)
    bbox = font.getbbox(current_text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad_x, pad_y = 26, 12
    box_w, box_h = tw + pad_x * 2, th + pad_y * 2
    box_center_y = 980

    box_x1 = (target_w - box_w) // 2
    box_y1 = box_center_y - (box_h // 2)
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h

    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=14, fill="#080c10", outline="#000000", width=2)
    draw.text((target_w // 2, box_center_y), current_text, font=font, fill="#FFE600", anchor="mm")

def make_sliding_tweet_frame(img_path, duration, script_text="", target_w=1920, target_h=1080, direction="right_to_left"):
    """
    টুইট কার্ডটিকে স্ক্রিনের এক পাশ থেকে অপর পাশে দৃশ্যমান ও মাখনের মতো মসৃণ গতিতে স্লাইড করায়
    """
    raw_img = Image.open(img_path)
    cropped_card = crop_tweet_card_strict(raw_img)

    bg_img = cropped_card.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=35))
    dark_overlay = Image.new("RGB", (target_w, target_h), "#06090e")
    bg_img = Image.blend(bg_img, dark_overlay, alpha=0.40)

    # স্কেলিং: যাতে দুই পাশে ৩৫০px পর্যাপ্ত জায়গা থাকে মুভ করার জন্য
    max_card_h = int(target_h * 0.74)
    scale = min((target_w * 0.76) / cropped_card.width, max_card_h / cropped_card.height)
    base_w = int(cropped_card.width * scale)
    base_h = int(cropped_card.height * scale)
    fg_card = cropped_card.resize((base_w, base_h), Image.LANCZOS)
    
    raw_img.close()
    cropped_card.close()

    card_y = 45 + ((860 - base_h) // 2)

    # 🌟 দৃশ্যমান ও গতিশীল স্লাইডিং দূরত্ব (৩৫০ পিক্সেল মোশন)
    travel_distance = 350
    half_travel = travel_distance / 2.0

    sub_font = get_subtitle_font(44)
    subtitle_cues = prepare_subtitle_cues(script_text, duration)

    def frame_getter(t):
        raw_progress = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        # 🌟 Sinusoidal Ease-in-Out: কোনো কাঁপাকাঁপি ছাড়া ১০০% স্মুথ ত্বরণ ও মন্দন
        eased_progress = 0.5 - 0.5 * math.cos(math.pi * raw_progress)

        if direction == "right_to_left":
            # ডান পাশ থেকে শুরু হয়ে সম্পূর্ণভাবে বাম পাশে যাবে
            x_shift = (0.5 - eased_progress) * travel_distance
        else:
            # বাম পাশ থেকে শুরু হয়ে সম্পূর্ণভাবে ডান পাশে যাবে
            x_shift = (eased_progress - 0.5) * travel_distance

        canvas = bg_img.copy()
        offset_x = int(((target_w - base_w) // 2) + x_shift)
        canvas.paste(fg_card, (offset_x, card_y))

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
        
        # পর্যায়ক্রমে এক স্লাইডে Right-to-Left, পরের স্লাইডে Left-to-Right
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
