# -*- coding: utf-8 -*-
import os, json, re, requests
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODELS = ["gemma4", "kimi-k3", "minimax-m3"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def parse_json_safely(raw_text):
    if not raw_text: return None
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

def clean_script_text(text):
    if not text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# ------------------ [ 🤖 AI GATEKEEPER ] ------------------
def ai_gatekeeper_check(author, tweet_text, likes):
    clean_t = tweet_text.strip()
    if len(clean_t) < 15 or likes < 250:
        return False, "Low engagement or too short", ""

    gatekeeper_prompt = f"""Evaluate if this tweet has commentary value for a 2-minute YouTube news video:
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

Reject ONLY if pure 1-word spam or generic greeting. Output JSON with boolean is_worthy:
{{"is_worthy": true, "reason": "Newsworthy statement", "editorial_angle": "Breaking Story"}}"""

    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": gatekeeper_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2, "max_tokens": 150
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                if data and "is_worthy" in data:
                    return data.get("is_worthy", True), data.get("reason", "Approved"), data.get("editorial_angle", "Breaking Story")
        except Exception: pass

    return True, "Passed engagement check", "Breaking Story"

# ------------------ [ ১০০% সুসংগত মাল্টি-স্লাইড স্ক্রিপ্ট ইঞ্জিন ] ------------------
def generate_synchronized_script(slides_data):
    """
    প্রতিটি স্লাইড এবং কমেন্টের সাথে হুবহু মিলিয়ে নিখুঁত স্ক্রিপ্ট সেগমেন্ট তৈরি করে (Groq + Ollama Fallback)
    """
    slides_formatted = "\n".join([f"Slide #{s['slide_id']} ({s['type'].upper()} by @{s['author']}): \"{s['text']}\"" for s in slides_data])
    total_slides = len(slides_data)

    prompt = f"""You are an elite US YouTube investigative news anchor and commentary host.
Write an exhilarating, deeply engaging synchronized broadcast script matching these {total_slides} visual slides in order:

{slides_formatted}

INSTRUCTIONS:
1. For Slide #1 (Main Tweet): Open with an explosive hook, explaining what @{slides_data[0]['author']} posted and the massive internet shockwave.
2. For each subsequent Slide: Directly react to, break down, and analyze that specific user's counter-argument, roast, or verified opinion shown on that slide.
3. Spoken English only: No markdown asterisks, bracketed notes, or timestamps.

Return strictly valid JSON with this exact structure:
{{
  "optimized_title": "Sensational High-CTR Title with emojis under 90 chars",
  "thumbnail_slogan": "ONE ULTRA PUNCHY 3-6 WORD SLOGAN IN ALL-CAPS",
  "video_description": "Engaging 2-paragraph description with summary and 4 hashtags",
  "segments": [
    {{"slide_id": 1, "script": "Spoken words introducing Slide 1..."}},
    {{"slide_id": 2, "script": "Spoken words discussing Reply 2..."}}
  ]
}}"""

    # ১. Groq ইঞ্জিন চেষ্টা করা
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            try:
                print(f"  🤖 [Groq AI] Attempting Key #{actual_idx+1} ({g_model})...")
                payload = {
                    "model": g_model,
                    "messages": [
                        {"role": "system", "content": "You are a professional YouTube news scriptwriter. You must output valid JSON containing an array of segments for all slides."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6, "max_tokens": 3000
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    raw_text = resp.json()['choices'][0]['message']['content']
                    data = parse_json_safely(raw_text)
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        update_success_key_pointer("groq", actual_idx)
                        print(f"  ✨ [Groq Success] Generated {len(data.get('segments'))} synced script segments!")
                        return data
                else:
                    print(f"  ⚠️ Groq returned HTTP {resp.status_code}: {resp.text[:120]}")
            except Exception as ge:
                print(f"  ⚠️ Groq exception: {ge}")

    # ২. Ollama ক্লাউড ব্যাকআপ
    ollama_keys = get_circular_key_queue("ollama", "Ollama_API_Key")
    for actual_idx, o_key in ollama_keys:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
        for o_model in OLLAMA_MODELS:
            try:
                print(f"  🤖 [Ollama AI Backup] Attempting Key #{actual_idx+1} ({o_model})...")
                payload = {
                    "model": o_model,
                    "messages": [{"role": "user", "content": prompt + "\nOutput strictly valid JSON only."}],
                    "stream": False, "options": {"temperature": 0.6}
                }
                resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=40)
                if resp.status_code == 200:
                    raw_text = resp.json().get("message", {}).get("content", "")
                    data = parse_json_safely(raw_text)
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        print(f"  ✨ [Ollama Success] Generated {len(data.get('segments'))} synced script segments!")
                        return data
            except Exception as oe:
                print(f"  ⚠️ Ollama exception: {oe}")

    # ৩. অটোমেটিক ফলব্যাক স্ক্রিপ্ট জেনারেটর (যাতে কোনো ভিডিও ফেইল না হয়)
    print("  🛠️ [AI Fallback] Creating structured narrative segments from slides metadata...")
    main_author = slides_data[0].get("author", "VIP")
    main_text = slides_data[0].get("text", "")
    
    fallback_segments = [
        {"slide_id": 1, "script": f"In a shocking turn of events, {main_author} just took to X and dropped a major statement that has sent shockwaves across the entire internet. The post immediately went viral, triggering an intense wave of reactions, fiery debates, and community backlash across every single timeline."}
    ]
    
    for s in slides_data[1:]:
        s_id = s.get("slide_id")
        author = s.get("author", "User")
        text = clean_script_text(s.get("text", ""))
        fallback_segments.append({
            "slide_id": s_id,
            "script": f"Reacting to this bombshell, user {author} weighed in with a sharp perspective, stating: {text}. This response quickly gained massive traction as thousands of people joined the heated conversation."
        })

    return {
        "optimized_title": f"{main_author.upper()} JUST BROKE THE INTERNET! (Full Reaction) 🚨",
        "thumbnail_slogan": "TOTAL CHAOS ON X! 🔥",
        "video_description": f"Breaking breakdown of the massive viral statement by @{main_author} and the wild internet reactions.",
        "segments": fallback_segments
}
