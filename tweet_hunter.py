# -*- coding: utf-8 -*-
import os, re, json, requests
from config import WORKSPACE_DIR, HISTORY_FILE, VIP_HANDLES, MAX_VIDEOS_PER_RUN
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

def get_processed_history():
    """পূর্বে প্রসেস হওয়া সকল Tweet ID ও টাইটেল লোড করে"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception: pass
    return set()

def fetch_tweet_details(tweet_url):
    try:
        api_url = tweet_url.replace("twitter.com", "api.fxtwitter.com").replace("x.com", "api.fxtwitter.com")
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 200 and "tweet" in data:
                return data["tweet"]
    except Exception: pass
    return None

def capture_tweet_screenshot(tweet_url, output_image_path):
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
    print(f"\n🔍 [TWEET HUNTER] Target to produce: {MAX_VIDEOS_PER_RUN} video(s)...")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    history = get_processed_history()
    collected_count = 0

    for handle in VIP_HANDLES:
        if collected_count >= MAX_VIDEOS_PER_RUN:
            break

        feed_url = f"https://nitter.poast.org/{handle}/rss"
        try:
            import feedparser
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                if collected_count >= MAX_VIDEOS_PER_RUN:
                    break

                tweet_link = entry.link.replace("nitter.poast.org", "x.com")
                
                # টুইটের ইউনিক আইডি এক্সট্রাক্ট করা (যেমন: 18293849201923)
                id_match = re.search(r'status/(\d+)', tweet_link)
                tweet_id = id_match.group(1) if id_match else tweet_link.split("/")[-1].split("?")[0]
                
                folder_name = f"tweet_{handle}_{tweet_id}"

                # 🌟 ডুপ্লিকেট চেক: Tweet ID বা ফোল্ডার নাম হিস্ট্রিতে থাকলে সাথে সাথে স্কিপ
                if tweet_id in history or folder_name in history or os.path.exists(os.path.join(WORKSPACE_DIR, folder_name)):
                    continue

                tweet_meta = fetch_tweet_details(tweet_link)
                likes = tweet_meta.get("likes", 0) if tweet_meta else 10000

                # ভাইরাল ফিল্টার: কমপক্ষে ৫,০০০ লাইক
                if likes >= 5000:
                    folder_path = os.path.join(WORKSPACE_DIR, folder_name)
                    os.makedirs(folder_path, exist_ok=True)
                    img_path = os.path.join(folder_path, "1.png")

                    print(f"📸 Capturing Screenshot for @{handle}'s Tweet (ID: {tweet_id})...")
                    if capture_tweet_screenshot(tweet_link, img_path):
                        tweet_text = tweet_meta.get("text", entry.summary) if tweet_meta else entry.summary
                        
                        with open(os.path.join(folder_path, "tweet_info.json"), "w", encoding="utf-8") as jf:
                            json.dump({
                                "tweet_id": tweet_id,
                                "author": handle,
                                "url": tweet_link,
                                "text": tweet_text,
                                "likes": likes
                            }, jf, indent=2)

                        with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                            tf.write(f"@{handle}: {tweet_text[:60]}")

                        print(f"✅ Staged #{collected_count + 1}: {folder_name} (Likes: {likes:,})")
                        collected_count += 1
                        break
        except Exception: 
            continue

    print(f"🎯 Total {collected_count}/{MAX_VIDEOS_PER_RUN} viral tweet(s) prepared for this run.\n")
