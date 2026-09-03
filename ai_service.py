# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODELS = ["kimi-k3", "minimax-m3", "gemma4", "kimi-k2.6"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

# ------------------ [ 🤖 AI GATEKEEPER ] ------------------
def ai_gatekeeper_check(author, tweet_text, likes):
    """
    টুইটটি আসলে একটি ৩ মিনিটের ইউটিউব ভিডিও বানানোর মতো যোগ্য ও গুরুত্বপূর্ণ কিনা তা AI যাচাই করে
    """
    gatekeeper_prompt = f"""You are an elite editorial gatekeeper for a US Breaking News YouTube Channel.
Evaluate if this tweet has enough newsworthiness, debate value, or viral controversy for a standalone 2-3 minute YouTube video.

Author: @{author}
Tweet: "{tweet_text}"
Likes: {likes}

CRITERIA FOR YES (is_worthy: true):
- Major tech/AI announcements, political controversies, global policy opinions, significant market statements, scandalous revelations, or viral drama.

CRITERIA FOR NO (is_worthy: false):
- 1-word memes, simple greetings (like 'gm', 'good morning'), generic congrats, ad spam, personal check-ins without news value.

Return strictly valid JSON:
{{
  "is_worthy": true,
  "reason": "Brief reason why it's worthy or rejected",
  "editorial_angle": "Main hook/angle for the video"
}}"""

    # ১. Groq এর ফাস্ট মডেল দিয়ে দ্রুত সিদ্ধান্ত নেওয়া
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": gatekeeper_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2, "max_tokens": 200
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                if data and "is_worthy" in data:
                    return data.get("is_worthy", False), data.get("reason", ""), data.get("editorial_angle", "")
        except Exception: pass

    # ডিফল্ট: যদি লাইক ৫,০০০ এর বেশি হয় এবং টেক্সট ৬০ অক্ষরের বড় হয় তবে এলাউ করবে
    return (likes >= 5000 and len(tweet_text) >= 60), "Fallback check passed", "Breaking Viral Moment"

# ------------------ [ ব্রেকিং নিউজ স্ক্রিপ্ট (টুইট + টপ রিপ্লাই সহ) ] ------------------
def generate_tweet_commentary(author, tweet_text, top_replies=None):
    replies_context = ""
    if top_replies:
        replies_context = "\nTop Community Reactions / Counter-Replies:\n" + "\n".join([f"- @{r.get('author')}: {r.get('text')}" for r in top_replies[:3]])

    prompt = f"""You are an elite American YouTube news anchor and viral investigative commentator.
Context:
- Main Tweet Author: @{author}
- Main Tweet Content: "{tweet_text}"
{replies_context}

CRITICAL SCRIPT RULES:
1. Target: USA Audience (Dynamic, dramatic, fast-paced, insightful American English).
2. Length: 2.5 to 3 minutes (340 to 420 spoken words).
3. Structure:
   - EXPLOSIVE HOOK (0-10s): Jump right into the bombshell statement.
   - THE CORE STATEMENT: What @{author} posted and why the internet is exploding.
   - COMMUNITY WAR & TOP REPLIES: Detail the top counter-reactions and what big figures/critics are saying.
   - BIGGER PICTURE & CALL TO ACTION: What happens next? Ask viewers for their opinion in the comments.
4. Spoken English: No asterisks, markdown, or URL mentions in the voiceover script.

Return strictly valid JSON:
{{
  "optimized_title": "High-CTR Sensational Title under 90 chars with emojis",
  "voiceover_script": "Full continuous spoken script...",
  "video_description": "2-paragraph YouTube description with summary and 4 hashtags",
  "specific_tags": ["tag1", "tag2", "tag3", "tag4"],
  "top_text": "2-3 UPPERCASE words (e.g. BREAKING NEWS)",
  "row1_text": "2-3 punchy words in RED (e.g. TOTAL CHAOS)",
  "row2_text": "2-4 words in BLACK (e.g. Internet War)",
  "bot_text": "Bottom Banner text (e.g. FULL EXPLANATION)"
}}"""

    # Ollama বা Groq দিয়ে স্ক্রিপ্ট জেনারেশন
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    if groq_queue:
        for actual_idx, g_key in groq_queue:
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
            for g_model in GROQ_MODELS:
                try:
                    payload = {
                        "model": g_model,
                        "messages": [{"role": "system", "content": "You are a professional American YouTube news scriptwriter. Output strictly valid JSON."},
                                     {"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.6, "max_tokens": 2200
                    }
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                        if data and data.get("optimized_title"):
                            update_success_key_pointer("groq", actual_idx)
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

# ------------------ [ সারাদিনের সেরা ১০ টুইট মেগা রাউন্ডআপ স্ক্রিপ্ট ] ------------------
def generate_daily_top10_script(top10_tweets):
    summary_text = "\n".join([f"#{i+1}. @{t['author']} ({t['likes']:,} Likes): \"{t['text'][:120]}\"" for i, t in enumerate(top10_tweets)])
    prompt = f"""You are an elite American YouTube news anchor hosting 'Top 10 Most Viral Tweets of the Day'.
Here are the 10 biggest viral moments of the last 24 hours:
{summary_text}

SCRIPT REQUIREMENTS:
1. Write a thrilling, engaging 7-8 minute full compilation script (around 900-1100 words).
2. Dedicate a focused, punchy segment for each of the 10 viral tweets sequentially (from #10 up to the #1 biggest bombshell).
3. Connect them smoothly with exciting broadcast transitions.

Return strictly valid JSON:
{{
  "optimized_title": "TOP 10 CRAZIEST TWEETS OF THE DAY! (Internet Explodes) 🚨",
  "voiceover_script": "Full master 900-1100 word continuous broadcast script...",
  "video_description": "Daily Roundup: The 10 biggest tweets and controversies from Elon Musk, Trump, Tech & Internet Culture.",
  "specific_tags": ["Top 10 Tweets", "Twitter Roundup", "Elon Musk", "Viral Moments", "Breaking News"],
  "top_text": "DAILY ROUNDUP",
  "row1_text": "TOP 10 TWEETS",
  "row2_text": "Internet Explodes",
  "bot_text": "FULL 24-HOUR BREAKDOWN"
}}"""

    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    for actual_idx, g_key in groq_queue:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.6, "max_tokens": 3500
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
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
