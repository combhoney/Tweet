# -*- coding: utf-8 -*-
import os, re

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

# রান মোড: "breaking" অথবা "daily_top10"
RUN_MODE = os.environ.get("RUN_MODE", "breaking").strip().lower()

# 🌟 ফিক্সড ৭ ঘণ্টার টাইম উইন্ডো (গত ৭ ঘণ্টার পোস্ট ও রিঅ্যাকশন স্ক্যান হবে)
SCAN_WINDOW_HOURS = 7 

# অডিও ইঞ্জিন: "kokoro" অথবা "edge"
TTS_ENGINE = os.environ.get("TTS_ENGINE", "kokoro").strip().lower()

# আপলোড সুইচ: True হলে YouTube Public, False হলে Google Drive (Rclone)
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

VIP_HANDLES = [
    "elonmusk", "sama", "realDonaldTrump", "ylecun", "paulg",
    "saylor", "cz_binance", "VitalikButerin", "MrBeast", "pmarca", "MarioNawfal"
]

DEFAULT_BASE_TAGS = ['Breaking News', 'Twitter News', 'X Trending', 'Elon Musk', 'Tech News', 'Viral Drama']

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
