# -*- coding: utf-8 -*-
"""
personal_profile.py - Jarvis Personal Profile & Interest Test Module

Modul vazifalari:
1. Foydalanuvchining shaxsiy va professional qiziqishlarini 9 ta bosqichda aniqlash:
   - 1. Kasbiy qiziqishlar (Cybersecurity, Python, AI, Backend, ...)
   - 2. Ish turi (Internship, Junior, Remote, Full-time, ...)
   - 3. Kiberxavfsizlik ichidagi qiziqishlar (SOC, SIEM, Incident Response, Pentest, ...)
   - 4. Texnologiyalar (Python, Linux, Docker, SQL, ...)
   - 5. Ta'lim va rivojlanish (Kurs, Grant, Bootcamp, Certification, ...)
   - 6. Ishlashni xohlagan sohalar (Bank, Fintech, IT, Telecom, Startup, ...)
   - 7. Joylashuv (Tashkent, Remote, Hybrid, ...)
   - 8. Maosh (Min, Ideal, Unpaid internship munosabati)
   - 9. Karyera maqsadi (Keyingi 6-12 oy)
2. Har bir qiziqishga HIGH / MEDIUM / LOW ustuvorlik (priority) darajasini biriktirish.
3. Barcha ma'lumotlarni alohida `personal_profile.json` faylida saqlash.
4. "skip" orqali har qanday savolni o'tkazib yuborish imkoniyati.
5. "Profilimni ko'rsat", "Profilimni o'zgartirish", "Qiziqishimni qo'sh", "Qiziqishimni olib tashla" amallari.
6. Kelgusida "Time & Schedule" modulini oson va to'siqsiz ulash uchun moslashuvchan arxitektura.
"""

import os
import re
import json
from datetime import datetime

PERSONAL_PROFILE_FILE = "personal_profile.json"

# Ustuvorlik (Priority) darajalari va emojilari
PRIORITY_BADGES = {
    "HIGH": "🔴 HIGH",
    "MEDIUM": "🟡 MEDIUM",
    "LOW": "⚪ LOW"
}

