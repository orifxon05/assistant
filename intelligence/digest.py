# -*- coding: utf-8 -*-
"""
digest.py - Jarvis Kunlik Intelligence Hisoboti (Daily Digest) moduli

Vazifalari:
1. Har bir relevant post (score >= 75) uchun ma'lumotlarni kunlik saqlab borish.
2. Statistikani quyidagi 5 ta asosiy toifa bo'yicha hisoblash:
   - 💼 Vakansiya
   - 🎓 Internship
   - 🛡 Cybersecurity
   - 🤖 AI
   - 🎓 Ta'lim
3. Eng yuqori ball to'plagan 3 ta e'lonni ajratib olish va har biriga qisqa "Nega senga mos" yozish.
4. Faqat relevant (75+ ball) postlarni kiritish, past balliklarni filtrlab tashlash.
"""

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


def generate_vacancy_digest_reason(match_result):
    """
    Vakansiya tahlilidan qisqa va lo'nda "Nega senga mos" sababini shakllantiradi.
    """
    reasons = []
    c = match_result.get("criteria", {})
    v = match_result.get("vacancy_summary", {})
    title = v.get("title", "")
    hours = v.get("working_hours", "")
    loc = v.get("location", "")
    exp = v.get("experience_required", "")

    # 1. Feedback sababi (agar bo'lsa, eng birinchi)
    fb_reasons = match_result.get("feedback_reasons", [])
    if fb_reasons:
        clean_fb = fb_reasons[0].replace("•", "").strip()
        reasons.append(clean_fb)

    # 2. Soha / Qiziqish
    matched_interests = c.get("interest", {}).get("matched_interests", [])
    if matched_interests:
        clean_int = matched_interests[0].split("(")[0].strip()
        reasons.append(f"{clean_int} sohasi")
    elif any(k in title.lower() for k in ["soc", "siem", "cyber", "pentest"]):
        reasons.append("Cybersecurity sohasi")
    elif "python" in title.lower():
        reasons.append("Python dasturlash")

    # 3. Vaqt jadvali
    sched = c.get("schedule", {})
    if not sched.get("has_conflict"):
        if any(h in hours for h in ["14:00", "13:00"]) or any(k in hours.lower() for k in ["part-time", "erkin", "yarim"]):
            reasons.append("o‘qishdan keyingi vaqtga mos")
        else:
            reasons.append("o'qish jadvalingizga mos")

    # 4. Joylashuv yoki Tajriba
    if "remote" in loc.lower() or "masofaviy" in loc.lower():
        reasons.append("masofaviy (Remote)")
    elif any(k in title.lower() or k in exp.lower() for k in ["intern", "stajyor", "trainee"]):
        reasons.append("Junior/Intern daraja")
    elif "toshkent" in loc.lower():
        reasons.append("Toshkent")

    if not reasons:
        reasons.append("Profilingizga mos vakansiya")

    # Dublikatlarni tozalab, 3 tasini birlashtirish
    unique_reasons = list(dict.fromkeys(reasons))
    return ", ".join(unique_reasons[:3])


def is_vacancy_item(item):
    cat = (item.get("category") or "").lower()
    title = (item.get("title") or "").lower()
    return (
        "vakansiya" in cat or "job" in cat or "ish" in cat or
        any(r in title for r in ["intern", "developer", "analyst", "operator", "engineer", "muhandis", "trainee", "stajyor", "mutaxassis"])
    )


def is_internship_item(item):
    text = f"{item.get('title', '')} {item.get('category', '')} {item.get('why_match', '')}".lower()
    return any(k in text for k in ["intern", "stajyor", "trainee", "amaliyot", "shogird", "apprentice"])


def is_cybersecurity_item(item):
    text = f"{item.get('title', '')} {item.get('category', '')} {item.get('why_match', '')}".lower()
    return any(k in text for k in ["cyber", "soc", "siem", "pentest", "xavfsizlik", "security", "edr", "incident", "infosec", "antifraud", "dlp", "kiber"])


def is_ai_item(item):
    text = f"{item.get('title', '')} {item.get('category', '')} {item.get('why_match', '')}".lower()
    return any(k in text for k in ["ai", "ml", "artificial intelligence", "sun'iy intellekt", "data science", "machine learning", "nlp", "llm", "deep learning", "gpt"])


def is_education_item(item):
    text = f"{item.get('title', '')} {item.get('category', '')} {item.get('why_match', '')}".lower()
    return any(k in text for k in ["kurs", "bootcamp", "grant", "scholarship", "hackathon", "sertifikat", "ta'lim", "talim", "education", "olimpiada", "konferensiya"])


def record_daily_item(title, company, link, category, score, level, why_match=None, source=""):
    """
    Faqat relevant postlarni (score >= 75) kunlik xulosaga yozadi.
    Takroriy yozuvlar (bir xil havola yoki sarlavha) avtomatik filtrlanadi.
    """
    if score < 75:
        # Qat'iy qoida: Faqat relevant postlarni qo'shish!
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_daily_items()
    if data.get("date") != today:
        data = {"date": today, "items": []}

    items = data.setdefault("items", [])

    # Takrorlanishni tekshirish (deduplication)
    for it in items:
        if link and it.get("link") == link:
            if score > it.get("score", 0):
                it["score"] = score
                if why_match:
                    it["why_match"] = why_match
            return False
        if it.get("title", "").strip().lower() == title.strip().lower() and it.get("company", "").strip().lower() == company.strip().lower():
            return False

    items.append({
        "title": title,
        "company": company or "Ko'rsatilmagan",
        "link": link,
        "category": category or "Umumiy",
        "score": score,
        "level": level,
        "why_match": why_match or "Profilingizga mos imkoniyat",
        "source": source or "Kanal",
        "time": int(time.time())
    })

    _save_daily_items(data)
    return True


def get_today_digest():
    """
    Bugungi kunlik qisqa Intelligence hisobotini generatsiya qiladi.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_daily_items()
    raw_items = data.get("items", []) if data.get("date") == today else []

    # Faqat 75+ ballik relevant postlarni qoldirish
    items = [i for i in raw_items if i.get("score", 0) >= 75]

    stats = {
        "vakansiya": sum(1 for i in items if is_vacancy_item(i)),
        "internship": sum(1 for i in items if is_internship_item(i)),
        "cybersecurity": sum(1 for i in items if is_cybersecurity_item(i)),
        "ai": sum(1 for i in items if is_ai_item(i)),
        "education": sum(1 for i in items if is_education_item(i)),
    }

    # Eng yuqori balliklarini tartiblash
    sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    return format_digest_message(today, stats, sorted_items)
