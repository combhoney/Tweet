# -*- coding: utf-8 -*-
import os, json, re

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")
CATEGORY_STATE_FILE = os.path.join(WORKSPACE_DIR, "category_state.json")

# গত ১২ ঘণ্টার পোস্ট ও কমেন্ট স্ক্যান হবে
SCAN_WINDOW_HOURS = 12

TTS_ENGINE = os.environ.get("TTS_ENGINE", "kokoro").strip().lower()
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

# 🌟 ১৪টি ক্যাটাগরির সুনির্দিষ্ট ক্রম (ধারাবাহিকভাবে একটার পর একটা ঘুরবে)
ORDERED_CATEGORIES = [
    "space",
    "tech",
    "political",
    "nba",
    "nfl",
    "soccer",
    "combat_sports",
    "f1",
    "mlb",
    "nhl",
    "tennis",
    "golf",
    "ncaaf",
    "fantasy_sports"
]

# ==================== [ ১৪টি ক্যাটাগরির হ্যান্ডেল তালিকা ] ====================
CATEGORY_HANDLES = {
    "space": [
        "SpaceX", "NASA", "elonmusk", "NASASpaceflight", "SpaceflightNow", "ISS_Research",
        "ESA", "NASAWebb", "SciGuySpace", "Erdayastronaut", "ArceneauxHayley"
    ],
    "tech": [
        "elonmusk", "sama", "ylecun", "paulg", "pmarca", "lexfridman", "satyanadella",
        "sundarpichai", "tim_cook", "BillGates", "karpathy", "gdb", "ID_AA_Carmack",
        "nearcyan", "levelsio", "fchollet", "AndrewYNg", "demishassabis", "GaryMarcus",
        "drfeifei", "tegmark", "OpenAI", "AnthropicAI", "Tesla", "SpaceX", "MKBHD",
        "jeffbezos", "bchesky", "jack", "levie", "tobi", "balajis", "garrytan", "cdixon"
    ],
    "political": [
        "realDonaldTrump", "JDVance", "VivekGRamaswamy", "BarackObama", "JoeBiden",
        "KamalaHarris", "AOC", "BernieSanders", "TuckerCarlson", "RobertKennedyJr",
        "RonDeSantis", "tedcruz", "RepMTG", "MattGaetz", "SpeakerJohnson", "GavinNewsom",
        "HillaryClinton", "TulsiGabbard", "IlhanMN", "marcorubio", "SenWarren",
        "CollinRugg", "EndWokeness", "MarioNawfal", "benshapiro", "charliekirk11"
    ],
    "nba": [
        "NBA", "ShamsCharania", "wojespn", "BleacherReport", "SportsCenter", "KingJames",
        "StephenCurry30", "KDTrey5", "Giannis_An34", "JoelEmbiid", "Dame_Lillard",
        "Luka77Doncic", "spidadmitchell", "MagicJohnson", "SHAQ", "ClutchPoints",
        "HouseHighlights", "Overtime", "TheDunkCentral", "TheSteinLine"
    ],
    "nfl": [
        "NFL", "AdamSchefter", "RapSheet", "PatrickMahomes", "TomBrady", "tkelce",
        "bakermayfield", "AaronRodgers12", "JalenHurts", "obj", "JJWatt", "DeionSanders",
        "BleacherReportNFL", "NFLonCBS", "NFLSTROUD", "AroundTheNFL", "MySportsUpdate"
    ],
    "soccer": [
        "FabrizioRomano", "David_Ornstein", "brfootball", "ChampionsLeague", "premierleague",
        "Cristiano", "neymarjr", "KMbappe", "ErlingHaaland", "lewy_official", "vinijr",
        "BellinghamJude", "ToniKroos", "MoSalah", "SkySportsNews", "goal", "Transfermarkt"
    ],
    "combat_sports": [
        "ufc", "danawhite", "ArielHelwani", "TheNotoriousMMA", "espnmma", "MMAFighting",
        "Canelo", "Tyson_Fury", "anthonyjoshua", "JonnyBones", "stylebender", "ChaelSonnen"
    ],
    "f1": [
        "F1", "LewisHamilton", "Max33Verstappen", "LandoNorris", "Charles_Leclerc",
        "SkySportsF1", "WTF1official", "RedBullRacing", "ScuderiaFerrari", "MercedesAMGF1"
    ],
    "mlb": [
        "MLB", "JeffPassan", "Ken_Rosenthal", "BRWalkoff", "TalkinBaseball_", "MikeTrout",
        "Starting9", "JonHeyman", "Feinsand", "PitchingNinja", "FoulTerritoryTV"
    ],
    "nhl": [
        "NHL", "PierreVLeBrun", "ElliotteFriedman", "SpittinChiclets", "Bardown",
        "PuckReportNHL", "FriedgeHNIC", "frank_seravalli", "BR_OpenIce"
    ],
    "tennis": [
        "atptour", "WTA", "Tennis", "JoseMorgado", "RafaelNadal", "CocoGauff",
        "BenRothenberg", "carlosalcaraz", "iga_swiatek", "DjokerNole", "TennisChannel"
    ],
    "golf": [
        "PGATOUR", "LIVGolf_League", "TigerWoods", "RoryMcIlroy", "PhilMickelson",
        "BrysonDeChambeau", "GolfDigest", "ForePlayPod", "NoLayingUp", "GolfChannel",
        "JustinThomas34", "BKoepka", "JonRahmOfficial"
    ],
    "ncaaf": [
        "CFB", "espncfb", "On3sports", "247Sports", "KirkHerbstreit", "CollegeGameDay",
        "BruceFeldmanCFB", "RJ_Young", "UnnecRoughness", "PFF_College"
    ],
    "fantasy_sports": [
        "FantasyPros", "MatthewBerryTMR", "rotowire", "PFF_Fantasy", "UnderdogFantasy",
        "SleeperHQ", "ActionNetworkHQ", "BradEvansMix", "LateRoundQB", "EstablishTheRun"
    ]
}

# ==================== [ 🔄 স্মার্ট ক্যাটাগরি রোটেশন ফাংশন ] ====================
def get_active_category():
    """
    ম্যানুয়াল ওভাররাইড না থাকলে প্রতিবার স্বয়ংক্রিয়ভাবে পরবর্তী ক্যাটাগরি বেছে নেয়
    এবং নতুন ইনডেক্স মেমোরিতে সেভ করে রাখে
    """
    forced_cat = os.environ.get("CATEGORY", "").strip().lower()
    if forced_cat in CATEGORY_HANDLES:
        return forced_cat

    last_index = -1
    if os.path.exists(CATEGORY_STATE_FILE):
        try:
            with open(CATEGORY_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                last_index = state_data.get("last_category_index", -1)
        except Exception: pass

    # পরবর্তী ক্যাটাগরি সিলেক্ট করা (রোটেশনাল ইনডেক্স)
    current_index = (last_index + 1) % len(ORDERED_CATEGORIES)
    active_category = ORDERED_CATEGORIES[current_index]

    # নতুন ইনডেক্স সেভ করা
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        with open(CATEGORY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_category_index": current_index,
                "active_category": active_category
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save category rotation state: {e}")

    print(f"\n🔄 [CATEGORY ROTATION] Selected Category #{current_index + 1}/{len(ORDERED_CATEGORIES)}: '{active_category.upper()}'")
    return active_category

DEFAULT_BASE_TAGS = ['Breaking News', 'Twitter Viral', 'X Trending', 'US News']

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
