# -*- coding: utf-8 -*-
import os, re, json, requests
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, MAX_VIDEOS_PER_RUN
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def get_processed_history():
    """পূর্বে তৈরি হওয়া Tweet ID ও হিস্ট্রি লোড করে"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception: pass
    return set()

def fetch_tweets_from_twitter_syndication(handle):
    """
    টুইটারের অফিসিয়াল Syndication সার্ভার থেকে সরাসরি লাইভ টুইট ও এনগেজমেন্ট বের করে
    """
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                entries = data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
                tweets = []
                for entry in entries:
                    t = entry.get("content", {}).get("tweet")
                    if t:
                        tweets.append({
                            "id": str(t.get("id_str")),
                            "text": t.get("text", ""),
                            "likes": int(t.get("favorite_count", 0)),
                            "retweets": int(t.get("retweet_count", 0)),
                            "url": f"https://x.com/{handle}/status/{t.get('id_str')}"
                        })
                return tweets
    except Exception as e:
        print(f"⚠️ Syndication error for @{handle}: {e}")
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
    print(f"\n🔍 [TWEET HUNTER] Scanning live Twitter timelines for {MAX_VIDEOS_PER_RUN} video(s)...")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    
    # নিশ্চিত করা যে history ফাইল উপস্থিত আছে
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f: pass

    history = get_processed_history()
    collected_count = 0

    for handle in VIP_HANDLES:
        if collected_count >= MAX_VIDEOS_PER_RUN:
            break

        print(f"📡 Checking @{handle}'s latest tweets directly from X...")
        tweets = fetch_tweets_from_twitter_syndication(handle)

        for tweet in tweets[:6]:
            if collected_count >= MAX_VIDEOS_PER_RUN:
                break

            tweet_id = tweet["id"]
            tweet_text = tweet["text"]
            likes = tweet["likes"]
            tweet_url = tweet["url"]
            folder_name = f"tweet_{handle}_{tweet_id}"

            # ডুপ্লিকেট চেক
            if tweet_id in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                continue

            # এনগেজমেন্ট ফিল্টার (কমপক্ষে ১,০০০ লাইক বা ভাইরাল টুইট)
            if likes >= 1000 or len(tweets) <= 3:
                print(f"🔥 Found Hot Tweet by @{handle}! (Likes: {likes:,})")
                folder_path = os.path.join(WORKSPACE_DIR, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                img_path = os.path.join(folder_path, "1.png")

                print(f"📸 Capturing Screenshot for: {tweet_url}")
                if capture_tweet_screenshot(tweet_url, img_path):
                    with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                        json.dump({
                            "tweet_id": tweet_id,
                            "author": handle,
                            "url": tweet_url,
                            "text": tweet_text,
                            "likes": likes
                        }, jf, indent=2)

                    with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                        tf.write(f"@{handle}: {tweet_text[:60]}")

                    print(f"✅ Prepared & Staged #{collected_count + 1}: {folder_name}")
                    collected_count += 1
                    break
                else:
                    print(f"⚠️ Screenshot failed for {tweet_url}, trying next tweet...")

    print(f"🎯 Total {collected_count}/{MAX_VIDEOS_PER_RUN} viral tweet(s) staged for video creation.\n")
