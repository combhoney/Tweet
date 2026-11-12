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

    gatekeeper_prompt = f"""Evaluate if this tweet has commentary value for a dedicated YouTube Shorts video:
Category: '{active_category.upper()}'
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

Reject ONLY if it belongs to a completely different niche, or is pure 1-word greeting/spam.
Output strictly JSON: {{"is_worthy": true/false, "reason": "...", "editorial_angle": "..."}}"""

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

    return True, "Approved", f"Breaking {active_category.capitalize()} Story"

def generate_shorts_script(slides_data, active_category="tech"):
    """
    🌟 ১.৫ থেকে ২.৫ মিনিটের জন্য ২০০-২৮০ শব্দের স্ক্রিপ্ট
    🌟 ইউজারনেম/হ্যান্ডেল (@user_123) উচ্চারণ করা সম্পূর্ণ নিষিদ্ধ; আসল নাম বা 'A commenter' বলবে
    """
    slides_formatted = []
    for s in slides_data:
        disp_name = s.get('author_name', s.get('author', 'A user'))
        slides_formatted.append(f"Slide #{s['slide_id']} ({s['type'].upper()} by {disp_name}): \"{s['text']}\"")
    slides_context = "\n".join(slides_formatted)

    main_person = slides_data[0].get('author_name', slides_data[0].get('author', 'A prominent figure'))

    prompt = f"""You are an elite, energetic American YouTube Shorts commentary host presenting a full 1.5 to 2.2 MINUTE video on '{active_category.upper()}'.

HERE ARE THE VISUAL SLIDES IN SEQUENCE:
{slides_context}

CRITICAL NAME PRONUNCIATION RULES:
1. NEVER SAY TWITTER HANDLES OR USERNAMES! Do NOT say 'at symbol', '@handle', or random numbers.
2. ALWAYS use their real Display Name (e.g. say '{main_person}', 'Alex', 'Sarah', 'Ron DeSantis').
3. If an account name is an awkward screen name, DO NOT read it out. Instead, use natural journalistic phrasing like "A top commenter pointed out", "One critic fired back", "An analyst weighed in", "A verified fan remarked".

SCRIPT LENGTH & PACING RULES:
1. SCRIPT LENGTH: Exactly 220 to 280 words across all slides (about 1.5 to 2.2 minutes, within YouTube's 3-minute Shorts limit).
2. Slide #1 (Main Tweet): Deliver a massive opening hook and thoroughly explain what {main_person} stated, the context, and why the internet is on fire (70-90 words).
3. Subsequent Slides: Thoroughly break down each reaction, counter-take, and community argument (35-50 words each).
4. Spoken English only: No asterisks, markdown symbols, or bracketed instructions.
5. The title MUST end with '#shorts'.

Return strictly valid JSON:
{{
  "optimized_title": "Sensational High-CTR Title with emojis under 70 chars #shorts",
  "thumbnail_slogan": "ONE ULTRA PUNCHY 3-5 WORD SLOGAN IN ALL-CAPS",
  "video_description": "Trending {active_category} moment #shorts #viral",
  "segments": [
    {{"slide_id": 1, "script": "High-energy narrative for Slide 1..."}},
    {{"slide_id": 2, "script": "Natural spoken reaction discussing Reply 2..."}}
  ]
}}"""

    # ১. Ollama প্রায়োরিটি মডেল
    ollama_keys = get_circular_key_queue("ollama", "Ollama_API_Key")
    if ollama_keys:
        for actual_idx, o_key in ollama_keys:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
            for model_name in OLLAMA_ALL_MODELS:
                try:
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "system", "content": "You are a professional YouTube Shorts news host. Output strictly valid JSON."},
                                     {"role": "user", "content": prompt}],
                        "stream": False, "format": "json"
                    }
                    resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json().get("message", {}).get("content", ""))
                        if data and data.get("segments") and len(data.get("segments")) > 0:
                            return data
                except Exception: pass

    # ২. Groq ফলব্যাক
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            try:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are a professional YouTube Shorts host. Output strictly valid JSON."},
                                 {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6, "max_tokens": 2000
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        return data
            except Exception: pass

    # ৩. সেফটি নেট ফলব্যাক
    fallback_segments = [
        {"slide_id": 1, "script": f"A massive controversy has just erupted in {active_category} after {main_person} dropped a statement that has sent shockwaves across social media. The post instantly triggered an intense storm of fiery debates across every timeline."}
    ]
    for s in slides_data[1:]:
        disp = s.get("author_name", "A commenter")
        fallback_segments.append({
            "slide_id": s.get("slide_id"),
            "script": f"Reacting to this, {disp} fired back with a sharp counter-perspective, stating: {s.get('text')[:80]}. This perspective quickly ignited hundreds of comments as the debate escalated."
        })

    return {
        "optimized_title": f"{active_category.upper()}: {main_person.upper()} DROPPED A BOMBSHELL! 🚨 #shorts",
        "thumbnail_slogan": "TOTAL CHAOS! 🔥",
        "video_description": f"Trending {active_category} controversy #shorts",
        "segments": fallback_segments
    }
