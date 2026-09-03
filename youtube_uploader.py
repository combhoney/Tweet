# -*- coding: utf-8 -*-
import os, re
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCHEDULE_TRACKER_FILE = os.path.join("workspace", "schedule_tracker.txt")
IS_FIRST_VIDEO_IN_RUN = True

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('youtube', 'v3', credentials=creds)

def get_upload_status_dict(schedule_upload=True):
    """
    ১ম ভিডিওটি সাথে সাথে পাবলিক এবং পরবর্তী ভিডিওগুলো ৩০ মিনিট পর পর শিডিউল করবে
    """
    global IS_FIRST_VIDEO_IN_RUN
    now_utc = datetime.now(timezone.utc)

    if not schedule_upload:
        return {'privacyStatus': 'public'}

    # 🌟 ১. এই রানের ১ম ভিডিও হলে সরাসরি সাথে সাথে পাবলিক (Instant Live)
    if IS_FIRST_VIDEO_IN_RUN:
        IS_FIRST_VIDEO_IN_RUN = False
        try:
            os.makedirs(os.path.dirname(SCHEDULE_TRACKER_FILE), exist_ok=True)
            with open(SCHEDULE_TRACKER_FILE, "w", encoding="utf-8") as sf:
                sf.write(now_utc.isoformat())
        except Exception: pass

        print("📢 [YouTube Policy] 1st Video ➔ Publishing IMMEDIATELY as PUBLIC!")
        return {'privacyStatus': 'public'}

    # 🌟 ২. পরবর্তী ভিডিওগুলোর জন্য ৩০ মিনিট পর পর শিডিউল
    base_time = now_utc + timedelta(minutes=30)
    if os.path.exists(SCHEDULE_TRACKER_FILE):
        try:
            with open(SCHEDULE_TRACKER_FILE, "r", encoding="utf-8") as sf:
                last_time = datetime.fromisoformat(sf.read().strip())
                if last_time >= now_utc:
                    base_time = last_time + timedelta(minutes=30)
        except Exception: pass

    try:
        os.makedirs(os.path.dirname(SCHEDULE_TRACKER_FILE), exist_ok=True)
        with open(SCHEDULE_TRACKER_FILE, "w", encoding="utf-8") as sf:
            sf.write(base_time.isoformat())
    except Exception: pass

    schedule_iso = base_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    print(f"⏰ [YouTube Policy] Subsequent Video ➔ SCHEDULED for: {schedule_iso} (+30 min gap)")
    return {'privacyStatus': 'private', 'publishAt': schedule_iso}

def clean_youtube_tags(tags, max_chars=400):
    clean_tags = []
    curr_len = 0
    for t in tags:
        c = re.sub(r'[\<\>\"\,\n\r]', '', str(t)).strip()[:45]
        if c and c not in clean_tags:
            if curr_len + len(c) + 1 <= max_chars:
                clean_tags.append(c)
                curr_len += len(c) + 1
    return clean_tags

def upload_to_youtube(yt, video_file, title, thumbnail_path, description, tags, schedule_upload=True):
    safe_title = re.sub(r'[\<\>]', '', str(title)).strip()[:100]
    print(f"\n📤 Uploading to YouTube: '{safe_title}'")

    body = {
        'snippet': {
            'title': safe_title,
            'description': description if description else safe_title,
            'tags': clean_youtube_tags(tags)
        },
        'status': get_upload_status_dict(schedule_upload=schedule_upload)
    }

    try:
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"✅ Video Uploaded Successfully! Link: https://youtu.be/{video_id}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("🖼️ Custom Thumbnail Attached Successfully!")
            except Exception as e:
                print(f"⚠️ Thumbnail attach failed: {e}")
        return True
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False
