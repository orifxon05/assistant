import os
import json
import time
from datetime import datetime
from .formatter import format_digest_message

DIGEST_FILE = "intelligence_daily.json"

def _load_daily_items():
    if not os.path.exists(DIGEST_FILE):
        return {"date": "", "items": []}
    try:
        with open(DIGEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"date": "", "items": []}

def _save_daily_items(data):
    try:
        with open(DIGEST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[DIGEST] Saqlashda xatolik:", e)

def record_daily_item(title, company, link, category, score, level):
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_daily_items()
    if data.get("date") != today:
        data = {"date": today, "items": []}

    data["items"].append({
        "title": title,
        "company": company,
        "link": link,
        "category": category,
        "score": score,
        "level": level,
        "time": int(time.time())
    })
    _save_daily_items(data)

def get_today_digest():
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_daily_items()
    items = data.get("items", []) if data.get("date") == today else []

    stats = {
        "💼 Vakansiyalar": sum(1 for i in items if "JOB" in i.get("category", "")),
        "🎓 Amaliyot / Shogirdlik": sum(1 for i in items if "INTERNSHIP" in i.get("category", "")),
        "🛡 Xavfsizlik (Cybersecurity)": sum(1 for i in items if "CYBERSECURITY" in i.get("category", "")),
        "🐍 Python / AI": sum(1 for i in items if ("PYTHON" in i.get("category", "") or "AI" in i.get("category", ""))),
        "💰 Grant va Kurslar": sum(1 for i in items if ("GRANT" in i.get("category", "") or "EDUCATION" in i.get("category", ""))),
    }

    # Sort items by score descending
    sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    return format_digest_message(today, stats, sorted_items)
