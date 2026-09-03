# -*- coding: utf-8 -*-
import os, json, time, requests
from PIL import Image
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, RUN_MODE
from key_manager import get_circular_key_queue
from ai_service import ai_gatekeeper_check

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

GLOBAL_VIRAL_HUBS = [
    "elonmusk", "realDonaldTrump", "MrBeast", "sama", "BarackObama",
    "MarioNawfal", "CollinRugg", "unusual_whales", "WatcherGuru",
    "PopBase", "Dexerto", "DailyLoud", "DiscussingFilm", "Pubity",
    "NASA", "OpenAI", "historyinmemes", "saylor", "cz_binance"
]

def init_workspace():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    for fname in ["history.txt", "api_key_state.json"]:
        p = os.path.join(WORKSPACE_DIR, fname)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                if fname.endswith(".json"): f.write("{}")
                else: f.write("")

def get_processed_history():
    init_workspace()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception: return set()

def fetch_live_tweets_fxtwitter_v2(handle):
    endpoints = [
        f"https://api.fxtwitter.com/2/profile/{handle}/statuses",
        f"https://api.fxtwitter.com/2/search?q=from:{handle}",
        f"https://api.fxtwitter.com/2/profile/{handle}"
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", []) or data.get("statuses", []) or data.get("tweets", [])
                if results and isinstance(results, list):
                    tweets = []
                    for t in results:
                        tid = str(t.get("id") or t.get("id_str") or "")
                        text = t.get("text", "")
                        likes = int(t.get("likes", t.get("favorite_count", 0)))
                        created_at = t.get("created_timestamp") or t.get("created_at")
                        quote_id = t.get("quote", {}).get("id") if t.get("quote") else None
                        has_media = bool(t.get("media", {}).get("photos") or t.get("media", {}).get("videos"))
                        if tid and text:
                            tweets.append({
                                "id": tid,
                                "text": text,
                                "likes": likes,
                                "author": handle,
                                "created_timestamp": created_at,
                                "quote_id": quote_id,
                                "has_media": has_media,
                                "url": f"https://x.com/{handle}/status/{tid}"
                            })
                    if tweets: return tweets
        except Exception: continue
    return []

def capture_clean_screenshot(tweet_id, output_path):
    key_queue = get_circular_key_queue("microlink", "MICROLINK_API_KEYS") or [(0, None)]
    embed_url = f"https://platform.twitter.com/embed/Tweet.html?id={tweet_id}&theme=dark"
    params = {"url": embed_url, "screenshot": "true", "scale": "2", "waitForTimeout": "3000", "hide": "[aria-label='Close'], div[role='dialog']"}
    
    for actual_idx, api_key in key_queue:
        headers = {"x-api-key": api_key} if api_key else {}
        try:
            resp = requests.get("https://api.microlink.io", params=params, headers=headers, timeout=25)
            if resp.status_code == 200:
                s_url = resp.json().get("data", {}).get("screenshot", {}).get("url")
                if s_url:
                    img_data = requests.get(s_url, timeout=20).content
                    with open(output_path, "wb") as f: f.write(img_data)
                    return True
        except Exception: continue
    return False

def crop_strict_card(pil_img):
    """সাদা মার্জিন ছাড়া শুধুমাত্র ডার্ক কার্ড কেটে নেয়"""
    try:
        rgb = pil_img.convert("RGB")
        import numpy as np
        arr = np.array(rgb)
        is_card = np.any(arr < 235, axis=-1)
        rows = np.where(np.any(is_card, axis=1))[0]
        cols = np.where(np.any(is_card, axis=0))[0]
        if len(rows) > 40 and len(cols) > 40:
            y1, y2 = max(0, rows[0] - 2), min(arr.shape[0], rows[-1] + 2)
            x1, x2 = max(0, cols[0] - 2), min(arr.shape[1], cols[-1] + 2)
            return rgb.crop((x1, y1, x2, y2))
    except Exception: pass
    return pil_img.convert("RGB")

def generate_topic_cohesive_slides(main_img_path, folder_path, has_media=False):
    """
    🌟 কোনো অপ্রাসঙ্গিক টুইট না এনে শুধুমাত্র মূল টুইট থেকেই ৪টি সুন্দর ও প্রাসঙ্গিক স্লাইড তৈরি করে:
    ১. ফুল টুইট কার্ড
    ২. টেক্সট ও বক্তব্যের ক্লোজ-আপ ভিউ
    ৩. মিডিয়া/ভিজুয়াল ফোকাস
    ৪. অথর ও এঙ্গেজমেন্ট হাইলাইট
    """
    try:
        raw_img = Image.open(main_img_path)
        cropped_card = crop_strict_card(raw_img)
        w, h = cropped_card.size

        # স্লাইড ২: টেক্সট ও কোট অংশের বড় ভিউ
        slide2 = os.path.join(folder_path, "2.png")
        if not os.path.exists(slide2):
            box2 = (0, 0, w, int(h * 0.65))
            cropped_card.crop(box2).save(slide2)

        # স্লাইড ৩: মিডিয়া বা বক্তব্যের মূল অংশ
        slide3 = os.path.join(folder_path, "3.png")
        if not os.path.exists(slide3):
            if has_media:
                box3 = (0, int(h * 0.25), w, int(h * 0.88))
            else:
                box3 = (0, int(h * 0.15), w, h)
            cropped_card.crop(box3).save(slide3)

        # স্লাইড ৪: নিচের এঙ্গেজমেন্ট ও কমিউনিটি সামারি ভিউ
        slide4 = os.path.join(folder_path, "4.png")
        if not os.path.exists(slide4):
            box4 = (0, int(h * 0.35), w, h)
            cropped_card.crop(box4).save(slide4)

        raw_img.close()
        cropped_card.close()
    except Exception as e:
        print(f"⚠️ Cohesive slide generation notice: {e}")

# ==================== [ ১. ২ ঘণ্টার ব্রেকিং নিউজ মোড (Single Topic) ] ====================
def hunt_2hour_breaking_tweets():
    init_workspace()
    history = get_processed_history()
    print("\n🔍 [TWEET HUNTER] Mode: 2-Hour Breaking News (Strict Single Topic Cohesion)...")
    
    now_ts = time.time()
    two_hours_sec = 3 * 3600
    staged_folders = []

    for handle in VIP_HANDLES:
        print(f"📡 Scanning @{handle} for fresh tweets...")
        tweets = fetch_live_tweets_fxtwitter_v2(handle)

        for tweet in tweets:
            tid = tweet["id"]
            tweet_text = tweet["text"]
            likes = tweet["likes"]
            tweet_url = tweet["url"]
            quote_id = tweet.get("quote_id")
            has_media = tweet.get("has_media", False)
            folder_name = f"tweet_{handle}_{tid}"

            if tid in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                continue

            created_ts = tweet.get("created_timestamp")
            if created_ts and isinstance(created_ts, (int, float)):
                if (now_ts - created_ts) > two_hours_sec:
                    continue

            is_worthy, reason, angle = ai_gatekeeper_check(handle, tweet_text, likes)
            if not is_worthy:
                print(f"  🚫 [GATEKEEPER REJECTED] {reason}")
                continue

            print(f"  🔥 [APPROVED] @{handle} (Likes: {likes:,}) ➔ \"{tweet_text[:60]}...\"")
            
            folder_path = os.path.join(WORKSPACE_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # স্লাইড ১: মূল টুইটের স্ক্রিনশট
            img_main = os.path.join(folder_path, "1.png")
            if capture_clean_screenshot(tid, img_main):
                slide_count = 1

                # যদি কোট টুইট থাকে (শুধুমাত্র এই নির্দিষ্ট টুইটের রেফারেন্স)
                if quote_id:
                    slide_count += 1
                    print(f"  📸 Capturing Direct Quoted Tweet (ID: {quote_id})...")
                    capture_clean_screenshot(quote_id, os.path.join(folder_path, f"{slide_count}.png"))

                # 🌟 কোনো অপ্রাসঙ্গিক অ্যাকাউন্ট না এনে এই টুইটের থেকেই ৪টি প্রাসঙ্গিক স্লাইড তৈরি
                generate_topic_cohesive_slides(img_main, folder_path, has_media=has_media)

                with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                    json.dump({
                        "mode": "breaking",
                        "tweet_id": tid,
                        "author": handle,
                        "url": tweet_url,
                        "text": tweet_text,
                        "likes": likes,
                        "editorial_angle": angle
                    }, jf, indent=2)
                
                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(f"@{handle}: {tweet_text[:60]}")

                staged_folders.append(folder_name)
                print(f"  ✅ Staged Cohesive Video for: {folder_name}")

    print(f"\n🎯 Total {len(staged_folders)} single-topic breaking video(s) staged.\n")
    return staged_folders

# ==================== [ ২. ২৪ ঘণ্টার প্ল্যাটফর্ম-ওয়াইড টপ ১০ মেগা মোড ] ====================
def hunt_daily_top10_viral_tweets():
    init_workspace()
    history = get_processed_history()
    print("\n🌍 [GLOBAL VIRAL HUNTER] Scanning Entire X Platform for Top 10 Viral Moments...")

    candidate_tweets = []
    now_ts = time.time()
    day_sec = 26 * 3600

    for handle in GLOBAL_VIRAL_HUBS:
        tweets = fetch_live_tweets_fxtwitter_v2(handle)
        for t in tweets:
            tid = t["id"]
            if tid in history: continue
            created_ts = t.get("created_timestamp")
            if created_ts and isinstance(created_ts, (int, float)) and (now_ts - created_ts) > day_sec:
                continue
            candidate_tweets.append(t)

    candidate_tweets.sort(key=lambda x: x.get("likes", 0), reverse=True)

    top10_selected = []
    for t in candidate_tweets:
        if len(top10_selected) >= 10: break
        if t["likes"] >= 1500 or len(top10_selected) < 5:
            is_worthy, _, _ = ai_gatekeeper_check(t["author"], t["text"], t["likes"])
            if is_worthy:
                top10_selected.append(t)

    if not top10_selected: return []

    folder_name = f"daily_top10_{int(time.time())}"
    folder_path = os.path.join(WORKSPACE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for idx, t in enumerate(top10_selected, start=1):
        img_file = os.path.join(folder_path, f"{idx}.png")
        capture_clean_screenshot(t["id"], img_file)

    with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
        json.dump({
            "mode": "daily_top10",
            "tweets": top10_selected,
            "tweet_ids": [t["id"] for t in top10_selected]
        }, jf, indent=2)

    with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
        tf.write("TOP 10 MOST VIRAL TWEETS OF THE DAY")

    return [folder_name]

def hunt_and_prepare_viral_tweets():
    if RUN_MODE == "daily_top10":
        return hunt_daily_top10_viral_tweets()
    else:
        return hunt_2hour_breaking_tweets()
