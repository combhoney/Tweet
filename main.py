# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from config import WORKSPACE_DIR, TMP_DIR, HISTORY_FILE, UPLOAD_TO_YOUTUBE, get_active_category
from tweet_hunter import hunt_category_tweets_for_compilation
from ai_service import generate_synchronized_script
from audio_engine import synthesize_audio_segment
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_story_segment_clip, render_and_merge_all_stories_to_video
from youtube_uploader import get_youtube_service, upload_to_youtube
from gdrive_uploader import upload_to_google_drive

def save_tweet_ids_to_history(id_list):
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            for tid in id_list:
                f.write(f"{tid}\n")
    except Exception: pass

def run_compilation_pipeline(yt):
    if not os.path.exists(WORKSPACE_DIR): return
    os.makedirs(TMP_DIR, exist_ok=True)

    active_cat = get_active_category()
    story_folders = [f for f in sorted(os.listdir(WORKSPACE_DIR)) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.startswith("story_")]

    if not story_folders:
        print(f"⏩ No approved stories found for category '{active_cat.upper()}'. Skipping run.")
        return

    print(f"\n=======================================================")
    print(f"🚀 Processing & Merging {len(story_folders)} Stories for Category: '{active_cat.upper()}'")
    print(f"=======================================================\n")

    rendered_story_clips = []
    processed_tweet_ids = []
    top_viral_story = None
    max_likes = -1

    for story_idx, folder_name in enumerate(story_folders, start=1):
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            info_json = os.path.join(folder_path, "tweet_info.json")
            if not os.path.exists(info_json): continue

            with open(info_json, "r", encoding="utf-8") as jf:
                tweet_meta = json.load(jf)

            slides_data = tweet_meta.get("slides_data", [])
            if not slides_data: continue

            print(f"--- [Story #{story_idx}/{len(story_folders)}] Generating Script for @{tweet_meta.get('author')} ---")
            ai_data = generate_synchronized_script(slides_data)
            if not ai_data or not ai_data.get("segments"):
                continue

            segments = ai_data.get("segments", [])
            paired_slides = []

            for s_idx, seg in enumerate(segments, start=1):
                img_path = os.path.join(folder_path, f"{seg.get('slide_id', s_idx)}.png")
                if not os.path.exists(img_path): img_path = os.path.join(folder_path, "1.png")

                aud_path = os.path.join(TMP_DIR, f"story_{story_idx}_seg_{s_idx}.wav")
                if synthesize_audio_segment(seg.get("script", ""), aud_path):
                    paired_slides.append((img_path, aud_path, seg.get("script", "")))

            if paired_slides:
                story_clip = render_story_segment_clip(paired_slides)
                rendered_story_clips.append(story_clip)
                processed_tweet_ids.append(tweet_meta.get("tweet_id"))

                # সবচেয়ে বেশি ভাইরাল টুইটটি থাম্বনেইলের জন্য ট্র্যাক করা
                if tweet_meta.get("likes", 0) > max_likes:
                    max_likes = tweet_meta.get("likes", 0)
                    top_viral_story = {
                        "img": os.path.join(folder_path, "1.png"),
                        "author": tweet_meta.get("author"),
                        "slogan": ai_data.get("thumbnail_slogan", "BREAKING RECAP! 🔥"),
                        "title": ai_data.get("optimized_title")
                    }

        except Exception as e:
            print(f"❌ Error processing story '{folder_name}': {e}")
            traceback.print_exc()

    if not rendered_story_clips:
        print("❌ No story clips could be generated.")
        return

    # 🌟 সবগুলো সেগমেন্ট জোড়া লাগিয়ে ১টি একক মেগা ভিডিও তৈরি
    cat_title = active_cat.upper()
    master_title = f"{cat_title} UNFILTERED: Top Controversies & Breaking Moments (12H Recap) 🚨"
    if top_viral_story and top_viral_story.get("title"):
        master_title = f"{cat_title}: {top_viral_story.get('title')}"[:95]

    safe_name = "".join(c for c in master_title if c.isalnum() or c in (' ', '_', '-')).strip()[:40]
    final_video_file = os.path.join(TMP_DIR, f"{safe_name}.mp4")
    final_thumb_file = os.path.join(TMP_DIR, f"{safe_name}.jpg")

    # থাম্বনেইল তৈরি (সবচেয়ে ভাইরাল টুইটের ছবি দিয়ে)
    thumb_img = top_viral_story["img"] if top_viral_story else os.path.join(TMP_DIR, "thumb.png")
    thumb_slogan = top_viral_story["slogan"] if top_viral_story else f"{cat_title} BREAKING ALERT! 🚨"
    generate_dynamic_thumbnail(thumb_img, final_thumb_file, thumb_slogan)

    # ভিডিও রেন্ডার
    render_and_merge_all_stories_to_video(rendered_story_clips, final_video_file)

    # আপলোড
    desc = f"Comprehensive 12-Hour Recap of the biggest viral debates, breaking news, and controversies across {cat_title}."
    if UPLOAD_TO_YOUTUBE:
        print("🎯 Uploading Single 12-Hour Compilation Video to YOUTUBE...")
        success = upload_to_youtube(yt, final_video_file, master_title, final_thumb_file, desc, [cat_title, 'Recap', 'Viral X'])
    else:
        print("🎯 Uploading Single 12-Hour Compilation Video to GOOGLE DRIVE...")
        success = upload_to_google_drive(final_video_file, final_thumb_file, master_title)

    if success:
        save_tweet_ids_to_history(processed_tweet_ids)
        for f in story_folders:
            shutil.rmtree(os.path.join(WORKSPACE_DIR, f), ignore_errors=True)
        print(f"\n🎉 [SUCCESS] 12-Hour {cat_title} Mega Video Successfully Uploaded & Cleaned!\n")

if __name__ == "__main__":
    try:
        yt_service = get_youtube_service() if UPLOAD_TO_YOUTUBE else None
        hunt_category_tweets_for_compilation()
        run_compilation_pipeline(yt_service)
    except Exception as e:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
