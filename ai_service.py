# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image
from config import DEFAULT_BASE_TAGS
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODELS = ["kimi-k3", "minimax-m3", "gemma4", "kimi-k2.6"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def encode_image_base64(image_path, max_dim=1024):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if max(img.size) > max_dim: img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception: return None

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

def generate_tweet_commentary(author, tweet_text, img_paths):
    prompt = f"""You are an elite American YouTube news commentator and viral investigative reporter.
Context:
- Author: @{author}
- Tweet Content: "{tweet_text}"

CRITICAL RULES:
1. Target Audience: USA (Fast-paced, dramatic, conversational American English).
2. Script Length: 2 to 2.5 minutes (320 to 380 words).
3. No markdown symbols or asterisks in the voiceover script.

Return strictly valid JSON:
{{
  "optimized_title": "High CTR title under 90 chars with emojis",
  "voiceover_script": "Full script here...",
  "video_description": "2-paragraph description with 4 hashtags",
  "specific_tags": ["tag1", "tag2", "tag3"],
  "top_text": "2-3 UPPERCASE words (e.g. BREAKING NEWS)",
  "row1_text": "2-3 punchy words in RED (e.g. TOTAL CHAOS)",
  "row2_text": "2-4 words in BLACK (e.g. Internet Shocked)",
  "bot_text": "Bottom Banner text (e.g. FULL EXPLANATION)"
}}"""

    base64_images = [encode_image_base64(p) for p in img_paths[:2] if encode_image_base64(p)]

    # ১. Ollama কিউ
    ollama_queue = get_circular_key_queue("ollama", "Ollama_API_Key")
    total_o_keys = len(ollama_queue)
    if ollama_queue:
        for attempt_num, (actual_idx, o_key) in enumerate(ollama_queue, start=1):
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
            key_worked = False
            for model_name in OLLAMA_MODELS:
                print(f"🤖 [Ollama] Trying Key #{actual_idx + 1} (Model: '{model_name}')...")
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt, "images": base64_images}],
                    "stream": False, "options": {"temperature": 0.6}
                }
                try:
                    resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json().get("message", {}).get("content", ""))
                        if data and data.get("optimized_title"):
                            update_success_key_pointer("ollama", actual_idx)
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
            
            # এই কী দিয়ে কোনো মডেল কাজ না করলে পয়েন্টার শিফট হবে
            update_exhausted_key_pointer("ollama", actual_idx, total_o_keys)

    # ২. Groq কিউ (ফলব্যাক)
    groq_queue = get_circular_key_queue("groq", "GROQ_API")
    total_g_keys = len(groq_queue)
    if groq_queue:
        for attempt_num, (actual_idx, g_key) in enumerate(groq_queue, start=1):
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
            for g_model in GROQ_MODELS:
                print(f"🤖 [Groq] Trying Key #{actual_idx + 1} (Model: '{g_model}')...")
                payload = {
                    "model": g_model,
                    "messages": [
                        {"role": "system", "content": "You are a professional American YouTube news scriptwriter. Output strictly valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.6,
                    "max_tokens": 2000
                }
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        raw = resp.json()['choices'][0]['message']['content']
                        data = parse_json_safely(raw)
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
            update_exhausted_key_pointer("groq", actual_idx, total_g_keys)

    return None, None, None, None, None
