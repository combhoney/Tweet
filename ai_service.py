# -*- coding: utf-8 -*-
import os, json, re, requests
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

def ai_gatekeeper_check(author, tweet_text, likes):
    clean_t = tweet_text.strip()
    if len(clean_t) < 20 or likes < 300:
        return False, "Low engagement or short text", ""

    gatekeeper_prompt = f"""Evaluate if this tweet has newsworthy or debate value:
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

Reject ONLY if pure 1-word spam or generic greeting. Output JSON: {{"is_worthy": true/false, "reason": "...", "editorial_angle": "..."}}"""

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

    return True, "Approved", "Breaking Story"

def generate_synchronized_script(slides_data):
    """
    🌟 কোনো সময়ের বাধ্যবাধকতা ছাড়াই বিষয়বস্তু অনুযায়ী সম্পূর্ণ মুক্ত ও আকর্ষণীয় স্ক্রিপ্ট তৈরি করে
    """
    slides_formatted = "\n".join([f"Slide #{s['slide_id']} ({s['type'].upper()} by @{s['author']}): \"{s['text']}\"" for s in slides_data])
    
    prompt = f"""You are an elite US YouTube investigative news anchor and commentary host.
Write an exhilarating, deeply engaging, and natural synchronized broadcast script for a video with {len(slides_data)} visual slides.

HERE ARE THE EXACT SLIDES SHOWN IN SEQUENCE:
{slides_formatted}

NATURAL STORYTELLING RULES (NO ARTIFICIAL TIME LIMITS):
1. For Slide #1 (Main Tweet): Open with an explosive hook, thoroughly explain the background story, what @{slides_data[0]['author']} posted, and why timelines are on fire. Take as much space as needed to make the intro punchy, clear, and comprehensive.
2. For each subsequent Slide (Replies/Comments): Naturally react to, break down, and analyze that specific user's counter-argument, roast, supporting point, or verified opinion. Feel free to elaborate on important debates and keep smaller points concise.
3. Flow & Cohesion: Connect all segments with smooth broadcast transitions so the entire video feels like one thrilling continuous investigative story.
4. Spoken English Only: Natural spoken American English. No markdown asterisks, timestamps, or bracketed instructions in the script text.

Return strictly valid JSON:
{{
  "optimized_title": "Sensational High-CTR Title with emojis under 90 chars",
  "thumbnail_slogan": "ONE ULTRA PUNCHY 3-6 WORD SLOGAN IN ALL-CAPS",
  "video_description": "Engaging 2-paragraph description with summary and 4 hashtags",
  "segments": [
    {{"slide_id": 1, "script": "Natural spoken narrative for Slide 1..."}},
    {{"slide_id": 2, "script": "Natural spoken breakdown of Reply 2..."}}
  ]
}}"""

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
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=35)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("segments") and len(data.get("segments")) > 0:
                        return data
            except Exception: pass
    return None
