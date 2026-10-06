# -*- coding: utf-8 -*-
"""
skills_profile.py - Jarvis Skills Profile Module

Modul vazifalari:
1. Foydalanuvchining ko'nikmalar (skills) profilini boshqarish:
   - Universitet (university)
   - Kurslar (courses)
   - Sertifikatlar (certifications)
   - Dasturlash tillari (programming_languages)
   - Cybersecurity bilimlari (cybersecurity_knowledge)
   - Linux (linux)
   - Networking (networking)
   - SIEM (siem)
   - Python (python)
   - Git/GitHub (git_github)
   - Ingliz tili (english)
   - Rus tili (russian)
   - Tajriba (experience)
   - Portfolio/GitHub loyihalari (portfolio_projects)
2. Har bir skill uchun 3 ta aniq daraja:
   - Beginner (Boshlovchi)
   - Intermediate (O'rta)
   - Advanced (Yuqori)
3. Royxatga olishning eng oson varianti (Easy UX):
   - 1-bosishda inline tugmalar orqali daraja tanlash (1-tap level selector)
   - Tayyor shablonlar (Presets: SOC Analyst, Python Dev va h.k.)
   - Darajalarni tezkor o'zgartirgich (1-klikda Beginner -> Intermediate -> Advanced)
   - Matnli smart parser (bir xabarda bir nechta skill va darajani o'rnatish)
4. Barcha ma'lumotlarni `skills_profile.json` faylida saqlash.
"""

import os
import re
import json
from datetime import datetime

SKILLS_FILE = "skills_profile.json"

LEVELS = ["Beginner", "Intermediate", "Advanced"]

LEVEL_BADGES = {
    "Beginner": "🟢 Beginner",
    "Intermediate": "🟡 Intermediate",
    "Advanced": "🔴 Advanced",
    "None": "⚪ Belgilanmagan"
}

LEVEL_METERS = {
    "Beginner": "▰▰▰▱▱▱▱▱▱",
    "Intermediate": "▰▰▰▰▰▰▱▱▱",
    "Advanced": "▰▰▰▰▰▰▰▰▰",
    "None": "▱▱▱▱▱▱▱▱▱"
}

