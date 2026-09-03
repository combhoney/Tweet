# -*- coding: utf-8 -*-
import os, re, asyncio
import soundfile as sf
import numpy as np
import edge_tts
from config import TTS_ENGINE, TMP_DIR

KOKORO_VOICE = "am_adam"
EDGE_VOICE = "en-US-ChristopherNeural"

_kokoro_pipeline = None

def get_kokoro_pipeline():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        from kokoro import KPipeline
        print("🧠 [Kokoro TTS] Loading American English AI Pipeline...")
        _kokoro_pipeline = KPipeline(lang_code='a')
    return _kokoro_pipeline

def clean_script_for_speech(text):
    if not text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def synthesize_audio_segment(text, out_path):
    """একটি সেগমেন্টের অডিও তৈরি করে"""
    clean_text = clean_script_for_speech(text)
    if "kokoro" in TTS_ENGINE:
        try:
            pipeline = get_kokoro_pipeline()
            generator = pipeline(clean_text, voice=KOKORO_VOICE, speed=1.0, split_pattern=r'\n+')
            segments = [audio for _, _, audio in generator]
            if segments:
                combined = np.concatenate(segments)
                sf.write(out_path, combined, 24000)
                return True
        except Exception: pass

    # Edge-TTS ফলব্যাক
    try:
        async def _run():
            communicate = edge_tts.Communicate(clean_text, EDGE_VOICE)
            await communicate.save(out_path)
        asyncio.run(_run())
        return os.path.exists(out_path) and os.path.getsize(out_path) > 500
    except Exception: return False
