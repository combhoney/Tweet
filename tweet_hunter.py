# -*- coding: utf-8 -*-
import os, json, time, random, requests
from config import WORKSPACE_DIR, HISTORY_FILE, CATEGORY_HANDLES, SCAN_WINDOW_HOURS, get_active_category
from key_manager import get_circular_key_queue
from ai_service import ai_gatekeeper_check

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

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

def fetch_live_tweets_fxtwitter(handle):
    url = f"https://api.fxtwitter.com/2/profile/{handle}/statuses"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            res = resp.json().get("results", []) or resp.json().get("statuses", [])
            tweets = []
            for t in res:
                tid = str(t.get("id") or t.get("id_str") or "")
                text = t.get("text", "")
                likes = int(t.get("likes", t.get("favorite_count", 0)))
                created_at = t.get("created_timestamp") or t.get("created_at")
                if tid and text:
                    tweets.append({
                        "id": tid,
                        "text": text,
                        "likes": likes,
                        "author": handle,
                        "created_timestamp": created_at,
                        "url": f"https://x.com/{handle}/status/{tid}"
                    })
            return tweets
    except Exception: pass
    return []

def fetch_direct_replies_for_tweet(author, tweet_id, max_needed=6):
    direct_replies = []
    search_url = f"https://api.fxtwitter.com/2/search?q=to:{author}&sort=top"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for r in results:
                rid = str(r.get("id", ""))
                rtext = r.get("text", "").strip()
                rauthor = r.get("author", {}).get("screen_name", "User")
                if rid and rid != str(tweet_id) and len(rtext) > 15:
                    if rid not in [x["id"] for x in direct_replies]:
                        direct_replies.append({
                            "id": rid,
                            "author": rauthor,
                            "text": rtext,
                            "likes": int(r.get("likes", 0))
                        })
                if len(direct_replies) >= max_needed: break
    except Exception: pass
    return direct_replies

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

def hunt_category_tweets_for_compilation():
    init_workspace()
    history = get_processed_history()
    active_cat = get_active_category()
    handles = CATEGORY_HANDLES.get(active_cat, [])
    random.shuffle(handles)

    now_ts = time.time()
    twelve_hours_sec = SCAN_WINDOW_HOURS * 3600

    print(f"\n=======================================================")
    print(f"🎯 [CATEGORY RUN] Scanning 100 Handles for '{active_cat.upper()}' (Last {SCAN_WINDOW_HOURS}h)")
    print(f"=======================================================\n")

    staged_stories = []

    for handle in handles:
        tweets = fetch_live_tweets_fxtwitter(handle)
        if not tweets: continue

        for tweet in tweets:
            tid = tweet["id"]
            tweet_text = tweet["text"]
            likes = tweet["likes"]
            tweet_url = tweet["url"]
            folder_name = f"story_{active_cat}_{handle}_{tid}"

            if tid in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                continue

            created_ts = tweet.get("created_timestamp")
            if created_ts and isinstance(created_ts, (int, float)):
                if (now_ts - created_ts) > twelve_hours_sec:
                    continue

            # 🌟 ক্যাটাগরি বিশুদ্ধতা যাচাই সহ AI Gatekeeper কল
            is_worthy, reason, angle = ai_gatekeeper_check(handle, tweet_text, likes, active_category=active_cat)
            if not is_worthy:
                continue

            print(f"\n🔥 [APPROVED: {active_cat.upper()}] @{handle} ({likes:,} Likes) ➔ \"{tweet_text[:60]}...\"")
            folder_path = os.path.join(WORKSPACE_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            img_main = os.path.join(folder_path, "1.png")
            if capture_clean_screenshot(tid, img_main):
                slides_data = [
                    {"slide_id": 1, "type": "main", "author": handle, "text": tweet_text, "image": "1.png"}
                ]

                print(f"  💬 Collecting direct community replies for @{handle}...")
                replies = fetch_direct_replies_for_tweet(handle, tid, max_needed=5)
                
                for idx, rep in enumerate(replies, start=2):
                    rep_img_path = os.path.join(folder_path, f"{idx}.png")
                    if capture_clean_screenshot(rep["id"], rep_img_path):
                        slides_data.append({
                            "slide_id": idx,
                            "type": "reply",
                            "author": rep["author"],
                            "text": rep["text"],
                            "image": f"{idx}.png"
                        })

                with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                    json.dump({
                        "category": active_cat,
                        "tweet_id": tid,
                        "author": handle,
                        "url": tweet_url,
                        "text": tweet_text,
                        "likes": likes,
                        "slides_data": slides_data,
                        "editorial_angle": angle
                    }, jf, indent=2)

                staged_stories.append(folder_name)
                print(f"  ✅ Staged {active_cat.upper()} Story #{len(staged_stories)}: {folder_name}")
                break

    print(f"\n🎯 Total {len(staged_stories)} pure {active_cat.upper()} story segment(s) staged.\n")
    return staged_stories
