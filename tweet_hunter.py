# -*- coding: utf-8 -*-
import os, re, json, requests, feedparser
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, MAX_VIDEOS_PER_RUN
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

def fetch_tweet_by_id(tweet_id):
    """FxTwitter API দিয়ে টুইটের টেক্সট, লেখক এবং লাইক সংখ্যা বের করে"""
    try:
        url = f"https://api.fxtwitter.com/status/{tweet_id}"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            tweet = data.get("tweet", {})
            if tweet and tweet.get("text"):
                return {
                    "id": str(tweet.get("id", tweet_id)),
                    "text": tweet.get("text", ""),
                    "likes": int(tweet.get("likes", 0)),
                    "retweets": int(tweet.get("retweets", 0)),
                    "author": tweet.get("author", {}).get("screen_name", "VIP"),
                    "url": tweet.get("url", f"https://x.com/i/status/{tweet_id}")
                }
    except Exception as e:
        print(f"⚠️ FxTwitter fetch error for ID {tweet_id}: {e}")
    return None

def find_tweets_from_google_and_rss(handle):
    """গুগল নিউজ ও গ্লোবাল আরএসএস ফিড থেকে ভিআইপিদের সর্বশেষ ভাইরাল টুইটের লিংক খুঁজে বের করে"""
    tweets_found = []
    
    # সোর্স ১: Google Real-Time X Search RSS
    search_queries = [
        f"https://news.google.com/rss/search?q=site:x.com/{handle}+OR+site:twitter.com/{handle}&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=%22@{handle}%22+tweet+OR+twitter&hl=en-US&gl=US&ceid=US:en",
        f"https://rsshub.app/twitter/user/{handle}"
    ]

    for feed_url in search_queries:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                # লিংকের ভেতর থেকে অথবা ডেসক্রিপশন থেকে টুইট আইডি খুঁজে বের করা
                full_content = f"{entry.get('link', '')} {entry.get('summary', '')} {entry.get('title', '')}"
                matches = re.findall(r'(?:twitter\.com|x\.com)/(?:[a-zA-Z0-9_]+)/status/(\d+)', full_content)
                for tid in matches:
                    if tid not in tweets_found:
                        tweets_found.append(tid)
            if tweets_found:
                break
        except Exception:
            continue

    return tweets_found

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
    print(f"\n🔍 [TWEET HUNTER] Multi-Engine Hunter Active (Target: {MAX_VIDEOS_PER_RUN} video)...")
    history = get_processed_history()
    collected_count = 0

    for handle in VIP_HANDLES:
        if collected_count >= MAX_VIDEOS_PER_RUN:
            break

        print(f"📡 Searching viral tweets for @{handle} via Global Engine...")
        tweet_ids = find_tweets_from_google_and_rss(handle)

        for tid in tweet_ids:
            if collected_count >= MAX_VIDEOS_PER_RUN:
                break

            folder_name = f"tweet_{handle}_{tid}"
            if tid in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                continue

            # টুইট ডিটেইলস নিয়ে আসা
            tweet_data = fetch_tweet_by_id(tid)
            if not tweet_data:
                continue

            likes = tweet_data["likes"]
            tweet_text = tweet_data["text"]
            tweet_url = tweet_data["url"]

            print(f"🔥 Found Active Tweet by @{handle}! (Likes: {likes:,})")
            print(f"   └─ \"{tweet_text[:65]}...\"")

            folder_path = os.path.join(WORKSPACE_DIR, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            img_path = os.path.join(folder_path, "1.png")

            print(f"📸 Capturing Screenshot via Microlink: {tweet_url}")
            if capture_tweet_screenshot(tweet_url, img_path):
                with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                    json.dump(tweet_data, jf, indent=2)

                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(f"@{handle}: {tweet_text[:60]}")

                print(f"✅ Staged for Video Creation: {folder_name}")
                collected_count += 1
                break
            else:
                print(f"⚠️ Screenshot failed for ID {tid}, trying next...")

    print(f"🎯 Total {collected_count}/{MAX_VIDEOS_PER_RUN} viral tweet(s) prepared for this run.\n")
