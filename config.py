# -*- coding: utf-8 -*-
import os, re
from datetime import datetime, timezone

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

# গত ১২ ঘণ্টার পোস্ট ও কমেন্ট স্ক্যান হবে
SCAN_WINDOW_HOURS = 12

TTS_ENGINE = os.environ.get("TTS_ENGINE", "kokoro").strip().lower()
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

# ==================== [ ১৪টি ক্যাটাগরির হ্যান্ডেল তালিকা ] ====================
CATEGORY_HANDLES = {
    # ১. Tech & AI
    "tech": [
        "elonmusk", "sama", "ylecun", "paulg", "pmarca", "lexfridman", "satyanadella",
        "sundarpichai", "tim_cook", "BillGates", "karpathy", "gdb", "ID_AA_Carmack",
        "nearcyan", "levelsio", "fchollet", "AndrewYNg", "demishassabis", "GaryMarcus",
        "drfeifei", "tegmark", "OpenAI", "AnthropicAI", "Tesla", "SpaceX", "MKBHD",
        "jeffbezos", "bchesky", "jack", "levie", "tobi", "balajis", "garrytan", "cdixon"
    ],

    # ২. Political
    "political": [
        "realDonaldTrump", "JDVance", "VivekGRamaswamy", "BarackObama", "JoeBiden",
        "KamalaHarris", "AOC", "BernieSanders", "TuckerCarlson", "RobertKennedyJr",
        "RonDeSantis", "tedcruz", "RepMTG", "MattGaetz", "SpeakerJohnson", "GavinNewsom",
        "HillaryClinton", "TulsiGabbard", "IlhanMN", "marcorubio", "SenWarren",
        "CollinRugg", "EndWokeness", "MarioNawfal", "benshapiro", "charliekirk11"
    ],

    # ৩. NBA (Basketball)
    "nba": [
        "NBA", "ShamsCharania", "wojespn", "BleacherReport", "SportsCenter", "KingJames",
        "StephenCurry30", "KDTrey5", "Giannis_An34", "JoelEmbiid", "Dame_Lillard",
        "Luka77Doncic", "spidadmitchell", "MagicJohnson", "SHAQ", "ClutchPoints",
        "HouseHighlights", "Overtime", "TheDunkCentral", "TheSteinLine"
    ],

    # ৪. NFL (American Football)
    "nfl": [
        "NFL", "AdamSchefter", "RapSheet", "PatrickMahomes", "TomBrady", "tkelce",
        "bakermayfield", "AaronRodgers12", "JalenHurts", "obj", "JJWatt", "DeionSanders",
        "BleacherReportNFL", "NFLonCBS", "NFLSTROUD", "AroundTheNFL", "MySportsUpdate"
    ],

    # ৫. World Cup (Soccer / Football)
    "soccer": [
        "FabrizioRomano", "David_Ornstein", "brfootball", "ChampionsLeague", "premierleague",
        "Cristiano", "neymarjr", "KMbappe", "ErlingHaaland", "lewy_official", "vinijr",
        "BellinghamJude", "ToniKroos", "MoSalah", "SkySportsNews", "goal", "Transfermarkt"
    ],

    # ৬. Golf
    "golf": [
        "PGATOUR", "LIVGolf_League", "TigerWoods", "RoryMcIlroy", "PhilMickelson",
        "BrysonDeChambeau", "GolfDigest", "ForePlayPod", "NoLayingUp", "GolfChannel",
        "JustinThomas34", "BKoepka", "JonRahmOfficial"
    ],

    # ৭. MLB (Baseball)
    "mlb": [
        "MLB", "JeffPassan", "Ken_Rosenthal", "BRWalkoff", "TalkinBaseball_", "MikeTrout",
        "Starting9", "JonHeyman", "Feinsand", "PitchingNinja", "FoulTerritoryTV"
    ],

    # ৮. Tennis
    "tennis": [
        "atptour", "WTA", "Tennis", "JoseMorgado", "RafaelNadal", "CocoGauff",
        "BenRothenberg", "carlosalcaraz", "iga_swiatek", "DjokerNole", "TennisChannel"
    ],

    # ৯. NCAAF (College Football)
    "ncaaf": [
        "CFB", "espncfb", "On3sports", "247Sports", "KirkHerbstreit", "CollegeGameDay",
        "BruceFeldmanCFB", "RJ_Young", "UnnecRoughness", "PFF_College"
    ],

    # ১০. NHL (Ice Hockey)
    "nhl": [
        "NHL", "PierreVLeBrun", "ElliotteFriedman", "SpittinChiclets", "Bardown",
        "PuckReportNHL", "FriedgeHNIC", "frank_seravalli", "BR_OpenIce"
    ],

    # ১১. Fantasy Sports & Betting
    "fantasy_sports": [
        "FantasyPros", "MatthewBerryTMR", "rotowire", "PFF_Fantasy", "UnderdogFantasy",
        "SleeperHQ", "ActionNetworkHQ", "BradEvansMix", "LateRoundQB", "EstablishTheRun"
    ],

    # ১২. UFC / MMA / Boxing
    "combat_sports": [
        "ufc", "danawhite", "ArielHelwani", "TheNotoriousMMA", "espnmma", "MMAFighting",
        "Canelo", "Tyson_Fury", "anthonyjoshua", "JonnyBones", "stylebender", "ChaelSonnen"
    ],

    # ১৩. Formula 1 (F1)
    "f1": [
        "F1", "LewisHamilton", "Max33Verstappen", "LandoNorris", "Charles_Leclerc",
        "SkySportsF1", "WTF1official", "RedBullRacing", "ScuderiaFerrari", "MercedesAMGF1"
    ],

    # ১৪. SpaceX, NASA & Space
    "space": [
        "SpaceX", "NASA", "elonmusk", "NASASpaceflight", "SpaceflightNow", "ISS_Research",
        "ESA", "NASAWebb", "SciGuySpace", "Erdayastronaut", "ArceneauxHayley"
    ]
}

