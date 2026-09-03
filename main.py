# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from config import WORKSPACE_DIR, TMP_DIR, HISTORY_FILE, UPLOAD_TO_YOUTUBE, RUN_MODE
from tweet_hunter import hunt_and_prepare_viral_tweets
from ai_service import generate_tweet_commentary, generate_daily_top10_script
from audio_engine import generate_voiceover_audio_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_video_slideshow
from youtube_uploader import get_youtube_service, upload_to_youtube
from gdrive_uploader import upload_to_google_drive

def save_tweet_ids_to_history(id_list):
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            for tid in id_list:
                f.write(f"{tid}\n")
        print(f"📝 [HISTORY] Saved {len(id_list)} Tweet ID(s) (Never repeat).")
    except Exception as e:
        print(f"⚠️ Failed to update history: {e}")

def process_and_publish_videos(yt):
    if not os.path.exists(WORKSPACE_DIR): return
    os.makedirs(TMP_DIR, exist_ok=True)

    folders = [f for f in sorted(os.listdir(WORKSPACE_DIR)) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and (f.startswith("tweet_") or f.startswith("daily_top10_"))]

    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            info_json = os.path.join(folder_path, "tweet_info.json")
            if not os.path.exists(info_json):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            with open(info_json, "r", encoding="utf-8") as jf:
                metadata = json.load(jf)

            img_files = [os.path.join(folder_path, f) for f in sorted(os.listdir(folder_path)) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not img_files:
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            mode = metadata.get("mode", "breaking")
            print(f"\n========== Processing Video: {folder_name} (Mode: {mode.upper()}) ==========")

            # ১. স্ক্রিপ্ট তৈরি
            if mode == "daily_top10":
                opt_title, script, thumb_meta, desc, tags = generate_daily_top10_script(metadata.get("tweets", []))
                tweet_ids_to_save = metadata.get("tweet_ids", [])
            else:
                author = metadata.get("author", "VIP")
                text = metadata.get("text", "")
                opt_title, script, thumb_meta, desc, tags = generate_tweet_commentary(author, text)
                tweet_ids_to_save = [metadata.get("tweet_id", folder_name)]

            if not opt_title or not script:
                print(f"🛑 Script generation failed for {folder_name}")
                continue

            # ২. চাঙ্কড অডিও তৈরি ও নিখুঁত জোড়া লাগানো
            audio_path = os.path.join(TMP_DIR, "voiceover.mp3")
            if not generate_voiceover_audio_pipeline(script, audio_path):
                print(f"🛑 Voiceover failed for {folder_name}")
                continue

            # ৩. ডায়নামিক থাম্বনেইল তৈরি
            thumb_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            generate_dynamic_thumbnail(thumb_path, thumb_meta=thumb_meta)

            # ৪. ১৬:৯ ল্যান্ডস্কেপ মোশন ভিডিও রেন্ডারিং (সবগুলো স্লাইড সহ)
            safe_title = "".join(c for c in opt_title if c.isalnum() or c in (' ', '_', '-')).strip()[:40]
            out_video = os.path.join(TMP_DIR, f"{safe_title}.mp4")
            print(f"🎬 Rendering 16:9 Dynamic Video ({len(img_files)} Slides)...")
            render_video_slideshow(audio_path, img_files, out_video, is_vertical=False)

            # ৫. আপলোড (ইউটিউব বা গুগল ড্রাইভ)
            if UPLOAD_TO_YOUTUBE:
                print("🎯 Uploading to YOUTUBE (Public)...")
                upload_success = upload_to_youtube(yt, out_video, opt_title, thumb_path, desc, tags)
            else:
                print("🎯 Uploading to GOOGLE DRIVE (Rclone)...")
                upload_success = upload_to_google_drive(out_video, thumb_path, opt_title)

            # ৬. সফল হলে হিস্ট্রিতে সেভ ও ফোল্ডার ডিলিট
            if upload_success:
                save_tweet_ids_to_history(tweet_ids_to_save)
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Video Finished & Uploaded: {folder_name}\n")

        except Exception as e:
            print(f"❌ Error in {folder_name}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print(f"\n====== [ X Viral Engine: Mode '{RUN_MODE.upper()}' ] ======\n")
    try:
        yt_service = get_youtube_service() if UPLOAD_TO_YOUTUBE else None
        hunt_and_prepare_viral_tweets()
        process_and_publish_videos(yt_service)
    except Exception as e:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized.\n======================================")
