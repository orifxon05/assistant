import os
import json
import hashlib
import time

STATE_FILE = "intelligence_state.json"
SEEN_FILE = "intelligence_seen.json"

def _safe_load_json(file_path, default):
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[STATE] {file_path} o'qishda xatolik:", e)
        return default

def _safe_save_json(file_path, data):
    tmp_file = file_path + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(tmp_file, file_path)
        return True
    except Exception as e:
        print(f"[STATE] {file_path} saqlashda xatolik:", e)
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        return False

def load_intelligence_state():
    return _safe_load_json(STATE_FILE, {})

def save_intelligence_state(state):
    return _safe_save_json(STATE_FILE, state)

def get_channel_last_id(channel_id):
    state = load_intelligence_state()
    chat_data = state.get(str(channel_id), {})
    return chat_data.get("last_message_id", 0)

def update_channel_state(channel_id, last_message_id, channel_title=""):
    state = load_intelligence_state()
    str_id = str(channel_id)
    chat_data = state.get(str_id, {})
    chat_data["last_message_id"] = max(chat_data.get("last_message_id", 0), last_message_id)
    chat_data["last_check_time"] = int(time.time())
    if channel_title:
        chat_data["channel_title"] = channel_title
    state[str_id] = chat_data
    save_intelligence_state(state)

def load_seen_hashes():
    return set(_safe_load_json(SEEN_FILE, []))

def save_seen_hashes(hashes_set):
    # Keep only the last 2000 hashes to prevent file bloating
    hashes_list = list(hashes_set)[-2000:]
    return _safe_save_json(SEEN_FILE, hashes_list)

def compute_message_hash(text):
    if not text:
        return ""
    # Normalize text by removing extra spaces and lowercasing
    clean = " ".join(text.lower().split()[:60])
    return hashlib.md5(clean.encode("utf-8")).hexdigest()

def is_message_seen(text, msg_id=None, chat_id=None):
    if not text or len(text.strip()) < 10:
        return True
    seen = load_seen_hashes()
    text_hash = compute_message_hash(text)
    if text_hash in seen:
        return True
    if msg_id and chat_id:
        pair_id = f"{chat_id}:{msg_id}"
        if pair_id in seen:
            return True
    return False

def mark_message_seen(text, msg_id=None, chat_id=None):
    seen = load_seen_hashes()
    text_hash = compute_message_hash(text)
    if text_hash:
        seen.add(text_hash)
    if msg_id and chat_id:
        seen.add(f"{chat_id}:{msg_id}")
    save_seen_hashes(seen)

def is_daily_tpd_paused():
    """
    Groq kunlik token limiti (TPD) tugaganligi sababli monitoring bugun uchun
    to'xtatilganligini tekshiradi. Kun almashganda (ertaga) avtomatik False bo'ladi.
    """
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    state = load_intelligence_state()
    return state.get("daily_tpd_pause_date") == today_str

def set_daily_tpd_paused(paused=True):
    """
    Kunlik TPD limiti tugaganda monitoringni bugungi sana uchun pauzaga qo'yadi.
    """
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    state = load_intelligence_state()
    if paused:
        state["daily_tpd_pause_date"] = today_str
    else:
        state.pop("daily_tpd_pause_date", None)
    save_intelligence_state(state)
