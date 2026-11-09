# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from config import WORKSPACE_DIR, TMP_DIR, HISTORY_FILE, UPLOAD_TO_YOUTUBE, get_active_category
from tweet_hunter import hunt_category_shorts_story
from ai_service import generate_shorts_script
from audio_engine import synthesize_audio_segment
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_shorts_video
from youtube_uploader import get_youtube_service, upload_to_youtube
from gdrive_uploader import upload_to_google_drive

def save_tweet_id_to_history(tid):
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{tid}\n")
    except Exception: pass

def run_shorts_pipeline(yt):
    if not os.path.exists(WORKSPACE_DIR): return
    os.makedirs(TMP_DIR, exist_ok=True)

    active_cat = get_active_category()
    story_folders = [f for f in sorted(os.listdir(WORKSPACE_DIR)) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.startswith(f"shorts_{active_cat}_")]

    if not story_folders:
        print(f"⏩ No approved Shorts story found for '{active_cat.upper()}'. Skipping run.")
        return

    folder_name = story_folders[0]
    folder_path = os.path.join(WORKSPACE_DIR, folder_name)

    try:
        info_json = os.path.join(folder_path, "tweet_info.json")
        with open(info_json, "r", encoding="utf-8") as jf:
            tweet_meta = json.load(jf)

        slides_data = tweet_meta.get("slides_data", [])
        print(f"\n🎬 Generating 9:16 Shorts for Category: '{active_cat.upper()}' (@{tweet_meta.get('author')})")

        # ১. শর্টস স্ক্রিপ্ট তৈরি
        ai_data = generate_shorts_script(slides_data, active_category=active_cat)
        if not ai_data or not ai_data.get("segments"):
            print("🛑 Shorts script generation failed.")
            return

        opt_title = ai_data.get("optimized_title", f"{active_cat.upper()} Controversy #shorts")
        if "#shorts" not in opt_title.lower():
            opt_title = f"{opt_title} #shorts"

        desc = ai_data.get("video_description", f"Trending {active_cat} moment #shorts #viral")
        slogan = ai_data.get("thumbnail_slogan", f"{active_cat.upper()} ALERT!")
        segments = ai_data.get("segments", [])

        # ২. অডিও সিন্থেসিস
        paired_slides = []
        for s_idx, seg in enumerate(segments, start=1):
            img_path = os.path.join(folder_path, f"{seg.get('slide_id', s_idx)}.png")
            if not os.path.exists(img_path): img_path = os.path.join(folder_path, "1.png")

            aud_path = os.path.join(TMP_DIR, f"shorts_seg_{s_idx}.wav")
            if synthesize_audio_segment(seg.get("script", ""), aud_path):
                paired_slides.append((img_path, aud_path, seg.get("script", "")))

        if not paired_slides:
            print("🛑 Audio synthesis failed.")
            return

        # ৩. ৯:১৬ শর্টস ভিডিও ফাইল নির্ধারণ
        safe_name = "".join(c for c in opt_title if c.isalnum() or c in (' ', '_', '-')).strip()[:40]
        final_video_file = os.path.join(TMP_DIR, f"{safe_name}.mp4")
        final_thumb_file = os.path.join(TMP_DIR, f"{safe_name}.jpg")

        # থাম্বনেইল তৈরি
        main_img = os.path.join(folder_path, "1.png")
        generate_dynamic_thumbnail(main_img, final_thumb_file, slogan)

        # ৪. ৯:১৬ শর্টস ভিডিও রেন্ডারিং
        print(f"🎬 Rendering 9:16 Vertical Short with {len(paired_slides)} Slides...")
        render_shorts_video(paired_slides, final_video_file)

        # ৫. আপলোড (ইউটিউব শর্টস বা গুগল ড্রাইভ)
        if UPLOAD_TO_YOUTUBE:
            print("🎯 Uploading to YOUTUBE SHORTS...")
            success = upload_to_youtube(yt, final_video_file, opt_title, final_thumb_file, desc, [active_cat, 'shorts', 'viral'])
        else:
            print("🎯 Uploading to GOOGLE DRIVE...")
            success = upload_to_google_drive(final_video_file, final_thumb_file, opt_title)

        if success:
            save_tweet_id_to_history(tweet_meta.get("tweet_id"))
            shutil.rmtree(folder_path, ignore_errors=True)
            print(f"🎉 [SUCCESS] Pure {active_cat.upper()} Short Uploaded Successfully!\n")

    except Exception as e:
        print(f"❌ Error processing Short: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        yt_service = get_youtube_service() if UPLOAD_TO_YOUTUBE else None
        hunt_category_shorts_story()
        run_shorts_pipeline(yt_service)
    except Exception as e:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
