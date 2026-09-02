# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from config import WORKSPACE_DIR, TMP_DIR, HISTORY_FILE, UPLOAD_TO_YOUTUBE
from tweet_hunter import hunt_and_prepare_viral_tweets
from ai_service import generate_tweet_commentary
from audio_engine import generate_voiceover_audio_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_video_slideshow
from youtube_uploader import get_youtube_service, upload_to_youtube
from gdrive_uploader import upload_to_google_drive

def add_to_history(tweet_id, folder_name):
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{tweet_id}\n")
            f.write(f"{folder_name}\n")
        print(f"📝 [HISTORY] Saved Tweet ID '{tweet_id}' (Never repeat).")
    except Exception as e:
        print(f"⚠️ Failed to update history: {e}")

def process_and_publish_videos(yt):
    if not os.path.exists(WORKSPACE_DIR): return
    os.makedirs(TMP_DIR, exist_ok=True)

    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.startswith("tweet_")]

    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            info_json = os.path.join(folder_path, "tweet_info.json")
            img_path = os.path.join(folder_path, "1.png")

            if not os.path.exists(img_path) or not os.path.exists(info_json):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            with open(info_json, "r", encoding="utf-8") as jf:
                tweet_data = json.load(jf)

            tweet_id = str(tweet_data.get("tweet_id", folder_name))
            author = tweet_data.get("author", "VIP")
            tweet_text = tweet_data.get("text", "")

            print(f"\n========== Processing: {folder_name} (@{author}) ==========")

            # ১. এআই স্ক্রিপ্ট ও মেটাডেটা জেনারেশন
            opt_title, script, thumb_meta, desc, tags = generate_tweet_commentary(author, tweet_text, [img_path])
            if not opt_title or not script:
                print(f"🛑 AI Script generation failed for {folder_name}")
                continue

            # ২. চাঙ্কড অডিও সিন্থেসিস (ElevenLabs বা Edge-TTS)
            audio_path = os.path.join(TMP_DIR, "voiceover.mp3")
            if not generate_voiceover_audio_pipeline(script, audio_path):
                print(f"🛑 Voiceover failed for {folder_name}")
                continue

            # ৩. থাম্বনেইল তৈরি
            thumb_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            generate_dynamic_thumbnail(thumb_path, thumb_meta=thumb_meta)

            # ৪. ১৬:৯ ফুল এইচডি লং ভিডিও রেন্ডারিং
            safe_title = "".join(c for c in opt_title if c.isalnum() or c in (' ', '_', '-')).strip()[:40]
            out_video = os.path.join(TMP_DIR, f"{safe_title}.mp4")
            print("🎬 Rendering 16:9 Landscape Video...")
            render_video_slideshow(audio_path, [img_path], out_video, is_vertical=False)

            # 🌟 ৫. সুইচ অনুযায়ী আপলোড মেকানিজম
            if UPLOAD_TO_YOUTUBE:
                print("🎯 [Destination Switch] Uploading to YOUTUBE (Public)...")
                upload_success = upload_to_youtube(yt, out_video, opt_title, thumb_path, desc, tags)
            else:
                print("🎯 [Destination Switch] Uploading to GOOGLE DRIVE (Rclone)...")
                upload_success = upload_to_google_drive(out_video, thumb_path, opt_title)

            # ৬. সফল হলে হিস্ট্রি আপডেট ও ক্লিনআপ
            if upload_success:
                add_to_history(tweet_id, folder_name)
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Finished & Cleaned: {folder_name}\n")

        except Exception as e:
            print(f"❌ Error processing {folder_name}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("\n====== [ X Viral Video Engine Starting ] ======\n")
    try:
        yt_service = get_youtube_service() if UPLOAD_TO_YOUTUBE else None
        hunt_and_prepare_viral_tweets()
        process_and_publish_videos(yt_service)
    except Exception as e:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized.\n======================================")
