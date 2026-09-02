# -*- coding: utf-8 -*-
import os, re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('youtube', 'v3', credentials=creds)

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

def upload_to_youtube(yt, video_file, title, thumbnail_path, description, tags):
    safe_title = re.sub(r'[\<\>]', '', str(title)).strip()[:100]
    print(f"\n📤 Uploading to YouTube: '{safe_title}'")

    # cron-job.org নিয়ন্ত্রিত হওয়ায় সরাসরি পাবলিক আপলোড হবে
    body = {
        'snippet': {
            'title': safe_title,
            'description': description if description else safe_title,
            'tags': clean_youtube_tags(tags)
        },
        'status': {
            'privacyStatus': 'public', # সাথে সাথে লাইভ
            'selfDeclaredMadeForKids': False
        }
    }

    try:
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"🎉 Video is now LIVE on YouTube! Link: https://youtu.be/{video_id}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("🖼️ Custom High-CTR Thumbnail Attached Successfully!")
            except Exception as e:
                print(f"⚠️ Thumbnail attach failed: {e}")
        return True
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False
