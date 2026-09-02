# -*- coding: utf-8 -*-
import os, json, re, requests
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, MAX_VIDEOS_PER_RUN
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

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
    except Exception:
        return set()

def fetch_live_tweets_fxtwitter_v2(handle):
    """
    FxTwitter API v2 দিয়ে সরাসরি হ্যান্ডেলের লাইভ টাইমলাইন এবং পোস্টগুলো নিয়ে আসে
    """
    endpoints = [
        f"https://api.fxtwitter.com/2/profile/{handle}/statuses",
        f"https://api.fxtwitter.com/2/search?q=from:{handle}",
        f"https://api.fxtwitter.com/2/profile/{handle}"
    ]

    for url in endpoints:
        try:
            print(f"  ⏳ Querying FxTwitter API: {url} ...")
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                
                # ১. লিস্ট আকারে টুইট থাকলে
                results = data.get("results", []) or data.get("statuses", []) or data.get("tweets", [])
                if results and isinstance(results, list):
                    tweets = []
                    for t in results:
                        tid = str(t.get("id") or t.get("id_str") or "")
                        text = t.get("text", "")
                        likes = int(t.get("likes", t.get("favorite_count", 0)))
                        if tid and text:
                            tweets.append({
                                "id": tid,
                                "text": text,
                                "likes": likes,
                                "author": handle,
                                "url": f"https://x.com/{handle}/status/{tid}"
                            })
                    if tweets:
                        print(f"  ✅ Found {len(tweets)} tweets for @{handle}")
                        return tweets

                # ২. সিঙ্গেল বা পিনড টুইট থাকলে
                single = data.get("status") or data.get("tweet") or data.get("pinned_tweet")
                if single and isinstance(single, dict):
                    tid = str(single.get("id", ""))
                    text = single.get("text", "")
                    if tid and text:
                        return [{
                            "id": tid,
                            "text": text,
                            "likes": int(single.get("likes", 0)),
                            "author": handle,
                            "url": f"https://x.com/{handle}/status/{tid}"
                        }]
            else:
                print(f"  ⚠️ HTTP {resp.status_code} returned from {url}")
        except Exception as e:
            print(f"  ⚠️ Error from {url}: {e}")
            continue

    return []

def capture_tweet_screenshot(tweet_url, output_image_path):
    """Microlink API দিয়ে ক্রিস্প হাই-রেজোলিউশন স্ক্রিনশট নেয়"""
    key_queue = get_circular_key_queue("microlink", "MICROLINK_API_KEYS")
    if not key_queue:
        key_queue = [(0, None)]

    total_keys = len(key_queue)
    endpoint = "https://api.microlink.io"
    params = {
        "url": tweet_url,
        "screenshot": "true",
        "scale": "2",
        "waitForTimeout": "3500"
    }

    for actual_idx, api_key in key_queue:
        headers = {"x-api-key": api_key} if api_key else {}
        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                screenshot_url = data.get("data", {}).get("screenshot", {}).get("url")
                if screenshot_url:
                    img_data = requests.get(screenshot_url, timeout=20).content
                    with open(output_image_path, "wb") as f:
                        f.write(img_data)
                    if api_key:
                        update_success_key_pointer("microlink", actual_idx)
                    return True
            else:
                if api_key:
                    update_exhausted_key_pointer("microlink", actual_idx, total_keys)
        except Exception:
            if api_key:
                update_exhausted_key_pointer("microlink", actual_idx, total_keys)
            continue

    return False

def hunt_and_prepare_viral_tweets():
    init_workspace()
    print(f"\n🔍 [TWEET HUNTER] FxTwitter Cloud Engine Active (Target: {MAX_VIDEOS_PER_RUN} video)...")
    history = get_processed_history()
    collected_count = 0

    for handle in VIP_HANDLES:
        if collected_count >= MAX_VIDEOS_PER_RUN:
            break

        print(f"\n📡 Scanning live timeline for @{handle}...")
        tweets = fetch_live_tweets_fxtwitter_v2(handle)

        for tweet in tweets:
            if collected_count >= MAX_VIDEOS_PER_RUN:
                break

            tid = tweet["id"]
            tweet_text = tweet["text"]
            likes = tweet["likes"]
            tweet_url = tweet["url"]
            folder_name = f"tweet_{handle}_{tid}"

            # ডুপ্লিকেট ফিল্টার
            if tid in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                print(f"  ⏩ Skipping already processed tweet ID: {tid}")
                continue

            print(f"🔥 Selecting Tweet by @{handle}! (Likes: {likes:,})")
            print(f"   📝 Text: \"{tweet_text[:80]}...\"")

            folder_path = os.path.join(WORKSPACE_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            img_path = os.path.join(folder_path, "1.png")

            print(f"📸 Capturing Screenshot via Microlink: {tweet_url}")
            if capture_tweet_screenshot(tweet_url, img_path):
                with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                    json.dump(tweet, jf, indent=2)

                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(f"@{handle}: {tweet_text[:60]}")

                print(f"✅ Successfully Staged: {folder_name}")
                collected_count += 1
                break
            else:
                print(f"⚠️ Screenshot failed for {tweet_url}, trying next...")

    print(f"\n🎯 Total {collected_count}/{MAX_VIDEOS_PER_RUN} viral tweet(s) prepared for video creation.\n")
