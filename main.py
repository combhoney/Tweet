# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from config import WORKSPACE_DIR, TMP_DIR, HISTORY_FILE, UPLOAD_TO_YOUTUBE
from tweet_hunter import hunt_and_prepare_viral_tweets
from ai_service import generate_synchronized_script
from audio_engine import synthesize_audio_segment
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_synchronized_video
from youtube_uploader import get_youtube_service, upload_to_youtube
from gdrive_uploader import upload_to_google_drive

def save_tweet_ids_to_history(id_list):
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            for tid in id_list:
                f.write(f"{tid}\n")
    except Exception: pass

def process_and_publish_videos(yt):
    if not os.path.exists(WORKSPACE_DIR): return
    os.makedirs(TMP_DIR, exist_ok=True)

    folders = [f for f in sorted(os.listdir(WORKSPACE_DIR)) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.startswith("tweet_")]

    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            info_json = os.path.join(folder_path, "tweet_info.json")
            if not os.path.exists(info_json):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            with open(info_json, "r", encoding="utf-8") as jf:
                tweet_meta = json.load(jf)

            slides_data = tweet_meta.get("slides_data", [])
            if not slides_data:
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            print(f"\n========== Processing: {folder_name} ({len(slides_data)} Synced Slides) ==========")

            # ১. প্রতিটি স্লাইড ও কমেন্টের সাথে মিলিয়ে সিঙ্কড স্ক্রিপ্ট তৈরি
            ai_data = generate_synchronized_script(slides_data)
            if not ai_data or not ai_data.get("segments"):
                print(f"🛑 Synced script generation failed for {folder_name}")
                continue

            opt_title = ai_data.get("optimized_title", "Breaking News")
            slogan = ai_data.get("thumbnail_slogan", "BREAKING NEWS ALERT! 🚨")
            desc = ai_data.get("video_description", "")
            segments = ai_data.get("segments", [])

            # ২. প্রতিটি স্লাইডের জন্য আলাদা আলাদা অডিও জেনারেশন
            paired_slides = []
            audio_success = True

            for idx, seg in enumerate(segments, start=1):
                img_path = os.path.join(folder_path, f"{seg.get('slide_id', idx)}.png")
                if not os.path.exists(img_path):
                    img_path = os.path.join(folder_path, "1.png")

                aud_path = os.path.join(TMP_DIR, f"seg_{idx}.wav")
                script_text = seg.get("script", "")
                
                print(f"  🎙️ Synthesizing Audio for Slide #{idx}: \"{script_text[:45]}...\"")
                if synthesize_audio_segment(script_text, aud_path):
                    paired_slides.append((img_path, aud_path))
                else:
                    audio_success = False
                    break

            if not audio_success or not paired_slides:
                print(f"🛑 Audio synthesis failed for {folder_name}")
                continue

            # ৩. থাম্বনেইল তৈরি
            safe_base_name = "".join(c for c in opt_title if c.isalnum() or c in (' ', '_', '-')).strip()[:45]
            if not safe_base_name: safe_base_name = f"video_{folder_name}"

            out_video = os.path.join(TMP_DIR, f"{safe_base_name}.mp4")
            thumb_path = os.path.join(TMP_DIR, f"{safe_base_name}.jpg")
            
            main_tweet_img = os.path.join(folder_path, "1.png")
            generate_dynamic_thumbnail(main_tweet_img, thumb_path, slogan)

            # ৪. ১০০% ফ্রেম-পারফেক্ট সিঙ্ক্রোনাইজড ভিডিও রেন্ডারিং
            print(f"🎬 Rendering {len(paired_slides)} 100% Synced Slides into Video...")
            render_synchronized_video(paired_slides, out_video)

            # ৫. আপলোড
            if UPLOAD_TO_YOUTUBE:
                upload_success = upload_to_youtube(yt, out_video, opt_title, thumb_path, desc, ['Breaking News', 'X Viral'])
            else:
                upload_success = upload_to_google_drive(out_video, thumb_path, opt_title)

            if upload_success:
                save_tweet_ids_to_history([tweet_meta.get("tweet_id")])
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Video Uploaded & Cleaned: {folder_name}\n")

        except Exception as e:
            print(f"❌ Error in {folder_name}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        yt_service = get_youtube_service() if UPLOAD_TO_YOUTUBE else None
        hunt_and_prepare_viral_tweets()
        process_and_publish_videos(yt_service)
    except Exception as e:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