# 9 ta bosqich ta'riflari
STEPS_CONFIG = [
    {
        "step": 1,
        "key": "professional_interests",
        "title": "🎯 1/9: Kasbiy qiziqishlar",
        "prompt": (
            "🎯 <b>1/9-savol: Kasbiy qiziqishlaringiz</b>\n\n"
            "Qaysi asosiy soha va yo'nalishlarga qiziqasiz?\n"
            "<i>(Masalan: Cybersecurity, SOC, Antifraud, SIEM, Network Security, Python, Backend, AI...)</i>\n\n"
            "💡 <b>Qanday javob berish mumkin:</b>\n"
            "• Qiziqishlarni ustuvorligi bilan yozing:\n"
            "  <code>Cybersecurity HIGH, Python HIGH, AI MEDIUM</code>\n"
            "• Yoki oddiygina vergul bilan yozing (standart HIGH bo'ladi):\n"
            "  <code>Cybersecurity, Python, SOC</code>\n"
            "• Yoki quyidagi tugmalardan birini bosing.\n"
            "• O'tkazib yuborish uchun <b>skip</b> deb yozing."
        ),
        "options": ["Cybersecurity", "SOC", "Antifraud", "SIEM", "Network Security", "Python", "Backend", "AI"]
    },
    {
        "step": 2,
        "key": "job_types",
        "title": "💼 2/9: Ish va bandlik turi",
        "prompt": (
            "💼 <b>2/9-savol: Ish va bandlik turi</b>\n\n"
            "Sizga qanday ish shakllari ma'qul?\n"
            "<i>(Masalan: Internship, Junior, Trainee, Apprentice, Full-time, Part-time, Remote, Hybrid, On-site...)</i>\n\n"
            "💡 Yozing (masalan: <code>Internship HIGH, Remote HIGH, Full-time MEDIUM</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["Internship", "Junior", "Trainee", "Apprentice", "Full-time", "Part-time", "Remote", "Hybrid", "On-site"]
    },
    {
        "step": 3,
        "key": "cybersecurity_interests",
        "title": "🛡 3/9: Kiberxavfsizlik yo'nalishlari",
        "prompt": (
            "🛡 <b>3/9-savol: Kiberxavfsizlik (Cybersecurity) ichidagi qiziqishlar</b>\n\n"
            "Cybersecurity ichida aynan qaysi tarmoqlarga ko'proq qiziqasiz?\n"
            "<i>(Masalan: SOC, Incident Response, SIEM, EDR/XDR, DLP, UEBA, Pentest, Cloud Security...)</i>\n\n"
            "💡 Yozing (masalan: <code>SOC HIGH, Incident Response HIGH, SIEM MEDIUM</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["SOC", "Incident Response", "SIEM", "EDR/XDR", "DLP", "UEBA", "Pentest", "Cloud Security"]
    },
    {
        "step": 4,
        "key": "technologies",
        "title": "💻 4/9: Texnologiyalar",
        "prompt": (
            "💻 <b>4/9-savol: Texnologiyalar va vositalar</b>\n\n"
            "Qaysi texnologiyalar, dasturlash tillari yoki vositalar bo'yicha ishlashni yoki o'rganishni xohlaysiz?\n"
            "<i>(Masalan: Python, Linux, Git, SQL, Docker, Cloud, Splunk, Wireshark...)</i>\n\n"
            "💡 Yozing (masalan: <code>Python HIGH, Linux HIGH, Docker MEDIUM</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["Python", "Linux", "Git", "SQL", "Docker", "Cloud", "Splunk", "Wireshark"]
    },
    {
        "step": 5,
        "key": "education_interests",
        "title": "🎓 5/9: Ta'lim va imkoniyatlar",
        "prompt": (
            "🎓 <b>5/9-savol: Ta'lim va rivojlanish imkoniyatlari</b>\n\n"
            "Qanday ta'lim dasturlariga qiziqasiz?\n"
            "<i>(Masalan: Kurs, Grant, Scholarship, Bootcamp, Hackathon, Certification, Internship...)</i>\n\n"
            "💡 Yozing (masalan: <code>Grant HIGH, Bootcamp MEDIUM, Certification HIGH</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["Kurs", "Grant", "Scholarship", "Bootcamp", "Hackathon", "Certification", "Internship"]
    },
    {
        "step": 6,
        "key": "target_industries",
        "title": "🏢 6/9: Ishlashni xohlagan sohalar",
        "prompt": (
            "🏢 <b>6/9-savol: Kompaniya va biznes sohalari</b>\n\n"
            "Qaysi yo'nalishdagi kompaniyalarda ishlashni afzal ko'rasiz?\n"
            "<i>(Masalan: Bank, Fintech, IT, Telecom, Startup, Government/Davlat...)</i>\n\n"
            "💡 Yozing (masalan: <code>Fintech HIGH, Bank HIGH, Startup MEDIUM</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["Bank", "Fintech", "IT", "Telecom", "Startup", "Government"]
    },
    {
        "step": 7,
        "key": "locations",
        "title": "🌍 7/9: Joylashuv",
        "prompt": (
            "🌍 <b>7/9-savol: Joylashuv va lokatsiya</b>\n\n"
            "Qaysi hudud yoki shaklda ishlash sizga qulay?\n"
            "<i>(Masalan: Tashkent, Boshqa shahar, Remote, Hybrid, Xorij...)</i>\n\n"
            "💡 Yozing (masalan: <code>Tashkent HIGH, Remote HIGH</code>) "
            "yoki tugmalardan tanlang (o'tkazish uchun <b>skip</b>)."
        ),
        "options": ["Tashkent", "Boshqa shahar", "Remote", "Hybrid", "Global/Xorij"]
    },
    {
        "step": 8,
        "key": "salary",
        "title": "💰 8/9: Maosh kutilmalari",
        "prompt": (
            "💰 <b>8/9-savol: Maosh kutilmalari va amaliyot</b>\n\n"
            "Minimal va ideal maoshingiz qancha? To'lovsiz amaliyotga (unpaid internship) rozimisiz?\n"
            "<i>(Masalan: <code>Min: $300, Ideal: $800, Unpaid: Ha</code>)</i>\n\n"
            "💡 Matn ko'rinishida yozing, tugmalardan birini bosing yoki <b>skip</b> deb o'tkazib yuboring."
        ),
        "options": [
            "Min: $300, Ideal: $700, Unpaid: Ha",
            "Min: $500, Ideal: $1200, Unpaid: Yo'q",
            "Min: $1000+, Unpaid: Yo'q",
            "Faqat tajriba (Unpaid: Ha)"
        ]
    },
    {
        "step": 9,
        "key": "career_goal",
        "title": "🚀 9/9: Karyera maqsadi",
        "prompt": (
            "🚀 <b>9/9-savol: Karyera maqsadi (Keyingi 6–12 oy)</b>\n\n"
            "Keyingi 6–12 oy ichida aynan qanday marraga erishmoqchisiz?\n"
            "<i>(Masalan: SOC L1 mutaxassisi bo'lish, Xalqaro sertifikat olish, Junior Backend dasturchi bo'lib ishga kirish...)</i>\n\n"
            "💡 Maqsadingizni erkin matn shaklida yozing yoki quyidagi variantlardan birini bosing (o'tkazish uchun <b>skip</b>)."
        ),
        "options": [
            "SOC L1 analitik mutaxassisi bo'lib ishga kirish",
            "Junior Python Backend dasturchi bo'lish",
            "Xalqaro kiberxavfsizlik sertifikatini qo'lga kiritish"
        ]
    }
]

# Faol test sessiyalari: {chat_id: {"step": 1, "data": {}, "temp_items": []}}
TEST_SESSIONS = {}

# ─────────────────────────────────────────────────────────────────────────────
# JSON BAZA BILAN ISHLASH (personal_profile.json)
# ─────────────────────────────────────────────────────────────────────────────

def get_default_profile_schema():
    """Bo'sh profil andozasi."""
    return {
        "professional_interests": [],
        "job_types": [],
        "cybersecurity_interests": [],
        "technologies": [],
        "education_interests": [],
        "target_industries": [],
        "locations": [],
        "salary": {
            "min_salary": None,
            "ideal_salary": None,
            "unpaid_internship": None,
            "raw_text": "",
            "priority": "HIGH"
        },
        "career_goal": {
            "goal": None,
            "priority": "HIGH"
        },
        # Kelgusida "Time & Schedule" modulini to'g'ridan-to'g'ri ulash uchun tayyor blok:
        "schedule": {
            "preferred_work_hours": None,
            "study_hours_daily": None,
            "available_days": [],
            "daily_check_times": [],
            "timezone": "Asia/Tashkent"
        },
        "metadata": {
            "version": "1.0",
            "test_completed": False,
            "created_at": None,
            "updated_at": None
        }
    }

def load_personal_profile():
    """personal_profile.json faylidan o'qiydi yoki standart andoza qaytaradi."""
    if not os.path.exists(PERSONAL_PROFILE_FILE):
        profile = get_default_profile_schema()
        save_personal_profile(profile)
        return profile
    try:
        with open(PERSONAL_PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Schema to'liqligini kafolatlash
            default = get_default_profile_schema()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"[PERSONAL_PROFILE] O'qishda xatolik: {e}")
        return get_default_profile_schema()

def save_personal_profile(profile_data):
    """personal_profile.json fayliga saqlaydi."""
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "metadata" not in profile_data:
            profile_data["metadata"] = {}
        if not profile_data["metadata"].get("created_at"):
            profile_data["metadata"]["created_at"] = now_str
        profile_data["metadata"]["updated_at"] = now_str

        with open(PERSONAL_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[PERSONAL_PROFILE] Saqlashda xatolik: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MATNLARDAN QIZIQISHLAR VA USTUVORLIKNI AJRATISH (PARSER)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_apostrophes(text):
    """O'zbek tilidagi barcha turdagi tutruq va qo'shtirnoqlarni tozalaydi/birxillashtiradi."""
    if not text:
        return ""
    t = text
    for ap in ["\u2018", "\u2019", "\u02bb", "\u02bc", "`"]:
        t = t.replace(ap, "'")
    return t

def parse_items_with_priority(raw_text, default_priority="HIGH"):
    """
    Foydalanuvchi kiritgan matndan elementlar va ularning HIGH/MEDIUM/LOW darajasini ajratadi.
    Formatlar:
      - 'Cybersecurity HIGH, Python MEDIUM, SOC LOW'
      - 'Cybersecurity, Python' (standart HIGH)
      - 'Python: high, Linux (medium), Docker - low'
    """
    if not raw_text or not raw_text.strip():
        return []
    items = []
    # Vergul, nuqta-vergul yoki yangi qatordan bo'lish
    parts = [p.strip() for p in re.split(r"[,;\n]+", raw_text) if p.strip()]
    for part in parts:
        clean_part = normalize_apostrophes(part).strip()
        # Ustuvorlik belgisini qidirish (HIGH, MEDIUM, LOW)
        m = re.search(r"[:\s\-(]+(HIGH|MEDIUM|LOW)[\)]?$", clean_part, re.IGNORECASE)
        if m:
            priority = m.group(1).upper()
            name = clean_part[:m.start()].strip(" :()-")
        else:
            priority = default_priority
            name = clean_part.strip()

        if name:
            # Agar oldin kiritilgan bo'lsa yangilaymiz
            existing = next((x for x in items if x["name"].lower() == name.lower()), None)
            if existing:
                existing["priority"] = priority
            else:
                items.append({"name": name, "priority": priority})
    return items

def parse_salary_input(text):
    """Maosh bo'yicha kiritilgan matndan minimal, ideal va unpaid ma'lumotlarini ajratadi."""
    t = normalize_apostrophes(text).strip()
    result = {
        "min_salary": None,
        "ideal_salary": None,
        "unpaid_internship": None,
        "raw_text": t,
        "priority": "HIGH"
    }
    # Min salary
    min_m = re.search(r"(?:min|minimal|kamida|boshlang[']?ich)[:\s]*([$\d\w\s]+?)(?:[,;]|ideal|unpaid|$)", t, re.IGNORECASE)
    if min_m:
        result["min_salary"] = min_m.group(1).strip()
    # Ideal salary
    ideal_m = re.search(r"(?:ideal|maksimal|orzu|kutilayotgan)[:\s]*([$\d\w\s]+?)(?:[,;]|unpaid|min|$)", t, re.IGNORECASE)
    if ideal_m:
        result["ideal_salary"] = ideal_m.group(1).strip()
    # Unpaid internship
    if "unpaid" in t.lower() or "tekin" in t.lower() or "to'lovsiz" in t.lower() or "tolovsiz" in t.lower():
        if any(w in t.lower() for w in ["ha", "roziman", "tayyorman", "yes", "+"]):
            result["unpaid_internship"] = "Ha (tayyorman)"
        elif any(w in t.lower() for w in ["yo'q", "yoq", "rozi emasman", "no", "-"]):
            result["unpaid_internship"] = "Yo'q (faqat pullik)"
        else:
            result["unpaid_internship"] = "Ko'rib chiqiladi"
    else:
        result["unpaid_internship"] = "Ha (tajriba uchun)" if "ha" in t.lower() else None

    return result

# ─────────────────────────────────────────────────────────────────────────────
# 9 BOSQICHLI TEST GENERATORI VA BOSHQARUVI
# ─────────────────────────────────────────────────────────────────────────────

def is_in_interest_test(chat_id):
    """Foydalanuvchi hozir test jarayonidami?"""
    return chat_id in TEST_SESSIONS

def cancel_interest_test(chat_id):
    """Testni bekor qilish."""
    if chat_id in TEST_SESSIONS:
        del TEST_SESSIONS[chat_id]
        return True
    return False

def get_step_config(step_number):
    """Bosqich ma'lumotlarini olish."""
    for cfg in STEPS_CONFIG:
        if cfg["step"] == step_number:
            return cfg
    return None

def build_step_keyboard(step_number, selected_items=None):
    """Har bir bosqich uchun inline tugmalar yasaydi."""
    cfg = get_step_config(step_number)
    if not cfg:
        return None

    selected_names = [it["name"].lower() for it in (selected_items or [])]
    inline_keyboard = []
    row = []

    # Variant tugmalari
    for idx, opt in enumerate(cfg.get("options", [])):
        is_selected = opt.lower() in selected_names
        btn_text = f"✅ {opt}" if is_selected else opt
        row.append({"text": btn_text, "callback_data": f"pt_opt_{step_number}_{idx}"})
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)

    # Pastki boshqaruv tugmalari: [⏩ O'tkazib yuborish (Skip)] va [⏭ Keyingisi]
    nav_row = [
        {"text": "⏩ O'tkazish (Skip)", "callback_data": f"pt_skip_{step_number}"},
        {"text": "⏭ Keyingisi", "callback_data": f"pt_next_{step_number}"}
    ]
    inline_keyboard.append(nav_row)
    inline_keyboard.append([{"text": "❌ Testni to'xtatish", "callback_data": "pt_cancel"}])

    return {"inline_keyboard": inline_keyboard}

def start_interest_test(chat_id):
    """Qiziqish testini 1-bosqichdan boshlaydi."""
    TEST_SESSIONS[chat_id] = {
        "step": 1,
        "data": {},
        "temp_items": []
    }
    cfg = get_step_config(1)
    kb = build_step_keyboard(1, selected_items=[])
    text = (
        "🌟 <b>Personal Profile & Qiziqishlar Testi Boshlandi!</b>\n\n"
        "Ushbu test <b>9 ta qisqa bosqich</b>dan iborat. Har bir qiziqishingizga "
        "<b>🔴 HIGH</b>, <b>🟡 MEDIUM</b> yoki <b>⚪ LOW</b> darajasini berishingiz mumkin.\n\n"
        "Har qanday savolni <b>skip</b> deb yozib o'tkazib yuborishingiz mumkin.\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{cfg['prompt']}"
    )
    return text, kb

def process_test_input(chat_id, user_text):
    """Foydalanuvchi yozma matn yuborganda test qadami sifatida qabul qilish."""
    session = TEST_SESSIONS.get(chat_id)
    if not session:
        return None, None

    step = session["step"]
    cfg = get_step_config(step)
    if not cfg:
        del TEST_SESSIONS[chat_id]
        return None, None

    text_clean = user_text.strip()
    is_skip = text_clean.lower() in ["skip", "o'tkazish", "otkazish", "o‘tkazish", "/skip", "keyingisi", "next"]

    if not is_skip:
        # 8-bosqich: Maosh
        if cfg["key"] == "salary":
            session["data"]["salary"] = parse_salary_input(text_clean)
        # 9-bosqich: Karyera maqsadi
        elif cfg["key"] == "career_goal":
            session["data"]["career_goal"] = {
                "goal": text_clean,
                "priority": "HIGH"
            }
        # 1-7 bosqichlar: Qiziqishlar ro'yxati
        else:
            parsed = parse_items_with_priority(text_clean)
            if not parsed and text_clean:
                parsed = [{"name": text_clean, "priority": "HIGH"}]
            # Oldingi temp_items bilan birlashtirish
            combined = {item["name"].lower(): item for item in session.get("temp_items", [])}
            for p in parsed:
                combined[p["name"].lower()] = p
            session["data"][cfg["key"]] = list(combined.values())
    else:
        # Agar skip qilinsa va temp_items bo'lsa ularni saqlaymiz, bo'lmasa bo'sh
        if session.get("temp_items"):
            session["data"][cfg["key"]] = session["temp_items"]
        elif cfg["key"] not in session["data"]:
            if cfg["key"] == "salary":
                session["data"]["salary"] = {"min_salary": None, "ideal_salary": None, "unpaid_internship": None, "raw_text": "", "priority": "HIGH"}
            elif cfg["key"] == "career_goal":
                session["data"]["career_goal"] = {"goal": None, "priority": "HIGH"}
            else:
                session["data"][cfg["key"]] = []

    # Keyingi bosqichga o'tish
    next_step = step + 1
    session["step"] = next_step
    session["temp_items"] = []

    if next_step <= len(STEPS_CONFIG):
        next_cfg = get_step_config(next_step)
        kb = build_step_keyboard(next_step, selected_items=[])
        return next_cfg["prompt"], kb
    else:
        # Barcha 9 ta bosqich tugadi! Saqlash va yakunlash
        return finalize_test(chat_id)

def finalize_test(chat_id):
    """Test natijalarini personal_profile.json fayliga yozadi va xulosa chiqaradi."""
    session = TEST_SESSIONS.pop(chat_id, None)
    if not session:
        return "Xatolik: sessiya topilmadi.", None

    profile = load_personal_profile()
    for k, v in session.get("data", {}).items():
        profile[k] = v

    profile["metadata"]["test_completed"] = True
    save_personal_profile(profile)

    summary_text = (
        "🎉 <b>Qiziqishlar testi muvaffaqiyatli yakunlandi!</b>\n"
        "Barcha ma'lumotlar <code>personal_profile.json</code> fayliga saqlandi.\n\n"
        f"{format_profile_view(profile)}"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "📋 Profilimni ko'rsat", "callback_data": "pt_view_profile"}],
            [{"text": "✏️ Profilni o'zgartirish", "callback_data": "pt_edit_menu"}],
            [{"text": "📂 Asosiy menyu", "callback_data": "open_menu"}]
        ]
    }
    return summary_text, kb

def handle_profile_callback(chat_id, data):
    """
    Inline tugmalar orqali 'pt_' bilan kelgan callback'larni boshqarish.
    """
    # ─── TESTNI BEKOR QILISH ───
    if data == "pt_cancel":
        cancel_interest_test(chat_id)
        return "❌ Qiziqishlar testi bekor qilindi.", {"inline_keyboard": [[{"text": "🎯 Testni qayta boshlash", "callback_data": "pt_start_test"}]]}

    # ─── TESTNI BOSHLASH ───
    if data == "pt_start_test":
        return start_interest_test(chat_id)

    # ─── PROFILNI KO'RSATISH ───
    if data == "pt_view_profile":
        prof = load_personal_profile()
        return format_profile_view(prof), build_profile_action_keyboard()

    # ─── PROFILNI O'ZGARTIRISH MENYUSI ───
    if data == "pt_edit_menu":
        return get_edit_menu_text_and_keyboard()

    # ─── QIZIQISH QO'SHISH MENYUSI ───
    if data == "pt_action_add":
        return prompt_add_interest_text()

    # ─── QIZIQISHNI O'CHIRISH MENYUSI ───
    if data == "pt_action_del":
        return prompt_remove_interest_text()

    # ─── TESTDA VARIANT BOSILGANDA (pt_opt_STEP_INDEX) ───
    if data.startswith("pt_opt_"):
        parts = data.split("_")
        if len(parts) >= 4:
            step = int(parts[2])
            opt_idx = int(parts[3])
            session = TEST_SESSIONS.get(chat_id)
            if not session or session["step"] != step:
                return None, None

            cfg = get_step_config(step)
            if not cfg or opt_idx >= len(cfg.get("options", [])):
                return None, None

            opt_name = cfg["options"][opt_idx]
            temp_items = session.setdefault("temp_items", [])

            # Agar bu 8 yoki 9-bosqich bo'lsa (yagona qiymat tanlash)
            if cfg["key"] == "salary":
                session["data"]["salary"] = parse_salary_input(opt_name)
                # To'g'ridan-to'g'ri keyingi qadamga o'tkazish
                return process_test_input(chat_id, "skip")
            elif cfg["key"] == "career_goal":
                session["data"]["career_goal"] = {"goal": opt_name, "priority": "HIGH"}
                return process_test_input(chat_id, "skip")

            # 1-7 bosqichlar: ko'p tanlovli (multi-select) va ustuvorlik
            existing = next((x for x in temp_items if x["name"].lower() == opt_name.lower()), None)
            if existing:
                # Ustuvorlikni almashtirish: HIGH -> MEDIUM -> LOW -> O'chirish
                if existing["priority"] == "HIGH":
                    existing["priority"] = "MEDIUM"
                elif existing["priority"] == "MEDIUM":
                    existing["priority"] = "LOW"
                else:
                    temp_items.remove(existing)
            else:
                temp_items.append({"name": opt_name, "priority": "HIGH"})

            # Tugmalarni yangilab qaytarish
            kb = build_step_keyboard(step, selected_items=temp_items)
            current_selections_str = ", ".join([f"{it['name']} ({PRIORITY_BADGES.get(it['priority'], it['priority'])})" for it in temp_items])
            text = (
                f"{cfg['prompt']}\n\n"
                f"📌 <b>Hozir tanlandi:</b>\n{current_selections_str if current_selections_str else '<i>Hech narsa tanlanmagan</i>'}\n\n"
                "<i>(Tugmani yana bossangiz: HIGH ➡️ MEDIUM ➡️ LOW ➡️ O'chirish o'rtasida aylanadi)</i>"
            )
            return text, kb

    # ─── TESTDA SKIP BOSILGANDA ───
    if data.startswith("pt_skip_"):
        return process_test_input(chat_id, "skip")

    # ─── TESTDA KEYINGISI BOSILGANDA ───
    if data.startswith("pt_next_"):
        session = TEST_SESSIONS.get(chat_id)
        if session:
            return process_test_input(chat_id, "skip")

    # ─── BIROR ANIQ BOSQICHNI QAYTA TO'LDIRISH (EDIT STEP) ───
    if data.startswith("pt_edit_step_"):
        step_num = int(data.replace("pt_edit_step_", ""))
        TEST_SESSIONS[chat_id] = {
            "step": step_num,
            "data": load_personal_profile(),
            "temp_items": []
        }
        cfg = get_step_config(step_num)
        kb = build_step_keyboard(step_num, selected_items=[])
        return (f"✏️ <b>{cfg['title']}ni tahrirlash:</b>\n\n{cfg['prompt']}", kb)

    # ─── QIZIQISHNI O'CHIRISH CALLBACK (pt_del_item_ITEM) ───
    if data.startswith("pt_del_item_"):
        item_name = data.replace("pt_del_item_", "")
        success = remove_interest_from_profile(item_name)
        if success:
            text = f"✅ <b>'{item_name}'</b> profilingizdan olib tashlandi.\n\n{format_profile_view(load_personal_profile())}"
        else:
            text = f"❌ '{item_name}' topilmadi."
        return text, build_profile_action_keyboard()

    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# PROFILNI CHIQARISH VA TAHRIRLASH FUNKSIYALARI
# ─────────────────────────────────────────────────────────────────────────────

def format_items_list(items):
    """Ro'yxatdagi elementlarni ustuvorlik emojisi bilan chiroyli formatlaydi."""
    if not items or not isinstance(items, list):
        return "<i>(Belgilanmagan)</i>"
    lines = []
    for it in items:
        if isinstance(it, dict):
            name = it.get("name", "")
            prio = it.get("priority", "HIGH")
            badge = PRIORITY_BADGES.get(prio, prio)
            lines.append(f" • {name} [{badge}]")
        elif isinstance(it, str):
            lines.append(f" • {it} [🔴 HIGH]")
    return "\n".join(lines) if lines else "<i>(Belgilanmagan)</i>"

def format_profile_view(profile):
    """Shaxsiy profilning to'liq chiroyli ko'rinishi."""
    prof = profile or load_personal_profile()

    salary_data = prof.get("salary", {})
    min_sal = salary_data.get("min_salary") or "Ko'rsatilmagan"
    ideal_sal = salary_data.get("ideal_salary") or "Ko'rsatilmagan"
    unpaid = salary_data.get("unpaid_internship") or "Ko'rsatilmagan"
    salary_str = f"Min: {min_sal} | Ideal: {ideal_sal} | Unpaid: {unpaid}"
    if salary_data.get("raw_text") and not (salary_data.get("min_salary") or salary_data.get("ideal_salary")):
        salary_str = salary_data.get("raw_text")

    goal_data = prof.get("career_goal", {})
    goal_str = goal_data.get("goal") or "Belgilanmagan"

    updated_at = prof.get("metadata", {}).get("updated_at", "Noma'lum")

    text = (
        "📋 <b>SHAXSIY PROFIL VA QIZIQISHLAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>Kasbiy qiziqishlar:</b>\n{format_items_list(prof.get('professional_interests'))}\n\n"
        f"💼 <b>Ish va bandlik turi:</b>\n{format_items_list(prof.get('job_types'))}\n\n"
        f"🛡 <b>Kiberxavfsizlik yo'nalishlari:</b>\n{format_items_list(prof.get('cybersecurity_interests'))}\n\n"
        f"💻 <b>Texnologiyalar:</b>\n{format_items_list(prof.get('technologies'))}\n\n"
        f"🎓 <b>Ta'lim va imkoniyatlar:</b>\n{format_items_list(prof.get('education_interests'))}\n\n"
        f"🏢 <b>Kompaniya va sohalar:</b>\n{format_items_list(prof.get('target_industries'))}\n\n"
        f"🌍 <b>Joylashuv:</b>\n{format_items_list(prof.get('locations'))}\n\n"
        f"💰 <b>Maosh kutilmasi:</b>\n • {salary_str}\n\n"
        f"🚀 <b>Karyera maqsadi (6–12 oy):</b>\n • <i>{goal_str}</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Oxirgi yangilanish: {updated_at}</i>"
    )
    return text

def build_profile_action_keyboard():
    """Profil ko'rilganda chiqadigan harakat tugmalari."""
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Qiziqish qo'shish", "callback_data": "pt_action_add"},
                {"text": "➖ Qiziqishni olib tashlash", "callback_data": "pt_action_del"}
            ],
            [
                {"text": "✏️ Bo'limni o'zgartirish", "callback_data": "pt_edit_menu"},
                {"text": "🔄 To'liq testni qayta topshirish", "callback_data": "pt_start_test"}
            ],
            [{"text": "📂 Asosiy menyu", "callback_data": "open_menu"}]
        ]
    }

