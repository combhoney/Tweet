# -*- coding: utf-8 -*-
import os, re, asyncio
import soundfile as sf
import numpy as np
from moviepy.editor import AudioFileClip, concatenate_audioclips
import edge_tts
from config import TTS_ENGINE, TMP_DIR

# ভয়েস কনফিগারেশন
KOKORO_VOICE = "am_adam"                   # Kokoro-র আমেরিকান ডিপ ধারাভাষ্য ভয়েস (Adam)
EDGE_VOICE = "en-US-ChristopherNeural"     # Edge-TTS এর আমেরিকান নিউজ অ্যাঙ্কর ভয়েস

_kokoro_pipeline = None

def get_kokoro_pipeline():
    """Kokoro Pipeline লোড ও ক্যাশ করে রাখে যাতে দ্রুত জেনারেট হয়"""
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        from kokoro import KPipeline
        print("🧠 [Kokoro TTS] Loading American English AI Pipeline ('a')...")
        _kokoro_pipeline = KPipeline(lang_code='a')
    return _kokoro_pipeline

def clean_script_for_speech(text):
    if not text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def split_into_speech_chunks(script, max_chars=250):
    sentences = re.split(r'(?<=[.!?])\s+', script)
    chunks = []
    current_chunk = ""

    for s in sentences:
        s = s.strip()
        if not s: continue
        if len(current_chunk) + len(s) + 1 <= max_chars:
            current_chunk = (current_chunk + " " + s).strip()
        else:
            if current_chunk: chunks.append(current_chunk)
            current_chunk = s

    if current_chunk: chunks.append(current_chunk)
    return chunks

# ------------------ [ ইঞ্জিন ১: Kokoro TTS ] ------------------
def synthesize_chunk_kokoro(chunk_text, out_path):
    try:
        pipeline = get_kokoro_pipeline()
        generator = pipeline(chunk_text, voice=KOKORO_VOICE, speed=1.0, split_pattern=r'\n+')
        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)
            
        if audio_segments:
            combined = np.concatenate(audio_segments)
            sf.write(out_path, combined, 24000)
            return True
    except Exception as e:
        print(f"⚠️ Kokoro synthesis failed on chunk: {e}")
    return False

# ------------------ [ ইঞ্জিন ২: Microsoft Edge-TTS ] ------------------
async def _synthesize_edge_async(text, out_path):
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await communicate.save(out_path)

def synthesize_chunk_edge_tts(chunk_text, out_path):
    try:
        asyncio.run(_synthesize_edge_async(chunk_text, out_path))
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception as e:
        print(f"⚠️ Edge-TTS error on chunk: {e}")
        return False

# ------------------ [ প্রধান অডিও পাইপলাইন ] ------------------
def generate_voiceover_audio_pipeline(text, final_output_audio_path):
    print("\n" + "="*65)
    selected_engine = "Kokoro Open-Source TTS" if "kokoro" in TTS_ENGINE else "Microsoft Edge-TTS"
    print(f"🎙️ [AUDIO ENGINE] Active TTS: {selected_engine.upper()}")
    print("="*65)

    clean_text = clean_script_for_speech(text)
    chunks = split_into_speech_chunks(clean_text)
    print(f"✂️ [Script Segmentation] Divided script into {len(chunks)} continuous chunks.")

    temp_chunk_files = []
    success = True

    for i, chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(TMP_DIR, f"chunk_{i}.wav" if "kokoro" in TTS_ENGINE else f"chunk_{i}.mp3")
        print(f"  • Generating Chunk #{i}/{len(chunks)}: \"{chunk[:40]}...\"")

        if "kokoro" in TTS_ENGINE:
            ok = synthesize_chunk_kokoro(chunk, chunk_file)
            if not ok:
                print("  🔄 Kokoro fallback ➔ Trying Edge-TTS for this chunk...")
                chunk_file = os.path.join(TMP_DIR, f"chunk_{i}.mp3")
                ok = synthesize_chunk_edge_tts(chunk, chunk_file)
        else:
            ok = synthesize_chunk_edge_tts(chunk, chunk_file)

        if ok and os.path.exists(chunk_file):
            temp_chunk_files.append(chunk_file)
        else:
            print(f"❌ Failed to synthesize Chunk #{i}!")
            success = False
            break

    if not success or not temp_chunk_files:
        print("❌ [AUDIO FAILED] Aborting audio pipeline.")
        return False

    # অডিও ক্লিপগুলো একসাথে জোড়া লাগানো
    print(f"🔗 [Audio Stitching] Merging {len(temp_chunk_files)} audio chunks into master track...")
    try:
        clips = [AudioFileClip(f) for f in temp_chunk_files]
        final_audio = concatenate_audioclips(clips)
        final_audio.write_audiofile(final_output_audio_path, fps=44100, logger=None)
        
        for c in clips: c.close()
        final_audio.close()

        # অস্থায়ী ফাইল ক্লিনআপ
        for f in temp_chunk_files:
            try: os.remove(f)
            except Exception: pass

        print(f"✅ Master Voiceover Ready: {final_output_audio_path}")
        return True
    except Exception as merge_err:
        print(f"❌ Error merging audio clips: {merge_err}")
        return False