# 14 ta asosiy bo'lim konfiguratsiyasi
SKILL_STEPS = [
    {
        "id": "university",
        "title": "🎓 1/14: Universitet",
        "name": "Universitet",
        "type": "text_or_pick",
        "prompt": (
            "🎓 <b>1/14: Universitet va Oliy ta'lim</b>\n\n"
            "Qaysi oliygohda o'qiysiz yoki tamomlagansiz?\n"
            "<i>(Tugmalardan birini bosing yoki nomini yozing)</i>"
        ),
        "options": ["TATU", "INHA", "O'zMU", "Mustaqil / O'zi o'rgangan", "Toshkent Davlat Yuridik"]
    },
    {
        "id": "courses",
        "title": "📚 2/14: O'quv kurslari",
        "name": "Kurslar",
        "type": "text_or_pick",
        "prompt": (
            "📚 <b>2/14: O'quv kurslari va akademiyalar</b>\n\n"
            "Qaysi o'quv markazlari yoki platformalarda tahsil olgansiz?\n"
            "<i>(Masalan: Najot Ta'lim, Coursera, Astrum, Mohirdev, Udemy...)</i>"
        ),
        "options": ["Najot Ta'lim", "Coursera (Google)", "Astrum", "Mohirdev", "Udemy", "Mustaqil (YouTube)"]
    },
    {
        "id": "certifications",
        "title": "📜 3/14: Sertifikatlar",
        "name": "Sertifikatlar",
        "type": "text_or_pick",
        "prompt": (
            "📜 <b>3/14: Xalqaro sertifikatlar</b>\n\n"
            "Qanday xalqaro yoki kasbiy sertifikatlarga egasiz (yoki tayyorlanyapsiz)?\n"
            "<i>(Masalan: CompTIA Security+, CEH, CCNA, Google Cybersecurity...)</i>"
        ),
        "options": ["CompTIA Security+", "Google Cybersecurity", "CCNA", "CEH", "Hozircha yo'q / Tayyorlanmoqda"]
    },
    {
        "id": "programming_languages",
        "title": "💻 4/14: Dasturlash tillari",
        "name": "Dasturlash tillari",
        "type": "skill_level",
        "prompt": (
            "💻 <b>4/14: Dasturlash tillari darajangiz</b>\n\n"
            "Umumiy dasturlash bo'yicha darajangiz qanday?\n"
            "<i>(Pastdagi tugmalardan 1-bosishda tanlang)</i>"
        ),
        "default_items": ["Python", "Bash", "SQL"]
    },
    {
        "id": "cybersecurity_knowledge",
        "title": "🛡 5/14: Cybersecurity bilimlari",
        "name": "Cybersecurity bilimlari",
        "type": "skill_level",
        "prompt": (
            "🛡 <b>5/14: Cybersecurity (Kiberxavfsizlik) darajangiz</b>\n\n"
            "Kiberxavfsizlik nazariy va amaliy bilimlari bo'yicha darajangiz qanday?\n"
            "<i>(SOC, Incident Response, Network Security, Pentesting va h.k.)</i>"
        ),
        "default_items": ["SOC", "Incident Response", "Network Security"]
    },
    {
        "id": "linux",
        "title": "🐧 6/14: Linux operatsion tizimi",
        "name": "Linux",
        "type": "skill_level",
        "prompt": (
            "🐧 <b>6/14: Linux bo'yicha bilim darajangiz</b>\n\n"
            "Terminal, buyruqlar, tizim boshqaruvi va distributivlar bo'yicha darajangiz?\n"
            "<i>(Ubuntu, Kali Linux, Debian, Bash)</i>"
        ),
        "default_items": ["Ubuntu", "Kali Linux", "Bash"]
    },
    {
        "id": "networking",
        "title": "🌐 7/14: Networking (Tarmoq bilimlari)",
        "name": "Networking",
        "type": "skill_level",
        "prompt": (
            "🌐 <b>7/14: Kompyuter tarmoqlari (Networking)</b>\n\n"
            "TCP/IP, OSI, Subnetting, Wireshark, DNS, DHCP, Marshrutlash bo'yicha darajangiz?"
        ),
        "default_items": ["TCP/IP", "Wireshark", "OSI Model"]
    },
    {
        "id": "siem",
        "title": "📊 8/14: SIEM tizimlari",
        "name": "SIEM",
        "type": "skill_level",
        "prompt": (
            "📊 <b>8/14: SIEM tizimlari bilan ishlash</b>\n\n"
            "Log tahlili, monitoring va qoidalar yozish bo'yicha darajangiz?\n"
            "<i>(Splunk, Wazuh, ELK Stack, Microsoft Sentinel)</i>"
        ),
        "default_items": ["Wazuh", "Splunk"]
    },
    {
        "id": "python",
        "title": "🐍 9/14: Python tili",
        "name": "Python",
        "type": "skill_level",
        "prompt": (
            "🐍 <b>9/14: Python dasturlash tili</b>\n\n"
            "Python'da kod yozish, skriptlar, avtomatlashtirish va botlar yaratish darajangiz?"
        ),
        "default_items": ["Automation", "Telethon", "OOP", "Requests"]
    },
    {
        "id": "git_github",
        "title": "🐙 10/14: Git va GitHub",
        "name": "Git/GitHub",
        "type": "skill_level",
        "prompt": (
            "🐙 <b>10/14: Git & GitHub versiya boshqaruvi</b>\n\n"
            "Buyruqlar, commit, branch, pull request va GitHub'da loyiha yuritish darajangiz?"
        ),
        "default_items": ["Git CLI", "GitHub workflows", "Version control"]
    },
    {
        "id": "english",
        "title": "🇬🇧 11/14: Ingliz tili",
        "name": "Ingliz tili",
        "type": "skill_level",
        "prompt": (
            "🇬🇧 <b>11/14: Ingliz tili darajangiz</b>\n\n"
            "Texnik hujjatlarni o'qish, video darslarni tushunish va muloqot darajangiz?"
        ),
        "default_items": ["Texnik hujjatlarni o'qish", "B1-B2"]
    },
    {
        "id": "russian",
        "title": "🇷🇺 12/14: Rus tili",
        "name": "Rus tili",
        "type": "skill_level",
        "prompt": (
            "🇷🇺 <b>12/14: Rus tili darajangiz</b>\n\n"
            "Texnik adabiyotlarni o'qish va muloqot qilish darajangiz?"
        ),
        "default_items": ["So'zlashuv", "B1"]
    },
    {
        "id": "experience",
        "title": "💼 13/14: Umumiy amaliy tajriba",
        "name": "Tajriba",
        "type": "skill_level",
        "prompt": (
            "💼 <b>13/14: Sohadagi amaliy ish tajribangiz</b>\n\n"
            "Qaysi toifadagi tajribaga egasiz?\n"
            "• 🟢 Beginner: 0–1 yil (Stajyor, amaliyotchi, mustaqil lablar)\n"
            "• 🟡 Intermediate: 1–3 yil (Junior / Mid mutaxassis)\n"
            "• 🔴 Advanced: 3+ yil (Katta mutaxassis)"
        ),
        "default_items": ["Junior / 0-1 yil"]
    },
    {
        "id": "portfolio_projects",
        "title": "🚀 14/14: Portfolio va GitHub loyihalari",
        "name": "Portfolio/GitHub loyihalari",
        "type": "text_or_pick",
        "prompt": (
            "🚀 <b>14/14: Portfolio yoki GitHub loyihalaringiz</b>\n\n"
            "GitHub profilingiz havolasini yoki bajargan loyihalaringiz nomini yozing:\n"
            "<i>(Masalan: https://github.com/orifxon05 yoki 'Telegram AI Bot, SOC Lab')</i>"
        ),
        "options": ["https://github.com/orifxon05", "Telegram AI Assistant", "SOC Monitoring Lab", "Hozircha tayyorlanmoqda"]
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# STANDART BOSHLANG'ICH PROFIL
# ─────────────────────────────────────────────────────────────────────────────

def get_default_skills_profile():
    """Standart boshlang'ich ko'nikmalar profili."""
    return {
        "university": "Toshkent Axborot Texnologiyalari Universiteti (TATU)",
        "courses": ["Coursera (Google Cybersecurity)", "Najot Ta'lim", "Mustaqil ta'lim"],
        "certifications": ["CompTIA Security+ (tayyorgarlik)"],
        "programming_languages": {
            "name": "Dasturlash tillari",
            "level": "Intermediate",
            "items": ["Python", "Bash", "SQL"]
        },
        "cybersecurity_knowledge": {
            "name": "Cybersecurity bilimlari",
            "level": "Intermediate",
            "items": ["SOC", "Incident Response", "Network Security"]
        },
        "linux": {
            "name": "Linux",
            "level": "Intermediate",
            "items": ["Ubuntu", "Kali Linux", "Bash"]
        },
        "networking": {
            "name": "Networking",
            "level": "Intermediate",
            "items": ["TCP/IP", "Wireshark", "OSI Model"]
        },
        "siem": {
            "name": "SIEM",
            "level": "Beginner",
            "items": ["Wazuh", "Splunk"]
        },
        "python": {
            "name": "Python",
            "level": "Intermediate",
            "items": ["Telethon", "Requests", "Automation"]
        },
        "git_github": {
            "name": "Git/GitHub",
            "level": "Intermediate",
            "items": ["Git commands", "GitHub repos"]
        },
        "english": {
            "name": "Ingliz tili",
            "level": "Intermediate",
            "items": ["Texnik hujjatlarni o'qish (B1-B2)"]
        },
        "russian": {
            "name": "Rus tili",
            "level": "Intermediate",
            "items": ["So'zlashuv (B1)"]
        },
        "experience": {
            "name": "Tajriba",
            "level": "Beginner",
            "items": ["Junior / 0-1 yil amaliyot"]
        },
        "portfolio_projects": [
            "Telegram AI Assistant (Jarvis)",
            "https://github.com/orifxon05"
        ],
        "metadata": {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_configured": True
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# JSON FAYL BILAN ISHLASH (skills_profile.json)
# ─────────────────────────────────────────────────────────────────────────────

def load_skills_profile():
    """skills_profile.json faylini o'qiydi. Fayl yo'q bo'lsa standart shablonni qaytaradi."""
    if not os.path.exists(SKILLS_FILE):
        data = get_default_skills_profile()
        save_skills_profile(data)
        return data
    try:
        with open(SKILLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            defaults = get_default_skills_profile()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"[SKILLS] Faylni o'qishda xatolik: {e}")
        return get_default_skills_profile()

def save_skills_profile(data):
    """skills_profile.json fayliga yozadi."""
    try:
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["updated_at"] = datetime.now().isoformat()
        with open(SKILLS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SKILLS] Saqlashda xatolik: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# INTERAKTIV RO'YXATGA OLISH SESSIYALARI (WIZARD)
# ─────────────────────────────────────────────────────────────────────────────

SKILLS_SESSIONS = {}

def is_in_skills_setup(chat_id):
    """Foydalanuvchi ko'nikmalar so'rovnomasidami?"""
    return chat_id in SKILLS_SESSIONS

def cancel_skills_setup(chat_id):
    """Ko'nikmalar so'rovnomasini bekor qilish."""
    if chat_id in SKILLS_SESSIONS:
        del SKILLS_SESSIONS[chat_id]
        return True
    return False

def start_skills_wizard(chat_id):
    """Ko'nikmalar profilini to'ldirishni 1-bosqichdan boshlaydi."""
    SKILLS_SESSIONS[chat_id] = {
        "step_index": 0,
        "data": load_skills_profile()
    }
    return get_skills_step_prompt(chat_id)

def get_skills_step_prompt(chat_id):
    """Joriy bosqich savoli va inline tugmalarini chiqaradi."""
    session = SKILLS_SESSIONS.get(chat_id)
    if not session:
        return "Sessiya topilmadi.", None

    step_idx = session.get("step_index", 0)
    if step_idx >= len(SKILL_STEPS):
        return finalize_skills_wizard(chat_id)

    cfg = SKILL_STEPS[step_idx]
    field_id = cfg["id"]
    field_type = cfg["type"]

    # Agar bu daraja (level) talab qiladigan skill bo'lsa:
    if field_type == "skill_level":
        cur_obj = session["data"].get(field_id, {})
        cur_level = cur_obj.get("level", "Belgilanmagan") if isinstance(cur_obj, dict) else "Belgilanmagan"
        cur_badge = LEVEL_BADGES.get(cur_level, cur_level)

        text = (
            f"{cfg['prompt']}\n\n"
            f"📌 <b>Hozirgi daraja:</b> {cur_badge}\n\n"
            "💡 <i>Kerakli darajani tanlash uchun quyidagi tugmalardan birini bosing:</i>"
        )
        keyboard = [
            [
                {"text": "🟢 Beginner (Boshlovchi)", "callback_data": f"sk_wz_lvl_{field_id}_Beginner"}
            ],
            [
                {"text": "🟡 Intermediate (O'rta)", "callback_data": f"sk_wz_lvl_{field_id}_Intermediate"}
            ],
            [
                {"text": "🔴 Advanced (Yuqori)", "callback_data": f"sk_wz_lvl_{field_id}_Advanced"}
            ],
            [
                {"text": "⏩ O'tkazish", "callback_data": "sk_wz_skip"},
                {"text": "❌ Bekor qilish", "callback_data": "sk_cancel"}
            ]
        ]
        return text, {"inline_keyboard": keyboard}

    # Agar bu oddiy matn / variantli bo'lim bo'lsa (Universitet, Kurslar, Sertifikatlar, Portfolio):
    options = cfg.get("options", [])
    text = (
        f"{cfg['prompt']}\n\n"
        "💡 <i>Tugmalardan birini bosing yoki o'zingiz matn ko'rinishida yozing:</i>"
    )
    keyboard = []
    # Tugmalarni 2 tadan qilib joylash
    row = []
    for opt in options:
        # callback_data uzunligi chegarasi: 64 bayt
        short_opt = opt[:25]
        row.append({"text": opt, "callback_data": f"sk_wz_opt_{field_id}_{short_opt}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        {"text": "⏩ O'tkazish", "callback_data": "sk_wz_skip"},
        {"text": "❌ Bekor qilish", "callback_data": "sk_cancel"}
    ])
    return text, {"inline_keyboard": keyboard}

def process_skills_input(chat_id, user_text):
    """Foydalanuvchi yozma matn yuborganda uni qabul qilish."""
    session = SKILLS_SESSIONS.get(chat_id)
    if not session:
        return None, None

    step_idx = session.get("step_index", 0)
    if step_idx >= len(SKILL_STEPS):
        return finalize_skills_wizard(chat_id)

    cfg = SKILL_STEPS[step_idx]
    field_id = cfg["id"]
    text_clean = user_text.strip()

    is_skip = text_clean.lower() in ["skip", "o'tkazish", "otkazish", "/skip", "keyingisi", "next"]

    if not is_skip and text_clean:
        if cfg["type"] == "skill_level":
            # Matndan levelni qidirish
            detected_level = None
            t_low = text_clean.lower()
            if any(w in t_low for w in ["advanced", "yuqori", "katta", "senior", "c1", "c2", "3 yil"]):
                detected_level = "Advanced"
            elif any(w in t_low for w in ["intermediate", "o'rta", "orta", "middle", "b1", "b2", "1-2 yil"]):
                detected_level = "Intermediate"
            elif any(w in t_low for w in ["beginner", "boshlovchi", "boshlang'ich", "junior", "trainee", "a1", "a2", "0-1 yil"]):
                detected_level = "Beginner"
            else:
                detected_level = "Intermediate"

            cur = session["data"].get(field_id, {})
            if not isinstance(cur, dict):
                cur = {"name": cfg["name"], "items": []}
            cur["level"] = detected_level
            # Agar qo'shimcha so'zlar yozilgan bo'lsa
            words = [w.strip() for w in text_clean.split(",") if w.strip()]
            if len(words) > 1:
                cur["items"] = words
            session["data"][field_id] = cur
        else:
            # Matnli maydon (Universitet, Kurslar, Portfolio)
            if field_id in ["courses", "certifications", "portfolio_projects"]:
                parts = [p.strip() for p in text_clean.split(",") if p.strip()]
                session["data"][field_id] = parts
            else:
                session["data"][field_id] = text_clean

    session["step_index"] = step_idx + 1
    if session["step_index"] >= len(SKILL_STEPS):
        return finalize_skills_wizard(chat_id)
    return get_skills_step_prompt(chat_id)

def finalize_skills_wizard(chat_id):
    """Barcha 14 bosqich yakunlanganda saqlash va hisobot berish."""
    session = SKILLS_SESSIONS.pop(chat_id, None)
    if not session:
        return "Sessiya topilmadi.", None

    prof = session.get("data", {})
    prof["metadata"]["is_configured"] = True
    save_skills_profile(prof)

    text = (
        "🎉 <b>Skills Profile muvaffaqiyatli saqlandi!</b>\n"
        "Barcha ko'nikmalar va darajalar <code>skills_profile.json</code> fayliga yozildi.\n\n"
        f"{format_skills_view(prof)}"
    )
    return text, build_skills_action_keyboard()

# ─────────────────────────────────────────────────────────────────────────────
# BIR BOSHDA DARAJA O'ZGARTIRGICH (QUICK LEVEL CYCLER)
# ─────────────────────────────────────────────────────────────────────────────

RATED_SKILL_KEYS = [
    ("programming_languages", "💻 Tillar"),
    ("cybersecurity_knowledge", "🛡 Cyber"),
    ("linux", "🐧 Linux"),
    ("networking", "🌐 Network"),
    ("siem", "📊 SIEM"),
    ("python", "🐍 Python"),
    ("git_github", "🐙 Git"),
    ("english", "🇬🇧 English"),
    ("russian", "🇷🇺 Russian"),
    ("experience", "💼 Tajriba")
]

def build_quick_levels_keyboard(prof):
    """
    Har bir skillning joriy darajasi bilan inline tugmalar paneli.
    Tugmani 1 marta bosish orqali darajani Beginner -> Intermediate -> Advanced aylantirish mumkin!
    """
    keyboard = []
    row = []
    level_icons = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}

    for key, label in RATED_SKILL_KEYS:
        obj = prof.get(key, {})
        lvl = obj.get("level", "Intermediate") if isinstance(obj, dict) else "Intermediate"
        icon = level_icons.get(lvl, "⚪")
        btn_text = f"{label}: {icon} {lvl[:3]}"
        row.append({"text": btn_text, "callback_data": f"sk_cyc_{key}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        {"text": "📋 Profilni to'liq ko'rish", "callback_data": "sk_view"},
        {"text": "⬅️ Asosiy menyu", "callback_data": "open_menu"}
    ])
    return {"inline_keyboard": keyboard}

def cycle_skill_level(skill_key):
    """Skill darajasini Beginner -> Intermediate -> Advanced -> Beginner qilib aylantiradi."""
    prof = load_skills_profile()
    obj = prof.get(skill_key, {})
    if not isinstance(obj, dict):
        obj = {"name": skill_key, "items": []}

    cur_level = obj.get("level", "Beginner")
    if cur_level == "Beginner":
        new_level = "Intermediate"
    elif cur_level == "Intermediate":
        new_level = "Advanced"
    else:
        new_level = "Beginner"

    obj["level"] = new_level
    prof[skill_key] = obj
    save_skills_profile(prof)
    return new_level, prof

# ─────────────────────────────────────────────────────────────────────────────
# TAYYOR SHABLONLAR (PRESETS)
# ─────────────────────────────────────────────────────────────────────────────

def apply_preset(preset_type):
    """Foydalanuvchi tanlagan tayyor shablonni o'rnatish."""
    prof = load_skills_profile()

    if preset_type == "soc_analyst":
        prof["university"] = "TATU (Axborot xavfsizligi)"
        prof["courses"] = ["Coursera (Google Cybersecurity)", "Najot Ta'lim"]
        prof["certifications"] = ["CompTIA Security+"]
        prof["programming_languages"]["level"] = "Intermediate"
        prof["cybersecurity_knowledge"]["level"] = "Intermediate"
        prof["linux"]["level"] = "Intermediate"
        prof["networking"]["level"] = "Intermediate"
        prof["siem"]["level"] = "Intermediate"
        prof["python"]["level"] = "Intermediate"
        prof["git_github"]["level"] = "Intermediate"
        prof["english"]["level"] = "Intermediate"
        prof["russian"]["level"] = "Intermediate"
        prof["experience"]["level"] = "Beginner"
        prof["experience"]["items"] = ["Junior SOC Analyst / 0-1 yil"]
    elif preset_type == "python_dev":
        prof["programming_languages"]["level"] = "Advanced"
        prof["python"]["level"] = "Advanced"
        prof["git_github"]["level"] = "Advanced"
        prof["linux"]["level"] = "Intermediate"
        prof["networking"]["level"] = "Intermediate"
        prof["cybersecurity_knowledge"]["level"] = "Beginner"
        prof["siem"]["level"] = "Beginner"
        prof["experience"]["level"] = "Intermediate"
    elif preset_type == "all_advanced":
        for k, _ in RATED_SKILL_KEYS:
            if isinstance(prof.get(k), dict):
                prof[k]["level"] = "Advanced"

    save_skills_profile(prof)
    return prof

# ─────────────────────────────────────────────────────────────────────────────
# KO'RINISh VA FORMATLASH (VIEW FORMATTER)
# ─────────────────────────────────────────────────────────────────────────────

def format_list_items(val):
    if isinstance(val, list):
        return ", ".join([str(x) for x in val if str(x).strip()]) if val else "<i>(Belgilanmagan)</i>"
    elif isinstance(val, str):
        return val if val.strip() else "<i>(Belgilanmagan)</i>"
    return "<i>(Belgilanmagan)</i>"

def format_skills_view(profile=None):
    """Foydalanuvchining ko'nikmalar profilini to'liq chiroyli ko'rsatish."""
    prof = profile or load_skills_profile()

    univ = prof.get("university", "Belgilanmagan")
    courses = format_list_items(prof.get("courses"))
    certs = format_list_items(prof.get("certifications"))
    portf = format_list_items(prof.get("portfolio_projects"))

    def render_skill_line(icon, title, key):
        obj = prof.get(key, {})
        lvl = obj.get("level", "Beginner") if isinstance(obj, dict) else "Beginner"
        badge = LEVEL_BADGES.get(lvl, lvl)
        meter = LEVEL_METERS.get(lvl, "")
        items = obj.get("items", []) if isinstance(obj, dict) else []
        items_str = f" ({', '.join(items)})" if items else ""
        return f"{icon} <b>{title}:</b> [{badge}]\n   <code>{meter}</code>{items_str}"

    text = (
        "🛠 <b>JARVIS SKILLS PROFILE (KO'NIKMALAR)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎓 <b>TA'LIM VA SERTIFIKATLAR:</b>\n"
        f"• 🏛 <b>Universitet:</b> {univ}\n"
        f"• 📚 <b>Kurslar:</b> {courses}\n"
        f"• 📜 <b>Sertifikatlar:</b> {certs}\n\n"
        "⚡ <b>TEXNIK KO'NIKMALAR & DARAJALAR:</b>\n"
        f"{render_skill_line('🐍', 'Python', 'python')}\n"
        f"{render_skill_line('🐧', 'Linux', 'linux')}\n"
        f"{render_skill_line('🌐', 'Networking', 'networking')}\n"
        f"{render_skill_line('🛡', 'Cybersecurity', 'cybersecurity_knowledge')}\n"
        f"{render_skill_line('📊', 'SIEM tizimlari', 'siem')}\n"
        f"{render_skill_line('🐙', 'Git & GitHub', 'git_github')}\n"
        f"{render_skill_line('💻', 'Dasturlash tillari', 'programming_languages')}\n\n"
        "🗣 <b>TIL BILISH DARAJALARI:</b>\n"
        f"{render_skill_line('🇬🇧', 'Ingliz tili', 'english')}\n"
        f"{render_skill_line('🇷🇺', 'Rus tili', 'russian')}\n\n"
        "💼 <b>TAJRIBA VA PORTFOLIO:</b>\n"
        f"{render_skill_line('⏳', 'Ish tajribasi', 'experience')}\n"
        f"• 🚀 <b>Portfolio/Loyihalar:</b> {portf}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Darajalarni tezkor o'zgartirish uchun pastdagi tugmani bosing:</i>"
    )
    return text

def build_skills_action_keyboard():
    """Asosiy ko'nikmalar ko'rinishi tugmalari."""
    return {
        "inline_keyboard": [
            [
                {"text": "⚡ Darajalarni tezkor sozlash", "callback_data": "sk_quick_levels"}
            ],
            [
                {"text": "✏️ Bosqichma-bosqich to'ldirish", "callback_data": "sk_start_wizard"},
                {"text": "🚀 SOC Shablonini yuklash", "callback_data": "sk_preset_soc"}
            ],
            [
                {"text": "📋 Shaxsiy profilim", "callback_data": "pt_view_profile"},
                {"text": "⬅️ Asosiy menyu", "callback_data": "open_menu"}
            ]
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER (sk_ PREFIKSI BILAN)
# ─────────────────────────────────────────────────────────────────────────────

def handle_skills_callback(chat_id, data):
    """Inline tugmalardan kelgan sk_ bilan boshlanuvchi amallarni bajarish."""
    # ─── KO'RSATISH ───
    if data == "sk_view":
        prof = load_skills_profile()
        return format_skills_view(prof), build_skills_action_keyboard()

    # ─── BEKOR QILISH ───
    if data == "sk_cancel":
        cancel_skills_setup(chat_id)
        return "❌ Ko'nikmalar so'rovnomasi bekor qilindi.", {"inline_keyboard": [[{"text": "🛠 Skills ko'rsatish", "callback_data": "sk_view"}]]}

    # ─── WIZARDNI BOSHLASH ───
    if data == "sk_start_wizard":
        return start_skills_wizard(chat_id)

    # ─── WIZARD: DARAJA TANLANGANDA (1-BOSISHDA KEYINGISIGA O'TADI) ───
    if data.startswith("sk_wz_lvl_"):
        parts = data.replace("sk_wz_lvl_", "").split("_")
        if len(parts) >= 2:
            field_id = parts[0]
            level = parts[1]
            session = SKILLS_SESSIONS.get(chat_id)
            if session:
                cur = session["data"].get(field_id, {})
                if not isinstance(cur, dict):
                    cur = {"name": field_id, "items": []}
                cur["level"] = level
                session["data"][field_id] = cur
                session["step_index"] += 1
                if session["step_index"] >= len(SKILL_STEPS):
                    return finalize_skills_wizard(chat_id)
                return get_skills_step_prompt(chat_id)

    # ─── WIZARD: VARIANT TANLANGANDA ───
    if data.startswith("sk_wz_opt_"):
        raw_part = data.replace("sk_wz_opt_", "")
        parts = raw_part.split("_", 1)
        if len(parts) == 2:
            field_id, val = parts[0], parts[1]
            session = SKILLS_SESSIONS.get(chat_id)
            if session:
                if field_id in ["courses", "certifications", "portfolio_projects"]:
                    cur_list = session["data"].get(field_id, [])
                    if not isinstance(cur_list, list):
                        cur_list = []
                    if val not in cur_list:
                        cur_list.append(val)
                    session["data"][field_id] = cur_list
                else:
                    session["data"][field_id] = val
                session["step_index"] += 1
                if session["step_index"] >= len(SKILL_STEPS):
                    return finalize_skills_wizard(chat_id)
                return get_skills_step_prompt(chat_id)

    # ─── WIZARD: O'TKAZISH ───
    if data == "sk_wz_skip":
        session = SKILLS_SESSIONS.get(chat_id)
        if session:
            session["step_index"] += 1
            if session["step_index"] >= len(SKILL_STEPS):
                return finalize_skills_wizard(chat_id)
            return get_skills_step_prompt(chat_id)

    # ─── DARAJALARNI TEZKOR SOZLASH (QUICK LEVEL CYCLER) ───
    if data == "sk_quick_levels":
        prof = load_skills_profile()
        text = (
            "⚡ <b>Tezkor Daraja O'zgartirgich</b>\n\n"
            "Har bir tugmani bossangiz, daraja avtomatik tarzda almashadi:\n"
            "🟢 Beginner ➡️ 🟡 Intermediate ➡️ 🔴 Advanced\n\n"
            "<i>(O'zgartirmoqchi bo'lgan ko'nikmangiz ustiga bosing):</i>"
        )
        return text, build_quick_levels_keyboard(prof)

    # ─── DARAJANI 1-KLIKDA AYLANTIRISH (CYCLE) ───
    if data.startswith("sk_cyc_"):
        skill_key = data.replace("sk_cyc_", "")
        new_lvl, prof = cycle_skill_level(skill_key)
        badge = LEVEL_BADGES.get(new_lvl, new_lvl)
        text = (
            f"✅ <b>{skill_key.capitalize()}</b> darajasi yangilandi: {badge}\n\n"
            "Yana o'zgartirish uchun tugmalarni bosing:"
        )
        return text, build_quick_levels_keyboard(prof)

    # ─── PRESETS ───
    if data == "sk_preset_soc":
        prof = apply_preset("soc_analyst")
        text = (
            "🚀 <b>SOC Analyst Junior shabloni muvaffaqiyatli yuklandi!</b>\n"
            "Kiberxavfsizlik, SIEM, Linux, Tarmoq va Python ko'nikmalari optimal holatga keltirildi.\n\n"
            f"{format_skills_view(prof)}"
        )
        return text, build_skills_action_keyboard()

    return None, None
