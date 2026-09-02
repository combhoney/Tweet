# -*- coding: utf-8 -*-
import os, re, time, asyncio, requests
from moviepy.editor import AudioFileClip, concatenate_audioclips
import edge_tts
from config import USE_ELEVENLABS, TMP_DIR
from key_manager import get_circular_key_queue, update_exhausted_key_pointer, update_success_key_pointer

DEFAULT_USA_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB") # Adam
MICROSOFT_EDGE_VOICE = "en-US-ChristopherNeural" # আমেরিকান ডিপ নিউজ কাস্টার ভয়েস

def clean_script_for_speech(text):
    if not text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def split_into_speech_chunks(script, max_chars=250):
    """স্ক্রিপ্টটিকে অর্থপূর্ণ ছোট ছোট বাক্যের অংশে বিভক্ত করে যাতে ভয়েস ন্যাচারাল থাকে"""
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

# ------------------ [ ইঞ্জিন ১: ElevenLabs Chunked Generator ] ------------------
def synthesize_chunk_elevenlabs(chunk_text, out_path, key_queue):
    total_keys = len(key_queue)
    voice_id = DEFAULT_USA_VOICE_ID
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    for actual_idx, api_key in key_queue:
        payload = {
            "text": chunk_text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.80}
        }
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        try:
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                update_success_key_pointer("elevenlabs", actual_idx)
                return True
            else:
                update_exhausted_key_pointer("elevenlabs", actual_idx, total_keys)
        except Exception:
            update_exhausted_key_pointer("elevenlabs", actual_idx, total_keys)
            continue
    return False

# ------------------ [ ইঞ্জিন ২: Microsoft Edge-TTS (১০০% ফ্রি) ] ------------------
async def _synthesize_edge_async(text, out_path):
    communicate = edge_tts.Communicate(text, MICROSOFT_EDGE_VOICE)
    await communicate.save(out_path)

def synthesize_chunk_edge_tts(chunk_text, out_path):
    try:
        asyncio.run(_synthesize_edge_async(chunk_text, out_path))
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception as e:
        print(f"⚠️ Edge-TTS error on chunk: {e}")
        return False

# ------------------ [ প্রধান কম্বাইন্ড অডিও পাইপলাইন ] ------------------
def generate_voiceover_audio_pipeline(text, final_output_audio_path):
    print("\n" + "="*65)
    engine_name = "ElevenLabs AI (API Key Pool)" if USE_ELEVENLABS else "Microsoft Edge-TTS (Free Neural)"
    print(f"🎙️ [AUDIO ENGINE] Voice Synthesis Mode: {engine_name}")
    print("="*65)

    clean_text = clean_script_for_speech(text)
    chunks = split_into_speech_chunks(clean_text)
    print(f"✂️ [Script Segmentation] Divided script into {len(chunks)} continuous chunks.")

    key_queue = get_circular_key_queue("elevenlabs", "ELEVENLABS_API_KEYS") if USE_ELEVENLABS else []
    temp_chunk_files = []
    success = True

    for i, chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(TMP_DIR, f"chunk_{i}.mp3")
        print(f"  • Generating Chunk #{i}/{len(chunks)}: \"{chunk[:40]}...\"")

        if USE_ELEVENLABS:
            ok = synthesize_chunk_elevenlabs(chunk, chunk_file, key_queue)
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

    # 🌟 অডিও ক্লিপগুলো একসাথে জোড়া লাগানো
    print(f"🔗 [Audio Stitching] Merging {len(temp_chunk_files)} audio chunks into final master track...")
    try:
        clips = [AudioFileClip(f) for f in temp_chunk_files]
        final_audio = concatenate_audioclips(clips)
        final_audio.write_audiofile(final_output_audio_path, fps=44100, logger=None)
        
        for c in clips: c.close()
        final_audio.close()

        # টেম্পোরারি খণ্ড অডিওগুলো রিমুভ করা
        for f in temp_chunk_files:
            try: os.remove(f)
            except Exception: pass

        print(f"✅ Master Voiceover Ready: {final_output_audio_path}")
        return True
    except Exception as merge_err:
        print(f"❌ Error merging audio clips: {merge_err}")
        return False
