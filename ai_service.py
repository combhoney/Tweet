# -*- coding: utf-8 -*-
import os, json, re, requests
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_PRIORITY_MODELS = [
    "gemma4:31b", "gpt-oss:120b", "gpt-oss:20b",
    "nemotron-3-nano:30b", "nemotron-3-super", "nemotron-3-ultra"
]
OLLAMA_FALLBACK_MODELS = ["kimi-k3", "minimax-m3", "gemma4"]
OLLAMA_ALL_MODELS = OLLAMA_PRIORITY_MODELS + OLLAMA_FALLBACK_MODELS
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def parse_json_safely(raw_text):
    if not raw_text: return None
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

def ai_gatekeeper_check(author, tweet_text, likes, active_category="tech"):
    clean_t = tweet_text.strip()
    if len(clean_t) < 15 or likes < 150:
        return False, "Too short or low engagement", ""

    gatekeeper_prompt = f"""You are a strict Category Gatekeeper for a US YouTube Shorts Channel.
Target Category for this run: '{active_category.upper()}'

Evaluate this tweet:
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

CATEGORY PURITY RULES:
1. The tweet MUST strictly and genuinely belong to '{active_category.upper()}'.
2. Reject if it is about any other niche or topic.
3. Reject generic greetings or ad spam.

Return JSON:
{{"is_worthy": true, "reason": "Why it belongs to {active_category}", "editorial_angle": "Viral angle"}}"""

    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": gatekeeper_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1, "max_tokens": 150
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                if data and "is_worthy" in data:
                    return data.get("is_worthy", True), data.get("reason", "Approved"), data.get("editorial_angle", "Breaking Story")
        except Exception: pass

    return True, "Passed engagement check", f"Breaking {active_category.capitalize()} Story"

def generate_shorts_script(slides_data, active_category="tech"):
    """
    🌟 ৪৫-৫৫ সেকেন্ডের (৯০-১১০ শব্দের) হাই-রিটেনশন ইউটিউব শর্টস স্ক্রিপ্ট
    """
    slides_formatted = "\n".join([f"Slide #{s['slide_id']} ({s['type'].upper()} by @{s['author']}): \"{s['text']}\"" for s in slides_data])
    total_slides = len(slides_data)

    prompt = f"""You are a viral YouTube Shorts creator specializing in fast-paced '{active_category.upper()}' content.
Write an electric, ultra-fast 45-50 SECOND YouTube Shorts script (TOTAL 90 TO 115 WORDS ACROSS ALL SLIDES).

HERE ARE THE {total_slides} VISUAL SLIDES IN SEQUENCE:
{slides_formatted}

SHORTS RETENTION RULES:
1. TOTAL WORD COUNT MUST BE UNDER 115 WORDS (So audio lasts 40-50 seconds).
2. Slide #1 (Main Tweet): Start with an insane 3-second hook (e.g. "You won't believe what {slides_data[0]['author']} just posted..." or "The entire {active_category} world is losing it...").
3. Subsequent Slides: Rapid-fire react to each user's comment/counter-take (1-2 punchy sentences each).
4. Title MUST end with '#shorts'.
5. Spoken English only: No asterisks, markdown, or timestamps.

Return strictly valid JSON:
{{
  "optimized_title": "Viral Hook Title Under 70 Chars #shorts",
  "thumbnail_slogan": "PUNCHY 3-WORD HOOK",
  "video_description": "Trending {active_category} moment #shorts #viral",
  "segments": [
    {{"slide_id": 1, "script": "High-energy 3-second hook and main tweet statement..."}},
    {{"slide_id": 2, "script": "Rapid breakdown of reaction 2..."}}
  ]
}}"""

    # Ollama প্রায়োরিটি মডেল ট্রাই করা
    ollama_keys = get_circular_key_queue("ollama", "Ollama_API_Key")
    if ollama_keys:
        for actual_idx, o_key in ollama_keys:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
            for model_name in OLLAMA_ALL_MODELS:
                try:
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "system", "content": "You are a professional YouTube Shorts scriptwriter. Output strictly valid JSON."},
                                     {"role": "user", "content": prompt}],
                        "stream": False, "format": "json"
                    }
                    resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=35)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json().get("message", {}).get("content", ""))
                        if data and data.get("segments") and len(data.get("segments")) > 0:
                            return data
                except Exception: pass

    # Groq ফলব্যাক
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            try:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are a viral YouTube Shorts scriptwriter. Output strictly valid JSON."},
                                 {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6, "max_tokens": 1500
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        return data
            except Exception: pass

    # সেফটি নেট ফলব্যাক
    main_author = slides_data[0].get("author", "VIP")
    fallback_segments = [
        {"slide_id": 1, "script": f"Wait until you see what {main_author} just posted in {active_category}. It is breaking the internet right now."}
    ]
    for s in slides_data[1:]:
        fallback_segments.append({
            "slide_id": s.get("slide_id"),
            "script": f"User {s.get('author')} fired back saying: {s.get('text')[:60]}."
        })

    return {
        "optimized_title": f"{active_category.upper()}: {main_author.upper()} JUST BROKE X! 🚨 #shorts",
        "thumbnail_slogan": "TOTAL CHAOS! 🔥",
        "video_description": f"Viral {active_category} moment #shorts",
        "segments": fallback_segments
    }
