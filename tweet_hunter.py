# -*- coding: utf-8 -*-
import os, json, time, requests
from datetime import datetime, timezone
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, RUN_MODE
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer
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

def fetch_live_tweets_fxtwitter_v2(handle):
    endpoints = [
        f"https://api.fxtwitter.com/2/profile/{handle}/statuses",
        f"https://api.fxtwitter.com/2/search?q=from:{handle}",
        f"https://api.fxtwitter.com/2/profile/{handle}"
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
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
                        if tid and text:
                            tweets.append({
                                "id": tid,
                                "text": text,
                                "likes": likes,
                                "author": handle,
                                "created_timestamp": created_at,
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
            resp = requests.get("https://api.microlink.io", params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                s_url = resp.json().get("data", {}).get("screenshot", {}).get("url")
                if s_url:
                    img_data = requests.get(s_url, timeout=20).content
                    with open(output_path, "wb") as f: f.write(img_data)
                    return True
        except Exception: continue
    return False

# ==================== [ ১. ২ ঘণ্টার ব্রেকিং নিউজ সংগ্রাহক ] ====================
def hunt_2hour_breaking_tweets():
    init_workspace()
    history = get_processed_history()
    print("\n🔍 [TWEET HUNTER] Mode: 2-Hour Breaking News + AI Gatekeeper Active...")
    
    now_ts = time.time()
    two_hours_sec = 2.5 * 3600 # ২.৫ ঘণ্টার উইন্ডো যাতে কোনো ব্রেকিং পোস্ট মিস না হয়
    staged_folders = []

    for handle in VIP_HANDLES:
        print(f"📡 Scanning @{handle} for fresh tweets...")
        tweets = fetch_live_tweets_fxtwitter_v2(handle)

        for tweet in tweets:
            tid = tweet["id"]
            tweet_text = tweet["text"]
            likes = tweet["likes"]
            tweet_url = tweet["url"]
            folder_name = f"tweet_{handle}_{tid}"

            # ১. হিস্ট্রি চেক (কখনোই ডুপ্লিকেট হবে না)
            if tid in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                continue

            # ২. টাইম চেক (যদি টাইমস্ট্যাম্প থাকে তবে ২ ঘণ্টার ভেতরের হতে হবে)
            created_ts = tweet.get("created_timestamp")
            if created_ts and isinstance(created_ts, (int, float)):
                if (now_ts - created_ts) > two_hours_sec:
                    continue # ২ ঘণ্টার পুরোনো হলে স্কিপ

            # ৩. 🤖 AI Gatekeeper চেক
            print(f"  🔍 Passing @{handle}'s Tweet (ID: {tid}) to AI Gatekeeper...")
            is_worthy, reason, angle = ai_gatekeeper_check(handle, tweet_text, likes)
            
            if not is_worthy:
                print(f"  🚫 [GATEKEEPER REJECTED] {reason} (Skipping).")
                continue

            print(f"  🔥 [GATEKEEPER APPROVED] {reason} | Angle: {angle}")
            
            # ৪. ফোল্ডার তৈরি ও স্ক্রিনশট সংগ্রহ
            folder_path = os.path.join(WORKSPACE_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            img_main = os.path.join(folder_path, "1.png")

            if capture_clean_screenshot(tid, img_main):
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
                print(f"  ✅ Staged Breaking News Video: {folder_name}")
                break # প্রতি অ্যাকাউন্ট থেকে এই রানে ১টি সেরা ব্রেকিং পোস্ট

    print(f"\n🎯 Staged {len(staged_folders)} breaking video(s) from the last 2 hours.\n")
    return staged_folders

# ==================== [ ২. ২৪ ঘণ্টার সেরা ১০ মেগা সংগ্রাহক ] ====================
def hunt_daily_top10_viral_tweets():
    init_workspace()
    history = get_processed_history()
    print("\n🌟 [DAILY TOP 10 HUNTER] Scanning all VIPs for Top 10 Viral Tweets of the day...")

    all_recent_tweets = []
    now_ts = time.time()
    day_sec = 26 * 3600 # ২৬ ঘণ্টার বাফার

    for handle in VIP_HANDLES:
        tweets = fetch_live_tweets_fxtwitter_v2(handle)
        for t in tweets:
            tid = t["id"]
            if tid in history: continue
            created_ts = t.get("created_timestamp")
            if created_ts and isinstance(created_ts, (int, float)) and (now_ts - created_ts) > day_sec:
                continue
            all_recent_tweets.append(t)

    # এনগেজমেন্ট (লাইক) অনুযায়ী সাজানো
    all_recent_tweets.sort(key=lambda x: x.get("likes", 0), reverse=True)

    qualified_tweets = []
    for t in all_recent_tweets:
        if len(qualified_tweets) >= 10: break
        is_worthy, _, _ = ai_gatekeeper_check(t["author"], t["text"], t["likes"])
        if is_worthy:
            qualified_tweets.append(t)

    if not qualified_tweets:
        print("❌ No qualified tweets found for Daily Top 10.")
        return []

    folder_name = f"daily_top10_{int(time.time())}"
    folder_path = os.path.join(WORKSPACE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # ১০টি টুইটের স্ক্রিনশট ক্রমানুসারে (1.png, 2.png, ..., 10.png) ডাউনলোড
    downloaded_imgs = []
    for idx, t in enumerate(qualified_tweets, start=1):
        img_file = os.path.join(folder_path, f"{idx}.png")
        print(f"📸 Downloading #{idx}/10 Screenshot (@{t['author']})...")
        if capture_clean_screenshot(t["id"], img_file):
            downloaded_imgs.append(img_file)

    with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
        json.dump({
            "mode": "daily_top10",
            "tweets": qualified_tweets,
            "tweet_ids": [t["id"] for t in qualified_tweets]
        }, jf, indent=2)

    print(f"🎉 Daily Top 10 Compilation Staged with {len(downloaded_imgs)} tweet slides!\n")
    return [folder_name]

def hunt_and_prepare_viral_tweets():
    if RUN_MODE == "daily_top10":
        return hunt_daily_top10_viral_tweets()
    else:
        return hunt_2hour_breaking_tweets()
