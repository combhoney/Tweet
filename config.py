# -*- coding: utf-8 -*-
import os, re
from datetime import datetime, timezone

WORKSPACE_DIR = "workspace"
TMP_DIR = "temp_assets"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

SCAN_WINDOW_HOURS = 12

TTS_ENGINE = os.environ.get("TTS_ENGINE", "kokoro").strip().lower()
UPLOAD_TO_YOUTUBE = os.environ.get("UPLOAD_TO_YOUTUBE", "true").strip().lower() in ("true", "1", "yes")
GDRIVE_PARENT_FOLDER_ID = os.environ.get("GDRIVE_PARENT_FOLDER_ID", "").strip()

# ==================== [ ৩টি ক্যাটাগরির ১০০টি করে মোট ৩০০টি হ্যান্ডেল ] ====================
CATEGORY_HANDLES = {
    # 💻 ১. Tech & AI (১০০টি অ্যাকাউন্ট: সিলিকন ভ্যালি, এআই ল্যাব, গবেষক ও টেক মিডিয়া)
    "tech": [
        "elonmusk", "sama", "ylecun", "paulg", "pmarca", "lexfridman", "satyanadella",
        "sundarpichai", "tim_cook", "BillGates", "karpathy", "gdb", "ID_AA_Carmack",
        "nearcyan", "levelsio", "fchollet", "AndrewYNg", "demishassabis", "GaryMarcus",
        "drfeifei", "tegmark", "OpenAI", "AnthropicAI", "Tesla", "SpaceX", "MKBHD",
        "jeffbezos", "bchesky", "jack", "levie", "tobi", "dharmesh", "alexandr_wang",
        "hardmaru", "schmidhuberai", "chrmanning", "ilyasut", "AravSrinivas", "sama",
        "balajis", "garrytan", "cdixon", "jason", "rabois", "chamath", "allinpodcast",
        "DavidSacks", "theRealKallaway", "LinusTech", "UnboxTherapy", "verge", "TechCrunch",
        "WIRED", "arstechnica", "mashable", "engadget", "CNET", "mrwhosetheboss",
        "Dave2D", "iJustine", "AustinNotJerry", "zollotech", "mkbhd", "tldraw",
        "swyx", "shadcn", "rauchg", "stolinski", "kentcdodds", "wesbos", "dan_abramov",
        "t3dotgg", "GoogleAI", "MetaAI", "DeepMind", "nvidia", "Microsoft", "Apple",
        "AMD", "Intel", "HuggingFace", "Midjourney", "xai", "MistralAI", "cursor_ai",
        "v0", "perplexity_ai", "runwayml", "replicate", "Scale_AI", "LangChainAI",
        "llama_index", "weights_biases", "github", "docker", "supabase", "vercel"
    ],

    # ⚽ ২. Sports (১০০টি অ্যাকাউন্ট: এনবিএ, এনএফএল, সকার, ইউএফসি, এফ১ ও ব্রেকিং জার্নালিস্ট)
    "sports": [
        "FabrizioRomano", "ShamsCharania", "AdamSchefter", "wojespn", "RapSheet",
        "David_Ornstein", "ChrisHaynes", "WindhorstESPN", "Ken_Rosenthal", "JeffPassan",
        "ArielHelwani", "bokamotoESPN", "BleacherReport", "espn", "SportsCenter",
        "brfootball", "BarstoolSports", "TalkSPORT", "ComplexSports", "TheAthletic",
        "SkySportsNews", "FOXSports", "CBSFootball", "BleacherReportNFL", "BRWalkoff",
        "HouseHighlights", "Overtime", "ClutchPoints", "NBA", "NFL", "premierleague",
        "ChampionsLeague", "ufc", "F1", "MLS", "MLB", "NHL", "WWE", "LaLiga",
        "SerieA", "KingJames", "StephenCurry30", "KDTrey5", "Giannis_An34", "JoelEmbiid",
        "Dame_Lillard", "Luka77Doncic", "spidadmitchell", "MagicJohnson", "SHAQ",
        "PatrickMahomes", "TomBrady", "tkelce", "bakermayfield", "AaronRodgers12",
        "JalenHurts", "obj", "JJWatt", "DeionSanders", "Cristiano", "neymarjr",
        "KMbappe", "ErlingHaaland", "lewy_official", "vinijr", "BellinghamJude",
        "ToniKroos", "MoSalah", "TheNotoriousMMA", "danawhite", "JonnyBones",
        "stylebender", "francis_ngannou", "Canelo", "Tyson_Fury", "anthonyjoshua",
        "LewisHamilton", "Max33Verstappen", "LandoNorris", "Charles_Leclerc", "RealMadrid",
        "FCBarcelona", "ManUtd", "Arsenal", "LFC", "ChelseaFC", "ManCity",
        "SkySportsF1", "espnmma", "BRKicks", "NBAonTNT", "CBSSports", "SI_wrestling",
        "SkyFootball", "goal", "Squawka", "OptaJoe", "Transfermarkt"
    ],

    # 🏛️ ৩. Political (১০০টি অ্যাকাউন্ট: মার্কিন রাজনীতি, কংগ্রেস, হোয়াইট হাউস, বিশ্বনেতা ও কমেন্টেটর)
    "political": [
        "realDonaldTrump", "JDVance", "VivekGRamaswamy", "BarackObama", "JoeBiden",
        "KamalaHarris", "AOC", "BernieSanders", "TuckerCarlson", "RobertKennedyJr",
        "RonDeSantis", "tedcruz", "RepMTG", "MattGaetz", "SpeakerJohnson", "GavinNewsom",
        "HillaryClinton", "TulsiGabbard", "IlhanMN", "marcorubio", "SenWarren",
        "CollinRugg", "EndWokeness", "MarioNawfal", "nayibbukele", "ZelenskyyUa",
        "WhiteHouse", "VP", "POTUS", "StephenM", "GlennGreenwald", "RandPaul",
        "RepThomasMassie", "Jim_Jordan", "ChuckSchumer", "LeaderMcConnell", "SenSchumer",
        "SenSanders", "SenTedCruz", "RepDanCrenshaw", "RepRoKhanna", "RepRaskin",
        "benshapiro", "charliekirk11", "MegynKelly", "piersmorgan", "MattWalshBlog",
        "JordanBPeterson", "Cernovich", "RubinReport", "hasanthehun", "michaelshermer",
        "KanekoaTheGreat", "libsoftiktok", "GOP", "TheDemocrats", "FoxNews", "CNN",
        "MSNBC", "politico", "thehill", "BreitbartNews", "DailyWire", "AP", "Reuters",
        "WSJpolitics", "dcexaminer", "axios", "semafor", "narendramodi", "EmmanuelMacron",
        "JustinTrudeau", "netanyahu", "KremlinRussia_E", "Keir_Starmer", "JMilei",
        "vonderleyen", "RishiSunak", "GiorgiaMeloni", "spectatorindex", "BRICSinfo",
        "ZeroHedge", "visegrad24", "SenFettermanPA", "GovWhitmer", "GovAbbott",
        "GregAbbott_TX", "SenDuckworth", "SenTimScott", "NikkiHaley", "Mike_Pence",
        "ChrisChristie", "SarahHuckabee", "GovPritzker", "HawleyMO", "TomCottonAR"
    ]
}

def get_active_category():
    forced_cat = os.environ.get("CATEGORY", "").strip().lower()
    if forced_cat in CATEGORY_HANDLES:
        return forced_cat

    cur_hour = datetime.now(timezone.utc).hour
    if cur_hour in [23, 0, 1, 2, 11, 12, 13, 14]:
        return "tech"
    elif cur_hour in [3, 4, 5, 6, 15, 16, 17, 18]:
        return "sports"
    else:
        return "political"

DEFAULT_BASE_TAGS = ['Breaking News', 'Twitter Viral', 'X Trending', 'US News', 'Top Drama']

def get_all_microlink_keys():
    raw_keys = os.environ.get("MICROLINK_API_KEYS", os.environ.get("MICROLINK_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
