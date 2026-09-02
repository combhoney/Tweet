# -*- coding: utf-8 -*-
import os, json, re

STATE_FILE = os.path.join("workspace", "api_key_state.json")

def parse_keys_multiline(env_var_name):
    """এন্টার (newline), কমা বা সেমিকোলন দিয়ে রাখা কীগুলো সুন্দরভাবে লিস্ট আকারে পড়ে"""
    raw_keys = os.environ.get(env_var_name, "").strip()
    if not raw_keys:
        return []
    # লাইন ব্রেক ও স্পেস ফিল্টার করে ভ্যালিড কী বের করা
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save key state: {e}")

def get_circular_key_queue(service_name, env_var_name):
    """
    সর্বশেষ ব্যবহৃত পয়েন্টার থেকে শুরু করে সার্কুলার লুপে (১ম থেকে শেষ এবং আবার ১ম) কী সাজিয়ে দেয়
    """
    keys = parse_keys_multiline(env_var_name)
    if not keys:
        return []

    state = load_state()
    start_index = state.get(service_name, 0) % len(keys)

    # সার্কুলার কিউ তৈরি
    queue = []
    for i in range(len(keys)):
        idx = (start_index + i) % len(keys)
        queue.append((idx, keys[idx]))
    
    return queue

def update_exhausted_key_pointer(service_name, failed_idx, total_keys):
    """লিমিট শেষ হলে পরবর্তী কী-তে পয়েন্টার শিফট করে সেভ করে রাখে"""
    state = load_state()
    next_idx = (failed_idx + 1) % total_keys
    state[service_name] = next_idx
    save_state(state)
    print(f"🔄 [{service_name.upper()}] Key #{failed_idx + 1} exhausted. Pointer shifted to Key #{next_idx + 1} (Saved for next runs).")

def update_success_key_pointer(service_name, success_idx):
    """যে কী-তে কাজ সফল হয়েছে সেটি মনে রাখে"""
    state = load_state()
    state[service_name] = success_idx
    save_state(state)
