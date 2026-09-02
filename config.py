# -*- coding: utf-8 -*-
import os, re

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

# প্রতি রানে ঠিক ১টি ভিডিও তৈরি হবে
MAX_VIDEOS_PER_RUN = 1

# ==================== [ ফিচার সুইচ / টগল বাটন ] ====================
# ১. ভয়েস সুইচ: True হলে ElevenLabs AI, False হলে সম্পূর্ণ ফ্রি Microsoft Edge-TTS
USE_ELEVENLABS = os.environ.get("USE_ELEVENLABS", "true").strip().lower() in ("true", "1", "yes")

# ২. আপলোড সুইচ: True হলে সরাসরি YouTube Public, False হলে Google Drive (Rclone)
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")

# ৩. গুগল ড্রাইভ ফোল্ডার আইডি (না দিলে ড্রাইভের রুট ফোল্ডারে সেভ হবে)
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

# ====================================================================

VIP_HANDLES = [
    "elonmusk",
    "sama",
    "realDonaldTrump",
    "ylecun",
    "paulg",
    "saylor",
    "cz_binance",
    "VitalikButerin",
    "MrBeast",
    "pmarca",
    "MarioNawfal"
]

DEFAULT_BASE_TAGS = [
    'Trending News', 'Twitter News', 'Breaking News',
    'Elon Musk', 'Tech News', 'Viral Tweets', 'X Trending'
]

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
