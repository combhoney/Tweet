# -*- coding: utf-8 -*-
import os, re

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

RUN_MODE = os.environ.get("RUN_MODE", "breaking").strip().lower()
SCAN_WINDOW_HOURS = 7 

TTS_ENGINE = os.environ.get("TTS_ENGINE", "kokoro").strip().lower()
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

# 🌟 শীর্ষ ১০০টি হাইপার-অ্যাক্টিভ, বিতর্কিত ও ভাইরাল এক্স (টুইটার) অ্যাকাউন্ট
VIP_HANDLES = [
    # --- [১. টেক, এআই ও সিলিকন ভ্যালি (২৫টি)] ---
    "elonmusk", "sama", "ylecun", "paulg", "pmarca", "lexfridman", "satyanadella",
    "sundarpichai", "tim_cook", "BillGates", "karpathy", "gdb", "ID_AA_Carmack",
    "nearcyan", "levelsio", "fchollet", "AndrewYNg", "demishassabis", "GaryMarcus",
    "drfeifei", "tegmark", "OpenAI", "AnthropicAI", "Tesla", "SpaceX",

    # --- [২. ইউএসএ পলিটিক্স ও সরকারি ব্যক্তিত্ব (২৫টি)] ---
    "realDonaldTrump", "JDVance", "VivekGRamaswamy", "BarackObama", "JoeBiden",
    "KamalaHarris", "AOC", "BernieSanders", "TuckerCarlson", "RobertKennedyJr",
    "RonDeSantis", "tedcruz", "RepMTG", "MattGaetz", "SpeakerJohnson", "GavinNewsom",
    "HillaryClinton", "TulsiGabbard", "IlhanMN", "marcorubio", "SenWarren",
    "StephenM", "GovRonDeSantis", "GlennGreenwald", "RandPaul",

    # --- [৩. আন্তর্জাতিক নেতা ও গ্লোবাল পলিটিক্স (১০টি)] ---
    "nayibbukele", "ZelenskyyUa", "narendramodi", "EmmanuelMacron", "JustinTrudeau",
    "netanyahu", "KremlinRussia_E", "Keir_Starmer", "JMilei", "vonderleyen",

    # --- [৪. ক্রিপ্টো, ফাইন্যান্স ও মার্কেট হুইলস (১৫টি)] ---
    "saylor", "cz_binance", "VitalikButerin", "CathieDWood", "APompliano",
    "PeterSchiff", "LynAldenContact", "brian_armstrong", "RaoulGMI", "charliebilello",
    "KobeissiLetter", "WClementeIII", "PlanB", "WatcherGuru", "unusual_whales",

    # --- [৫. ব্রেকিং নিউজ ও সিটিজেন জার্নালিজম (১৫টি)] ---
    "MarioNawfal", "CollinRugg", "spectatorindex", "BRICSinfo", "ZeroHedge",
    "EndWokeness", "libsoftiktok", "visegrad24", "KanekoaTheGreat", "ShitpostGateway",
    "PopBase", "Dexerto", "DailyLoud", "DiscussingFilm", "Pubity",

    # --- [৬. ইন্টারনেট ইনফ্লুয়েন্সার ও বিতর্কিত কমেন্টেটর (১০টি)] ---
    "MrBeast", "Cobratate", "JordanBPeterson", "joerogan", "PiersMorgan",
    "benshapiro", "hasanthehun", "TheBabylonBee", "KaiCenat", "LoganPaul"
]

DEFAULT_BASE_TAGS = ['Breaking News', 'Twitter News', 'X Trending', 'Tech News', 'Viral Drama', 'US News']

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
