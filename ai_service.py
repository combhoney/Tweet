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

# ------------------ [ 🤖 ১৪টি ক্যাটাগরির কঠোর গেটকিপার ] ------------------
def ai_gatekeeper_check(author, tweet_text, likes, active_category="tech"):
    clean_t = tweet_text.strip()
    if len(clean_t) < 15 or likes < 150:
        return False, "Too short or low engagement", ""

    gatekeeper_prompt = f"""You are a strict Category Gatekeeper for a US YouTube Sports & News Network.
Active Category for this run: '{active_category.upper()}'

Evaluate this tweet:
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

CATEGORY PURITY RULES:
- The tweet MUST strictly and genuinely belong to the '{active_category.upper()}' niche (e.g. if category is 'NBA', it must be about basketball/NBA; if 'F1', about Formula 1; if 'SPACE', about rockets/SpaceX/NASA; if 'TECH', about AI/tech/gadgets; if 'POLITICAL', about politics/policy).
- If the tweet is about a completely different topic (e.g., a basketball player tweeting about politics during an NBA run, or Elon tweeting a meme), REJECT IT IMMEDIATELY (is_worthy: false).
- Reject generic greetings ('gm', 'hello') or ad spam.

Return strictly valid JSON:
{{
  "is_worthy": true,
  "reason": "Why it belongs strictly to {active_category}",
  "editorial_angle": "Hook angle for this {active_category} story"
}}"""

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

    return True, "Passed check", f"Breaking {active_category.capitalize()} Story"

def generate_synchronized_script(slides_data, active_category="tech"):
    slides_formatted = "\n".join([f"Slide #{s['slide_id']} ({s['type'].upper()} by @{s['author']}): \"{s['text']}\"" for s in slides_data])
    total_slides = len(slides_data)

    prompt = f"""You are an elite US YouTube investigative sports & news host presenting a dedicated '{active_category.upper()}' segment.
Write an exhilarating, deeply engaging, natural synchronized broadcast script matching these {total_slides} visual slides in sequence:

{slides_formatted}

RULES:
1. Stay 100% focused on {active_category.upper()}.
2. For Slide #1: Open with a dramatic hook, explaining what @{slides_data[0]['author']} posted and why it's blowing up timelines.
3. For each subsequent Slide: Directly react to, analyze, and break down that specific user's reaction, counter-take, or roast.
4. Spoken English only: No asterisks, markdown, or timestamps.

Return strictly valid JSON:
{{
  "optimized_title": "Sensational High-CTR Title with emojis under 90 chars",
  "thumbnail_slogan": "ONE ULTRA PUNCHY 3-6 WORD SLOGAN IN ALL-CAPS",
  "video_description": "Engaging description with summary and 4 hashtags",
  "segments": [
    {{"slide_id": 1, "script": "Spoken narrative for Slide 1..."}},
    {{"slide_id": 2, "script": "Spoken breakdown of Reply 2..."}}
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
                        "messages": [{"role": "system", "content": "You are a professional YouTube news scriptwriter. Output strictly valid JSON only."},
                                     {"role": "user", "content": prompt}],
                        "stream": False, "format": "json"
                    }
                    resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=40)
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
                    "messages": [{"role": "system", "content": "You are a professional YouTube news scriptwriter. Output strictly valid JSON."},
                                 {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6, "max_tokens": 3000
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        return data
            except Exception: pass

    # সেফটি নেট ফলব্যাক
    main_author = slides_data[0].get("author", "VIP")
    fallback_segments = [
        {"slide_id": 1, "script": f"In a major developing story in {active_category}, {main_author} just posted a bombshell statement that has set social media on fire."}
    ]
    for s in slides_data[1:]:
        fallback_segments.append({
            "slide_id": s.get("slide_id"),
            "script": f"Responding to this, user {s.get('author')} voiced a sharp perspective, stating: {s.get('text')}. This sparked an intense community debate."
        })

    return {
        "optimized_title": f"{active_category.upper()}: {main_author.upper()} DROPPED A BOMBSHELL! 🚨",
        "thumbnail_slogan": f"TOTAL {active_category.upper()} CHAOS! 🔥",
        "video_description": f"Breaking 12-hour recap of the biggest viral controversy in {active_category}.",
        "segments": fallback_segments
    }