# ==================== [ ২৮টি স্লট অটো-ম্যাপিং ইঞ্জিন ] ====================
def get_active_category():
    forced_cat = os.environ.get("CATEGORY", "").strip().lower()
    if forced_cat in CATEGORY_HANDLES:
        return forced_cat

    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    minute = now_utc.minute

    # ২৮টি স্লটের নির্দিষ্ট সময়সূচি
    if hour == 0 and minute >= 25: return "tech"
    if hour == 0: return "space"
    if hour == 1: return "golf"
    if hour == 2: return "ncaaf"
    if hour == 3: return "nfl"
    if hour == 4: return "nba"
    if hour == 5: return "mlb"
    if hour == 6: return "nhl"
    if hour == 7: return "combat_sports"
    if hour == 8: return "f1"
    if hour == 9: return "tennis"
    if hour == 10: return "soccer"
    if hour == 11: return "political"
    if hour == 12 and minute >= 25: return "tech"
    if hour == 12: return "space"
    if hour == 13: return "fantasy_sports"
    if hour == 14: return "f1"
    if hour == 15: return "soccer"
    if hour == 16 and minute >= 25: return "tennis"
    if hour == 16: return "nba"
    if hour == 17: return "mlb"
    if hour == 18 and minute >= 25: return "ncaaf"
    if hour == 18: return "nfl"
    if hour == 19: return "nhl"
    if hour == 20 and minute >= 25: return "political"
    if hour == 20: return "golf"
    if hour == 21: return "fantasy_sports"
    if hour == 22: return "combat_sports"
    if hour == 23: return "tech"

    return "tech"

DEFAULT_BASE_TAGS = ['Breaking News', 'Twitter Viral', 'X Trending', 'US News']

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
