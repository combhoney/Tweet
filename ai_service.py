# -*- coding: utf-8 -*-
import os, json, re, requests
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODELS = ["gemma4", "kimi-k3", "minimax-m3"]
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
        return False, f"Too short or low engagement ({likes} likes)", ""

    gatekeeper_prompt = f"""Evaluate if this tweet has newsworthy or debate value for a 2-minute YouTube news video:
Author: @{author}
Tweet: "{clean_t}"
Likes: {likes}

Reject ONLY if it is pure 1-word spam or generic greeting. Otherwise ACCEPT.
Return JSON: {{"is_worthy": true/false, "reason": "...", "editorial_angle": "..."}}"""

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

def generate_tweet_commentary(author, tweet_text, replies_data=None):
    replies_summary = ""
    if replies_data:
        replies_summary = "\nTop Verified Reactions & Counter-Takes:\n" + "\n".join([f"- @{r.get('author')}: \"{r.get('text')[:90]}\"" for r in replies_data[:6]])

    prompt = f"""You are an elite US YouTube investigative news anchor (like Vox or Johnny Harris).
Write a thrilling, fast-paced 2.5-minute spoken commentary script (340-400 words) for USA viewers.

Context:
- Main Tweet Author: @{author}
- Main Tweet Statement: "{tweet_text}"
{replies_summary}

STORY & SLIDE PACING:
1. HOOK: What was just posted by @{author} and why it's breaking the internet.
2. CONTEXT: The backstory and why this matters right now.
3. COMMUNITY WAR & REACTIONS: Walk through the top verified opinions, brutal counter-arguments, and community drama in the replies.
4. FINAL IMPACT & CTA: What happens next? Ask viewers for their thoughts in the comments.

Return strictly valid JSON:
{{
  "optimized_title": "Sensational High-CTR Title with emojis under 90 chars",
  "thumbnail_slogan": "ONE ULTRA PUNCHY 3-6 WORD SLOGAN IN ALL-CAPS",
  "voiceover_script": "Full continuous spoken script...",
  "video_description": "Engaging description with summary and 4 hashtags",
  "specific_tags": ["Breaking News", "Twitter Viral", "Trending X"]
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
                    "temperature": 0.6, "max_tokens": 2000
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                    if data and data.get("optimized_title") and data.get("voiceover_script"):
                        return (
                            data.get("optimized_title").strip()[:100],
                            data.get("voiceover_script").strip(),
                            {"thumbnail_slogan": data.get("thumbnail_slogan", "BREAKING NEWS ALERT! 🚨")},
                            data.get("video_description", "").strip(),
                            data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                        )
            except Exception: pass

    # Ollama ফলব্যাক
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
                            {"thumbnail_slogan": data.get("thumbnail_slogan", "BREAKING NEWS ALERT! 🚨")},
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

Write a thrilling 7-8 minute full compilation script (900-1100 words).
Provide ONE ultra-catchy ALL-CAPS thumbnail slogan (e.g. TOP 10 CRAZIEST TWEETS TODAY! 🔥).

Return strictly valid JSON:
{{
  "optimized_title": "TOP 10 CRAZIEST TWEETS OF THE DAY! (Internet Explodes) 🚨",
  "thumbnail_slogan": "TOP 10 CRAZIEST TWEETS TODAY! 🔥",
  "voiceover_script": "Full master continuous script...",
  "video_description": "Daily Roundup of the 10 most viral tweets on X today.",
  "specific_tags": ["Top 10 Tweets", "Twitter Viral", "Trending News"]
}}"""

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
                        {"thumbnail_slogan": data.get("thumbnail_slogan", "TOP 10 CRAZIEST TWEETS TODAY! 🔥")},
                        data.get("video_description", "").strip(),
                        data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                    )
        except Exception: pass
    return None, None, None, None, None
