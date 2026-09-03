# -*- coding: utf-8 -*-
import os, json, re, requests
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODELS = ["gemma4", "kimi-k3", "minimax-m3"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

# ------------------ [ 🤖 ব্যালেন্সড AI GATEKEEPER ] ------------------
def ai_gatekeeper_check(author, tweet_text, likes):
    """
    শুধুমাত্র স্প্যাম ও অপ্রয়োজনীয় চ্যাট বাদ দেয়; যেকোনো ব্রেকিং স্টেটমেন্ট, নিউজ বা মন্তব্য গ্রহণ করে
    """
    clean_t = tweet_text.strip()
    # মিনিমাম বেসিক চেক (২৫ অক্ষর এবং ৫০০ লাইক)
    if len(clean_t) < 25 or likes < 400:
        return False, f"Too short ({len(clean_t)} chars) or low engagement ({likes} likes)", ""

    gatekeeper_prompt = f"""You are an editorial assistant for a Breaking News YouTube channel.
Determine if this tweet is worth discussing in a 2-3 minute news/commentary video.

Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

RULES:
- ACCEPT (is_worthy: true) if it mentions any tech, AI, politics, crypto, world event, business, hot debate, product launch, opinion, or controversy.
- REJECT (is_worthy: false) ONLY if it is pure spam, 1-word greeting (e.g. 'gm', 'good morning'), or meaningless personal chat.

Return strictly JSON:
{{
  "is_worthy": true,
  "reason": "Short reason",
  "editorial_angle": "Hook angle"
}}"""

    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": gatekeeper_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2, "max_tokens": 180
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                if data and "is_worthy" in data:
                    return data.get("is_worthy", True), data.get("reason", "Approved"), data.get("editorial_angle", "Breaking News")
        except Exception: pass

    # AI কানেকশন ফেইল করলে ফলব্যাক: ২৫ অক্ষরের বড় হলে পাস করবে
    return True, "Passed engagement check", "Breaking Story"

# ------------------ [ ব্রেকিং নিউজ স্ক্রিপ্ট জেনারেটর ] ------------------
def generate_tweet_commentary(author, tweet_text, top_replies=None):
    prompt = f"""You are an elite American YouTube news anchor.
Write an engaging, dramatic 2.5 minute continuous spoken commentary script (320-380 words) for USA viewers.
Context:
- Author: @{author}
- Tweet Content: "{tweet_text}"

CRITICAL RULES:
1. Fast-paced, engaging American English commentary. No fluff.
2. Structure: Explosive Hook -> Core Statement & Background -> Internet Reaction -> Call to Action.
3. Spoken English: No asterisks, markdown symbols, or hashtags in voiceover script.

Return strictly valid JSON:
{{
  "optimized_title": "High CTR Sensational Title under 90 chars with emojis",
  "voiceover_script": "Full spoken script...",
  "video_description": "Engaging description with summary and 4 hashtags",
  "specific_tags": ["Breaking News", "Tech News", "Twitter Viral"],
  "top_text": "BREAKING NEWS",
  "row1_text": "EXPLOSIVE STATEMENT",
  "row2_text": "Internet Shocked",
  "bot_text": "FULL BREAKDOWN"
}}"""

    # ১. Groq দিয়ে স্ক্রিপ্ট তৈরি
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            try:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are a professional YouTube scriptwriter. Output valid JSON only."},
                                 {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6, "max_tokens": 2000
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("optimized_title") and data.get("voiceover_script"):
                        return (
                            data.get("optimized_title").strip()[:100],
                            data.get("voiceover_script").strip(),
                            {
                                "top_text": data.get("top_text", "BREAKING NEWS"),
                                "row1_text": data.get("row1_text", "VIRAL ALERT"),
                                "row2_text": data.get("row2_text", "Internet Shocked"),
                                "bot_text": data.get("bot_text", "FULL BREAKDOWN")
                            },
                            data.get("video_description", "").strip(),
                            data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                        )
            except Exception: pass

    # ২. Ollama ফলব্যাক
    ollama_keys = get_circular_key_queue("ollama", "Ollama_API_Key")
    for actual_idx, o_key in ollama_keys:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
        for o_model in OLLAMA_MODELS:
            try:
                payload = {"model": o_model, "messages": [{"role": "user", "content": prompt}], "stream": False}
                resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=35)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json().get("message", {}).get("content", ""))
                    if data and data.get("optimized_title"):
                        return (
                            data.get("optimized_title").strip()[:100],
                            data.get("voiceover_script").strip(),
                            {
                                "top_text": data.get("top_text", "BREAKING NEWS"),
                                "row1_text": data.get("row1_text", "VIRAL ALERT"),
                                "row2_text": data.get("row2_text", "Internet Shocked"),
                                "bot_text": data.get("bot_text", "FULL BREAKDOWN")
                            },
                            data.get("video_description", "").strip(),
                            data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                        )
            except Exception: pass

    return None, None, None, None, None

def generate_daily_top10_script(top10_tweets):
    summary_text = "\n".join([f"#{i+1}. @{t['author']} ({t['likes']:,} Likes): \"{t['text'][:100]}\"" for i, t in enumerate(top10_tweets)])
    prompt = f"""You are a US YouTube news anchor hosting 'Top 10 Most Viral Tweets of the Day'.
Here are the top 10 tweets:
{summary_text}

Write a thrilling 7-8 minute full compilation script (900-1100 words). Output strictly valid JSON."""

    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.6, "max_tokens": 3000
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=50)
            if resp.status_code == 200:
                data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                if data and data.get("optimized_title"):
                    return (
                        data.get("optimized_title").strip()[:100],
                        data.get("voiceover_script").strip(),
                        {
                            "top_text": data.get("top_text", "DAILY ROUNDUP"),
                            "row1_text": data.get("row1_text", "TOP 10 TWEETS"),
                            "row2_text": data.get("row2_text", "Internet Explodes"),
                            "bot_text": data.get("bot_text", "FULL RECAP")
                        },
                        data.get("video_description", "").strip(),
                        data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                    )
        except Exception: pass
    return None, None, None, None, None
