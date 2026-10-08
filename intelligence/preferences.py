import os
import json

PREFERENCES_FILE = "intelligence_preferences.json"

DEFAULT_PREFERENCES = {
    "check_interval_minutes": 30,
    "is_enabled": False,  # Avtomatik fon tahlili o'chirilgan: tahlil faqat botda buyruq berilganda ishga tushadi
    "dry_run": False,
    "daily_digest_enabled": True,
    "daily_digest_time": "21:00",
    "sources": {},  # {channel_id_or_username: {"title": "...", "intent": "all", "priority": "normal", "muted": False}}
    "disliked_keywords": [],
    "boosted_keywords": [],
    "feedback_log": []
}

def load_preferences():
    if not os.path.exists(PREFERENCES_FILE):
        save_preferences(DEFAULT_PREFERENCES)
        return DEFAULT_PREFERENCES.copy()
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_PREFERENCES.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        print("[PREFERENCES] O'qishda xatolik:", e)
        return DEFAULT_PREFERENCES.copy()

def save_preferences(data):
    try:
        with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("[PREFERENCES] Saqlashda xatolik:", e)
        return False

def get_check_interval():
    prefs = load_preferences()
    return prefs.get("check_interval_minutes", 30)

def set_check_interval(minutes):
    prefs = load_preferences()
    prefs["check_interval_minutes"] = max(5, int(minutes))
    save_preferences(prefs)
    return prefs["check_interval_minutes"]

def is_intelligence_enabled():
    prefs = load_preferences()
    return prefs.get("is_enabled", True)

def set_intelligence_enabled(enabled: bool):
    prefs = load_preferences()
    prefs["is_enabled"] = bool(enabled)
    save_preferences(prefs)
    return prefs["is_enabled"]

def update_source_preference(channel_identifier, title=None, intent="all", priority="normal", muted=False):
    prefs = load_preferences()
    sources = prefs.setdefault("sources", {})
    key = str(channel_identifier).lower()
    item = sources.get(key, {})
    if title:
        item["title"] = title
    item["intent"] = intent  # 'jobs', 'education', 'news', 'all'
    item["priority"] = priority  # 'high', 'normal', 'low'
    item["muted"] = muted
    sources[key] = item
    save_preferences(prefs)
    return item

def record_feedback(post_title, feedback_type, note=""):
    """
    feedback_type: 'dislike', 'like', 'too_experienced', 'wrong_field', 'more_like_this'
    """
    prefs = load_preferences()
    log = prefs.setdefault("feedback_log", [])
    log.append({
        "post_title": post_title,
        "type": feedback_type,
        "note": note
    })
    # Keep last 100 feedbacks
    prefs["feedback_log"] = log[-100:]

    if feedback_type in ["dislike", "wrong_field"] and note:
        if note.lower() not in prefs["disliked_keywords"]:
            prefs["disliked_keywords"].append(note.lower())
    elif feedback_type in ["like", "more_like_this"] and note:
        if note.lower() not in prefs["boosted_keywords"]:
            prefs["boosted_keywords"].append(note.lower())

    save_preferences(prefs)