def get_edit_menu_text_and_keyboard():
    """Bo'limlar bo'yicha tahrirlash menyusi."""
    text = (
        "✏️ <b>Qaysi bo'limni o'zgartirmoqchisiz?</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang va o'sha bosqichni qaytadan to'ldiring:"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "1. 🎯 Kasbiy qiziqishlar", "callback_data": "pt_edit_step_1"}, {"text": "2. 💼 Ish turi", "callback_data": "pt_edit_step_2"}],
            [{"text": "3. 🛡 Kiberxavfsizlik", "callback_data": "pt_edit_step_3"}, {"text": "4. 💻 Texnologiyalar", "callback_data": "pt_edit_step_4"}],
            [{"text": "5. 🎓 Ta'lim", "callback_data": "pt_edit_step_5"}, {"text": "6. 🏢 Sohalar", "callback_data": "pt_edit_step_6"}],
            [{"text": "7. 🌍 Joylashuv", "callback_data": "pt_edit_step_7"}, {"text": "8. 💰 Maosh", "callback_data": "pt_edit_step_8"}],
            [{"text": "9. 🚀 Karyera maqsadi", "callback_data": "pt_edit_step_9"}],
            [{"text": "🔄 Butun testni qaytadan boshlash", "callback_data": "pt_start_test"}],
            [{"text": "⬅️ Orqaga (Profilga qaytish)", "callback_data": "pt_view_profile"}]
        ]
    }
    return text, keyboard

