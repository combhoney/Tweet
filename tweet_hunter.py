# -*- coding: utf-8 -*-
import os, json, time, requests
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
                        if tid and text:
                            tweets.append({
                                "id": tid,
                                "text": text,
                                "likes": likes,
                                "author": handle,
                                "created_timestamp": created_at,
                                "quote_id": quote_id,
                                "url": f"https://x.com/{handle}/status/{tid}"
                            })
                    if tweets: return tweets
        except Exception: continue
    return []

def fetch_related_community_replies(author, tweet_id, keyword_query, max_needed=8):
    """
    টুইটার সার্চ ও এফএক্সটুইটার থেকে ওই বিষয়ের ওপর টপ ভেরিফায়েড কমেন্ট, কোট ও মতামত খুঁজে বের করে
    """
    related_tweets = []
    # সার্চ কুয়েরি
    search_urls = [
        f"https://api.fxtwitter.com/2/search?q=to:{author}&sort=top",
        f"https://api.fxtwitter.com/2/search?q={author}&sort=top"
    ]
    for surl in search_urls:
        if len(related_tweets) >= max_needed: break
        try:
            resp = requests.get(surl, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                res = resp.json().get("results", [])
                for r in res:
                    rid = str(r.get("id", ""))
                    rtext = r.get("text", "")
                    rauthor = r.get("author", {}).get("screen_name", "")
                    if rid and rid != str(tweet_id) and len(rtext) > 20:
                        if rid not in [x["id"] for x in related_tweets]:
                            related_tweets.append({
                                "id": rid,
                                "author": rauthor,
                                "text": rtext,
                                "likes": int(r.get("likes", 0))
                            })
        except Exception: pass

    # যদি আরও স্লাইডের প্রয়োজন হয়, অন্যান্য হাবের আলোচিত পোস্ট যুক্ত করা
    if len(related_tweets) < max_needed:
        for v_handle in GLOBAL_VIRAL_HUBS[:5]:
            if len(related_tweets) >= max_needed: break
            if v_handle.lower() != author.lower():
                v_tweets = fetch_live_tweets_fxtwitter_v2(v_handle)
                for vt in v_tweets[:2]:
                    if vt["id"] != str(tweet_id) and vt["id"] not in [x["id"] for x in related_tweets]:
                        related_tweets.append(vt)

    return related_tweets[:max_needed]

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

# ==================== [ ১. ২ ঘণ্টার ব্রেকিং নিউজ মোড (৮-১০টি স্লাইড) ] ====================
def hunt_2hour_breaking_tweets():
    init_workspace()
    history = get_processed_history()
    print("\n🔍 [TWEET HUNTER] Mode: 2-Hour Breaking News + 8-10 Community Slides Active...")
    
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
            
            # 🌟 স্লাইড ১: মূল টুইটের স্ক্রিনশট
            img_main = os.path.join(folder_path, "1.png")
            if capture_clean_screenshot(tid, img_main):
                slide_count = 1

                # 🌟 স্লাইড ২: কোট টুইট থাকলে
                if quote_id:
                    slide_count += 1
                    capture_clean_screenshot(quote_id, os.path.join(folder_path, f"{slide_count}.png"))

                # 🌟 স্লাইড ৩ থেকে ১০: শীর্ষ ভেরিফায়েড রিপ্লাই ও মতামত কালেকশন
                print(f"  💬 Hunting top 8-10 community replies & reactions for @{handle}...")
                replies = fetch_related_community_replies(handle, tid, tweet_text, max_needed=8)
                
                for rep in replies:
                    slide_count += 1
                    rep_img = os.path.join(folder_path, f"{slide_count}.png")
                    print(f"    📸 Capturing Slide #{slide_count} (@{rep['author']})...")
                    capture_clean_screenshot(rep["id"], rep_img)
                    if slide_count >= 10: break

                with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                    json.dump({
                        "mode": "breaking",
                        "tweet_id": tid,
                        "author": handle,
                        "url": tweet_url,
                        "text": tweet_text,
                        "likes": likes,
                        "replies_data": replies,
                        "editorial_angle": angle
                    }, jf, indent=2)
                
                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(f"@{handle}: {tweet_text[:60]}")

                staged_folders.append(folder_name)
                print(f"  ✅ Staged {slide_count}-Slide Video for: {folder_name}")

    print(f"\n🎯 Total {len(staged_folders)} breaking video(s) staged with rich community slides.\n")
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

    if not top10_selected:
        return []

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