def prompt_add_interest_text():
    """Qiziqish qo'shish bo'yicha yo'riqnoma va tugmalar."""
    text = (
        "➕ <b>Yangi qiziqish qo'shish</b>\n\n"
        "Qo'shmoqchi bo'lgan qiziqishingizni nomi va darajasi bilan yozing.\n"
        "Masalan: <code>Docker HIGH</code> yoki <code>Splunk MEDIUM</code> yoki oddiygina <code>FastAPI</code>\n\n"
        "<i>(Standart ustuvorlik darajasi: 🔴 HIGH)</i>"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Bekor qilish", "callback_data": "pt_view_profile"}]
        ]
    }
    return text, keyboard

def prompt_remove_interest_text():
    """Qiziqishni o'chirish menyusi va tugmalari."""
    kb = build_remove_interest_keyboard()
    if not kb:
        text = "ℹ️ Profilingizda hali o'chirish uchun birorta ham qiziqish mavjud emas."
        kb = {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": "pt_view_profile"}]]}
    else:
        text = "➖ <b>O'chirmoqchi bo'lgan qiziqishingiz ustiga bosing:</b>\n<i>(Yoki uning nomini yozib yuboring)</i>"
    return text, kb

# ─────────────────────────────────────────────────────────────────────────────
# QIZIQISH QO'SHISH VA OLIB TASHLASH (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

def add_interest_to_profile(item_name, priority="HIGH", category=None):
    """
    Profilga bitta qiziqish qo'shadi. Agar kategoriya aytilmasa,
    avtomatik mos toifani aniqlaydi yoki 'professional_interests'ga qo'shadi.
    """
    clean_name = item_name.strip()
    if not clean_name:
        return False, "Qiziqish nomi bo'sh bo'lishi mumkin emas."

    # Agar matn ichida ustuvorlik ko'rsatilgan bo'lsa (masalan 'Docker HIGH')
    parsed = parse_items_with_priority(clean_name, default_priority=priority or "HIGH")
    if parsed:
        clean_name = parsed[0]["name"]
        prio = parsed[0]["priority"]
    else:
        prio = priority.upper() if priority and priority.upper() in ["HIGH", "MEDIUM", "LOW"] else "HIGH"
    profile = load_personal_profile()

    # Agar kategoriya berilmagan bo'lsa, mosini aniqlash
    target_key = category
    if not target_key:
        name_lower = clean_name.lower()
        if any(w in name_lower for w in ["python", "linux", "git", "sql", "docker", "cloud", "c++", "java", "react", "splunk", "wireshark", "bash", "powershell"]):
            target_key = "technologies"
        elif any(w in name_lower for w in ["soc", "siem", "pentest", "incident", "edr", "dlp", "ueba", "kiber", "security", "threat", "forensic", "nmap", "burp"]):
            target_key = "cybersecurity_interests"
        elif any(w in name_lower for w in ["internship", "junior", "trainee", "remote", "hybrid", "full-time", "part-time"]):
            target_key = "job_types"
        elif any(w in name_lower for w in ["kurs", "grant", "bootcamp", "hackathon", "sertifikat", "scholarship"]):
            target_key = "education_interests"
        elif any(w in name_lower for w in ["bank", "fintech", "startup", "telecom", "davlat"]):
            target_key = "target_industries"
        else:
            target_key = "professional_interests"

    items = profile.setdefault(target_key, [])
    # Agar mavjud bo'lsa ustuvorligini yangilash
    existing = next((x for x in items if x.get("name", "").lower() == clean_name.lower()), None)
    if existing:
        existing["priority"] = prio
    else:
        items.append({"name": clean_name, "priority": prio})

    save_personal_profile(profile)
    badge = PRIORITY_BADGES.get(prio, prio)
    return True, f"✅ <b>'{clean_name}'</b> [{badge}] muvaffaqiyatli profilingizga qo'shildi!"

def remove_interest_from_profile(item_name):
    """
    Profilning barcha toifalaridan kiritilgan qiziqishni o'chiradi.
    """
    clean_name = item_name.strip().lower()
    profile = load_personal_profile()
    found = False

    list_keys = [
        "professional_interests", "job_types", "cybersecurity_interests",
        "technologies", "education_interests", "target_industries", "locations"
    ]
    for key in list_keys:
        items = profile.get(key, [])
        new_items = [it for it in items if it.get("name", "").lower() != clean_name]
        if len(new_items) != len(items):
            profile[key] = new_items
            found = True

    if found:
        save_personal_profile(profile)
    return found

def get_all_interests_flat():
    """O'chirish uchun profildagi barcha qiziqishlar ro'yxatini qaytaradi."""
    profile = load_personal_profile()
    result = []
    list_keys = [
        "professional_interests", "job_types", "cybersecurity_interests",
        "technologies", "education_interests", "target_industries", "locations"
    ]
    for key in list_keys:
        for it in profile.get(key, []):
            if isinstance(it, dict) and it.get("name"):
                result.append(it)
    return result

def build_remove_interest_keyboard():
    """Qiziqishlarni bir tugma bosish bilan o'chirish uchun klaviatura."""
    interests = get_all_interests_flat()
    if not interests:
        return None
    keyboard = []
    row = []
    for it in interests[:16]:  # Maksimal 16 ta eng faol element
        name = it["name"]
        row.append({"text": f"❌ {name}", "callback_data": f"pt_del_item_{name}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([{"text": "⬅️ Orqaga", "callback_data": "pt_view_profile"}])
    return {"inline_keyboard": keyboard}

# ─────────────────────────────────────────────────────────────────────────────
# KELGUSIDA "TIME & SCHEDULE" MODULINI ULASH UCHUN INTEGRATSIYA API
# ─────────────────────────────────────────────────────────────────────────────

def get_schedule_config():
    """Kelgusidagi Time & Schedule moduli uchun sozlamalarni o'qiydi."""
    prof = load_personal_profile()
    return prof.get("schedule", {})

def update_schedule_config(schedule_dict):
    """Kelgusidagi Time & Schedule moduli uchun sozlamalarni yangilaydi."""
    prof = load_personal_profile()
    current_sched = prof.setdefault("schedule", {})
    current_sched.update(schedule_dict)
    return save_personal_profile(prof)

def get_prioritized_interests(min_priority="LOW"):
    """
    Belgilangan minimal ustuvorlik darajasiga mos keluvchi barcha qiziqishlarni qaytaradi.
    Vakansiya va monitoring modullari uchun qulay API.
    """
    prio_ranks = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_rank = prio_ranks.get(min_priority.upper(), 1)

    prof = load_personal_profile()
    result = {}
    list_keys = [
        "professional_interests", "job_types", "cybersecurity_interests",
        "technologies", "education_interests", "target_industries", "locations"
    ]
    for key in list_keys:
        filtered = []
        for it in prof.get(key, []):
            if isinstance(it, dict):
                prio = it.get("priority", "HIGH").upper()
                if prio_ranks.get(prio, 1) >= min_rank:
                    filtered.append(it["name"])
        result[key] = filtered
    return result
