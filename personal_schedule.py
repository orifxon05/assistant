# -*- coding: utf-8 -*-
"""
personal_schedule.py - Jarvis Personal Schedule Module

Modul vazifalari:
1. Foydalanuvchining har bir kunlik vaqt jadvalini aniqlash va boshqarish:
   - Uydan chiqish vaqti (leave_home)
   - O'qish/ish vaqti (study_work)
   - Yo'l vaqti (commute)
   - Bo'sh vaqt (free_time)
   - Uyga qaytish vaqti (return_home)
   - Dam olish vaqti (rest_time)
2. Barcha ma'lumotlarni `schedule.json` faylida saqlash.
3. Asosiy buyruqlar:
   - "Jadvalimni ko'rsat" -> To'liq haftalik grafikni chiroyli ko'rsatish
   - "Bugun qachon bo'shman?" -> Bugungi kun va ayni vaqtdagi holat, bo'sh soatlar tahlili
   - "Jadvalimni o'zgartir" -> Kunma-kun yoki to'liq tahrirlash menyusi
4. Kelgusida vakansiya ish vaqtini jadval bilan avtomatik solishtirish uchun
   moslashuvchan taqqoslash (compatibility) API'si.
"""

import os
import re
import json
from datetime import datetime, time, timedelta

SCHEDULE_FILE = "schedule.json"

DAYS_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DAYS_UZ = {
    "monday": "Dushanba",
    "tuesday": "Seshanba",
    "wednesday": "Chorshanba",
    "thursday": "Payshanba",
    "friday": "Juma",
    "saturday": "Shanba",
    "sunday": "Yakshanba"
}

UZ_TO_DAY_KEY = {
    "dushanba": "monday",
    "seshanba": "tuesday",
    "chorshanba": "wednesday",
    "payshanba": "thursday",
    "juma": "friday",
    "shanba": "saturday",
    "yakshanba": "sunday"
}

WEEKDAY_INDEX_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}

def get_default_day_schedule(day_key="monday"):
    """Standart boshlang'ich kunlik jadval shabloni."""
    day_name = DAYS_UZ.get(day_key, "Dushanba")
    is_weekend = day_key in ["saturday", "sunday"]
    if is_weekend:
        return {
            "day_name_uz": day_name,
            "is_day_off": True,
            "leave_home": None,
            "study_work": None,
            "commute": None,
            "return_home": None,
            "free_time": "To'liq kun bo'sh",
            "rest_time": "23:00 - 08:00",
            "raw_text": "Dam olish kuni"
        }
    return {
        "day_name_uz": day_name,
        "is_day_off": False,
        "leave_home": "07:00",
        "study_work": "07:00 - 13:00",
        "commute": "07:00 - 08:00, 13:00 - 14:00",
        "return_home": "14:00",
        "free_time": "14:00 - 23:00",
        "rest_time": "23:00 - 06:30",
        "raw_text": "07:00 uydan chiqish, 07:00-13:00 o'qish, 13:00 dan keyin bo'sh vaqt"
    }

def get_default_full_schedule():
    """Barcha 7 kun uchun standart jadval."""
    days = {}
    for d in DAYS_ORDER:
        days[d] = get_default_day_schedule(d)
    return {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_configured": False
        },
        "days": days
    }

# ─────────────────────────────────────────────────────────────────────────────
# JSON FAYLNI O'QISH VA SAQLASH
# ─────────────────────────────────────────────────────────────────────────────

def load_schedule():
    """schedule.json faylini o'qiydi. Fayl yo'q bo'lsa standart shablonni yaratadi."""
    if not os.path.exists(SCHEDULE_FILE):
        default_data = get_default_full_schedule()
        save_schedule(default_data)
        return default_data
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "days" not in data:
                data["days"] = get_default_full_schedule()["days"]
            return data
    except Exception as e:
        print(f"[SCHEDULE] Faylni o'qishda xatolik: {e}")
        return get_default_full_schedule()

def save_schedule(data):
    """schedule.json fayliga ma'lumotlarni xavfsiz saqlaydi."""
    try:
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["updated_at"] = datetime.now().isoformat()
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SCHEDULE] Saqlashda xatolik: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MATNDAN VAQT VA JADVAL ELEMENTLARINI AJRATISH (SMART PARSER)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_time_str(val):
    """
    Turli formatdagi vaqtlarni 'HH:MM' standart formatga keltiradi.
    Masalan: '7' -> '07:00', '7:00' -> '07:00', '13.30' -> '13:30', '08' -> '08:00'
    """
    if not val:
        return None
    val = val.strip().replace(".", ":")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?$", val)
    if m:
        h = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        if 0 <= h <= 23 and 0 <= mins <= 59:
            return f"{h:02d}:{mins:02d}"
    return val

def parse_time_range(text):
    """
    '07:00 - 13:00' yoki '08:00 dan 14:00 gacha' kabi oraliqlarni ajratadi.
    """
    m = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:[-–—]|dan)\s*(\d{1,2}(?:[:.]\d{2})?)(?:\s*gacha)?", text)
    if m:
        start = normalize_time_str(m.group(1))
        end = normalize_time_str(m.group(2))
        return f"{start} - {end}"
    return None

def parse_day_schedule_input(raw_text, day_key="monday"):
    """
    Foydalanuvchi yozgan ixtiyoriy matndan 6 ta komponentni ajratib oladi:
    - Uydan chiqish vaqti
    - O'qish/ish vaqti
    - Yo'l vaqti
    - Bo'sh vaqt
    - Uyga qaytish
    - Dam olish vaqti
    """
    text = raw_text.strip()
    text_lower = text.lower()
    day_name = DAYS_UZ.get(day_key, "Kun")

    # Agar butun kun dam olish deb kiritilsa
    is_off = False
    if any(w in text_lower for w in ["dam olish kuni", "dam kuni", "to'liq bo'sh", "bo'sh kun", "ish yo'q", "dars yo'q"]):
        is_off = True
    elif text_lower.strip() in ["dam", "dam olish", "damolish", "off"]:
        is_off = True
    elif "dam olish" in text_lower and not any(k in text_lower for k in ["o'qish", "ish", "uydan", "dars", "chiqish", "qaytish"]):
        is_off = True

    if is_off:
        return {
            "day_name_uz": day_name,
            "is_day_off": True,
            "leave_home": None,
            "study_work": None,
            "commute": None,
            "return_home": None,
            "free_time": "To'liq kun bo'sh",
            "rest_time": "23:00 - 08:00",
            "raw_text": text
        }

    # Boshlang'ich qiymatlar
    leave_home = None
    study_work = None
    commute = None
    free_time = None
    return_home = None
    rest_time = None

    # 1. O'qish / Ish vaqtini aniqlash (masalan: '07:00-13:00 o'qish' yoki 'o'qish 08:30 dan 14:00 gacha')
    study_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?\s*[-–—dan]+\s*\d{1,2}(?:[:.]\d{2})?(?:\s*gacha)?)\s*(?:o['ʻ`ʼ]?qish|ish|dars|univer|maktab|ishlash)", text_lower)
    if not study_match:
        study_match = re.search(r"(?:o['ʻ`ʼ]?qish|ish|dars|univer|maktab)\s*:?\s*(\d{1,2}(?:[:.]\d{2})?\s*[-–—dan]+\s*\d{1,2}(?:[:.]\d{2})?(?:\s*gacha)?)", text_lower)
    if study_match:
        study_work = parse_time_range(study_match.group(1))

    # 2. Uydan chiqish vaqti (masalan: '07:00 uydan chiqish' yoki 'uydan 07:00 da chiqaman')
    leave_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:da|ga|da\s+uydan|uydan\s+chiq|chiqish|chiqaman)", text_lower)
    if not leave_match:
        leave_match = re.search(r"(?:uydan\s+chiqish|chiqish|chiqaman)\s*:?\s*(\d{1,2}(?:[:.]\d{2})?)", text_lower)
    if leave_match:
        leave_home = normalize_time_str(leave_match.group(1))

    # 3. Uyga qaytish vaqti (masalan: '14:00 da uyga kelaman' yoki 'uyga qaytish 14:00')
    return_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:da\s+uyga|uyga\s+kel|uyga\s+qayt|qaytish|kelaman)", text_lower)
    if not return_match:
        return_match = re.search(r"(?:uyga\s+qaytish|uyga\s+kelish|qaytish|kelaman)\s*:?\s*(\d{1,2}(?:[:.]\d{2})?)", text_lower)
    if return_match:
        return_home = normalize_time_str(return_match.group(1))

    # 4. Bo'sh vaqt (masalan: '13:00 dan keyin bo'shman', '14:00-22:00 bo'sh vaqt', '14:00 dan boshlab')
    free_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?\s*[-–—dan]+\s*\d{1,2}(?:[:.]\d{2})?(?:\s*gacha)?)\s*(?:bo['ʻ`ʼ]?sh|erkin)", text_lower)
    if free_match:
        free_time = parse_time_range(free_match.group(1))
    else:
        after_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:dan\s+keyin|dan\s+boshlab|dan\s+so['ʻ`ʼ]?ng)\s*(?:bo['ʻ`ʼ]?sh|erkin)?", text_lower)
        if after_match:
            after_t = normalize_time_str(after_match.group(1))
            free_time = f"{after_t} dan keyin (23:00 gacha)"

    # 5. Yo'l vaqti (masalan: '1 soat yo'l', 'yo'lga 40 daqiqa', '07:00-08:00 yo'l')
    commute_match = re.search(r"(?:yo['ʻ`ʼ]?l|yo['ʻ`ʼ]?lga|qatnov)\s*:?\s*([^,;\n]+)", text_lower)
    if commute_match:
        commute_candidate = commute_match.group(1).strip()
        # Qisqa tushunarli qilish
        commute = commute_candidate.split(".")[0].strip()
    elif leave_home and study_work:
        # Avtomatik hisoblash: chiqish bilan o'qish boshlanishi orasi
        sw_start = study_work.split("-")[0].strip()
        if leave_home != sw_start:
            commute = f"{leave_home} - {sw_start}"

    # 6. Dam olish vaqti (masalan: '23:00 dan uxlash', '23:00-07:00 dam olish')
    rest_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?\s*[-–—dan]+\s*\d{1,2}(?:[:.]\d{2})?(?:\s*gacha)?)\s*(?:dam|uxlash|uyqu)", text_lower)
    if rest_match:
        rest_time = parse_time_range(rest_match.group(1))
    else:
        rest_start_match = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:dan\s+boshlab\s+)?(?:dam|uxlash|uyqu)", text_lower)
        if rest_start_match:
            rest_time = f"{normalize_time_str(rest_start_match.group(1))} dan"

    # Agar umumiy oraliqlar orqali topilmagan bo'lsa, barcha vaqtlarni tartib bo'yicha aniqlash
    all_times = re.findall(r"\b(\d{1,2}(?:[:.]\d{2})?)\b", text)
    all_norm_times = [normalize_time_str(t) for t in all_times if normalize_time_str(t)]

    # Mantiqiy to'ldirish (agar foydalanuvchi qisqa yozgan bo'lsa, masalan "07:00, 08:00-13:00, 13:00 dan keyin bo'sh")
    if not leave_home and len(all_norm_times) >= 1:
        leave_home = all_norm_times[0]

    if not study_work and len(all_norm_times) >= 3:
        study_work = f"{all_norm_times[1]} - {all_norm_times[2]}"

    if not return_home:
        if study_work:
            return_home = study_work.split("-")[-1].strip()
        elif len(all_norm_times) >= 4:
            return_home = all_norm_times[3]

    if not free_time:
        if return_home:
            free_time = f"{return_home} dan keyin (23:00 gacha)"
        elif study_work:
            free_time = f"{study_work.split('-')[-1].strip()} dan keyin (23:00 gacha)"
        else:
            free_time = "14:00 - 23:00"

    if not commute:
        commute = "Yo'l vaqti ~1-1.5 soat"

    if not rest_time:
        rest_time = "23:00 - 06:30"

    return {
        "day_name_uz": day_name,
        "is_day_off": False,
        "leave_home": leave_home or "07:00",
        "study_work": study_work or "08:00 - 13:00",
        "commute": commute,
        "return_home": return_home or "14:00",
        "free_time": free_time,
        "rest_time": rest_time,
        "raw_text": text
    }

# ─────────────────────────────────────────────────────────────────────────────
# FOYDALANUVCHI INTERAKTIV SOZLASH SESSIYALARI (SCHEDULE_SESSIONS)
# ─────────────────────────────────────────────────────────────────────────────

SCHEDULE_SESSIONS = {}

def is_in_schedule_setup(chat_id):
    """Foydalanuvchi jadval sozlash jarayonidami?"""
    return chat_id in SCHEDULE_SESSIONS

def cancel_schedule_setup(chat_id):
    """Jadval sozlash jarayonini bekor qilish."""
    if chat_id in SCHEDULE_SESSIONS:
        del SCHEDULE_SESSIONS[chat_id]
        return True
    return False

def start_schedule_setup(chat_id, target_day=None):
    """
    Jadval sozlashni boshlaydi.
    target_day berilsa - aynan shu kunni o'zi so'raladi.
    target_day bo'lmasa - Dushanbadan boshlab barcha kunlar ketma-ket so'raladi.
    """
    SCHEDULE_SESSIONS[chat_id] = {
        "target_day": target_day,
        "current_day_idx": 0 if not target_day else DAYS_ORDER.index(target_day),
        "days_data": {}
    }
    return get_current_setup_step_prompt(chat_id)

def get_current_setup_step_prompt(chat_id):
    """Joriy kun uchun savol matni va tezkor tugmalarni qaytaradi."""
    session = SCHEDULE_SESSIONS.get(chat_id)
    if not session:
        return "Sessiya topilmadi.", None

    target_day = session.get("target_day")
    if target_day:
        day_key = target_day
        step_title = f"🗓 <b>{DAYS_UZ[day_key]} kuni uchun jadvalni o'zgartirish</b>"
    else:
        idx = session.get("current_day_idx", 0)
        day_key = DAYS_ORDER[idx]
        step_title = f"🗓 <b>{idx + 1}/7-kun: {DAYS_UZ[day_key]} kuni</b>"

    prompt = (
        f"{step_title}\n\n"
        f"Ushbu kun uchun vaqtlaringizni kiriting:\n"
        f"• 🚪 <b>Uydan chiqish vaqti</b> (masalan: <code>07:00</code>)\n"
        f"• 📚 <b>O'qish/ish vaqti</b> (masalan: <code>07:00–13:00</code> yoki <code>08:00–14:00</code>)\n"
        f"• 🚌 <b>Yo'l vaqti</b> (masalan: <code>07:00–08:00</code> yoki <code>1 soat</code>)\n"
        f"• 🏠 <b>Uyga qaytish</b> (masalan: <code>14:00</code>)\n"
        f"• ⏳ <b>Bo'sh vaqt</b> (masalan: <code>13:00 dan keyin</code> yoki <code>14:00–23:00</code>)\n"
        f"• 😴 <b>Dam olish vaqti</b> (masalan: <code>23:00 dan</code>)\n\n"
        f"💡 <i>Hammasini bitta xabarda erkin matn shaklida yozishingiz mumkin:\n"
        f"Masalan:</i> <code>07:00 uydan chiqish, 07:00-13:00 o'qish, 13:00 dan keyin bo'shman</code>\n\n"
        f"Yoki quyidagi tezkor tayyor variantlardan birini bosing:"
    )

    keyboard = [
        [
            {"text": "📚 07:00 chiqish, 07:00-13:00 o'qish", "callback_data": f"sc_fast_preset_1_{day_key}"},
        ],
        [
            {"text": "💼 08:00 chiqish, 09:00-18:00 ish", "callback_data": f"sc_fast_preset_2_{day_key}"},
        ],
        [
            {"text": "🎉 Dam olish kuni (To'liq bo'sh)", "callback_data": f"sc_fast_off_{day_key}"}
        ]
    ]

    # Agar 1-kunda (Dushanba) bo'lsa, "Dushanba-Juma bir xil qilish" qulay tugmasi
    if not target_day and session.get("current_day_idx") == 0:
        keyboard.append([
            {"text": "⚡️ Dushanba–Jumani shu jadval bilan to'ldirish", "callback_data": "sc_apply_weekdays"}
        ])

    keyboard.append([
        {"text": "⏩ O'tkazish (Standart qoldirish)", "callback_data": "sc_skip_day"},
        {"text": "❌ Bekor qilish", "callback_data": "sc_cancel"}
    ])

    return prompt, {"inline_keyboard": keyboard}

def process_schedule_input(chat_id, user_text):
    """Foydalanuvchi yuborgan matnni qabul qilib, joriy kun jadvalini saqlash."""
    session = SCHEDULE_SESSIONS.get(chat_id)
    if not session:
        return None, None

    target_day = session.get("target_day")
    if target_day:
        day_key = target_day
    else:
        idx = session.get("current_day_idx", 0)
        day_key = DAYS_ORDER[idx]

    # Matnni tahlil qilish
    parsed_day = parse_day_schedule_input(user_text, day_key=day_key)
    session["days_data"][day_key] = parsed_day

    # Agar aynan bitta kunni o'zgartirish rejimida bo'lsa
    if target_day:
        sched = load_schedule()
        sched["days"][day_key] = parsed_day
        sched["metadata"]["is_configured"] = True
        save_schedule(sched)
        del SCHEDULE_SESSIONS[chat_id]
        return (
            f"✅ <b>{DAYS_UZ[day_key]} kuni jadvali muvaffaqiyatli saqlandi!</b>\n\n"
            f"{format_single_day_view(parsed_day)}",
            build_schedule_action_keyboard()
        )

    # Agar Dushanba bo'lsa va foydalanuvchi butun ish haftasiga qo'llashni xohlasa
    # yoki oddiy keyingi kunga o'tish
    next_idx = session["current_day_idx"] + 1
    session["current_day_idx"] = next_idx

    if next_idx < len(DAYS_ORDER):
        return get_current_setup_step_prompt(chat_id)
    else:
        # Barcha 7 kun kiritib bo'lindi!
        return finalize_full_schedule(chat_id)

def finalize_full_schedule(chat_id):
    """Barcha 7 kun kiritilgach, schedule.json ga to'liq yozadi."""
    session = SCHEDULE_SESSIONS.pop(chat_id, None)
    if not session:
        return "Sessiya topilmadi.", None

    sched = load_schedule()
    for d_key, d_val in session.get("days_data", {}).items():
        sched["days"][d_key] = d_val

    # Agar ba'zi kunlar o'tkazib yuborilgan bo'lsa
    for d_key in DAYS_ORDER:
        if d_key not in sched["days"]:
            sched["days"][d_key] = get_default_day_schedule(d_key)

    sched["metadata"]["is_configured"] = True
    save_schedule(sched)

    text = (
        "🎉 <b>Haftalik shaxsiy vaqt jadvalingiz muvaffaqiyatli saqlandi!</b>\n"
        "Barcha ma'lumotlar <code>schedule.json</code> fayliga yozildi.\n\n"
        f"{format_schedule_view(sched)}"
    )
    return text, build_schedule_action_keyboard()

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER (sc_ PREFIKSI BILAN)
# ─────────────────────────────────────────────────────────────────────────────

def handle_schedule_callback(chat_id, data):
    """Inline tugmalardan kelgan sc_ callback'larni boshqarish."""
    # ─── BEKOR QILISH ───
    if data == "sc_cancel":
        cancel_schedule_setup(chat_id)
        return "❌ Jadval kiritish bekor qilindi.", {"inline_keyboard": [[{"text": "🗓 Jadvalimni ko'rsat", "callback_data": "sc_view"}]]}

    # ─── JADVALNI KO'RSATISH ───
    if data == "sc_view":
        sched = load_schedule()
        return format_schedule_view(sched), build_schedule_action_keyboard()

    # ─── BUGUN QACHON BO'SHMAN ───
    if data == "sc_free_today":
        return get_today_free_time_info()

    # ─── JADVALNI O'ZGARTIRISH MENYUSI ───
    if data == "sc_edit_menu":
        return get_edit_menu_text_and_keyboard()

    # ─── TO'LIQ QAYTA TUZISH ───
    if data == "sc_restart_all":
        return start_schedule_setup(chat_id, target_day=None)

    # ─── ANIQ BIR KUNNI TANLASH (sc_day_monday ...) ───
    if data.startswith("sc_day_"):
        day_key = data.replace("sc_day_", "")
        if day_key in DAYS_ORDER:
            return start_schedule_setup(chat_id, target_day=day_key)

    # ─── TEZKOR PRESET 1: 07:00 chiqish, 07:00-13:00 o'qish ───
    if data.startswith("sc_fast_preset_1_"):
        day_key = data.replace("sc_fast_preset_1_", "")
        preset_text = "07:00 uydan chiqish, 07:00-13:00 o'qish, 13:00-14:00 yo'l, 14:00 uyga qaytish, 13:00 dan keyin bo'sh vaqt, 23:00 dam olish"
        return process_schedule_input(chat_id, preset_text)

    # ─── TEZKOR PRESET 2: 08:00 chiqish, 09:00-18:00 ish ───
    if data.startswith("sc_fast_preset_2_"):
        day_key = data.replace("sc_fast_preset_2_", "")
        preset_text = "08:00 uydan chiqish, 09:00-18:00 ish, 18:00-19:00 yo'l, 19:00 uyga qaytish, 19:00 dan keyin bo'sh vaqt, 23:30 dam olish"
        return process_schedule_input(chat_id, preset_text)

    # ─── TEZKOR PRESET: DAM OLISH KUNI ───
    if data.startswith("sc_fast_off_"):
        day_key = data.replace("sc_fast_off_", "")
        return process_schedule_input(chat_id, "Dam olish kuni, kun bo'yi bo'sh")

    # ─── DUSHANBA-JUMANI SHU JADVAL BILAN TO'LDIRISH ───
    if data == "sc_apply_weekdays":
        session = SCHEDULE_SESSIONS.get(chat_id)
        if session:
            # Dushanba uchun kiritilgan yoki standart jadvalni olamiz
            mon_data = session["days_data"].get("monday")
            if not mon_data:
                mon_data = parse_day_schedule_input("07:00 uydan chiqish, 07:00-13:00 o'qish, 13:00 dan keyin bo'sh vaqt", "monday")
                session["days_data"]["monday"] = mon_data

            # Dushanba-Jumaga ko'chiramiz
            for d in ["tuesday", "wednesday", "thursday", "friday"]:
                copied = dict(mon_data)
                copied["day_name_uz"] = DAYS_UZ[d]
                session["days_data"][d] = copied

            # Shanbaga o'tamiz
            session["current_day_idx"] = DAYS_ORDER.index("saturday")
            return get_current_setup_step_prompt(chat_id)

    # ─── KUNNI O'TKAZISH (SKIP) ───
    if data == "sc_skip_day":
        session = SCHEDULE_SESSIONS.get(chat_id)
        if session:
            target_day = session.get("target_day")
            day_key = target_day or DAYS_ORDER[session.get("current_day_idx", 0)]
            if day_key not in session["days_data"]:
                session["days_data"][day_key] = get_default_day_schedule(day_key)
            if target_day:
                del SCHEDULE_SESSIONS[chat_id]
                sched = load_schedule()
                return (
                    f"ℹ️ {DAYS_UZ[day_key]} kuni jadvali o'zgarishsiz qoldirildi.",
                    build_schedule_action_keyboard()
                )
            next_idx = session["current_day_idx"] + 1
            session["current_day_idx"] = next_idx
            if next_idx < len(DAYS_ORDER):
                return get_current_setup_step_prompt(chat_id)
            else:
                return finalize_full_schedule(chat_id)

    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# JADVALNI KO'RSATISH VA CHIQARISH FORMATI
# ─────────────────────────────────────────────────────────────────────────────

def format_single_day_view(day_data):
    """Bitta kunning chiroyli vizual ko'rinishi."""
    day_name = day_data.get("day_name_uz", "Kun")
    if day_data.get("is_day_off"):
        return (
            f"📅 <b>{day_name}:</b>\n"
            f"  🎉 <i>Dam olish kuni (Kun bo'yi to'liq bo'sh)</i>\n"
            f"  😴 Dam olish: <code>{day_data.get('rest_time', '23:00 - 08:00')}</code>\n"
        )

    leave_home = day_data.get("leave_home") or "—"
    study_work = day_data.get("study_work") or "—"
    commute = day_data.get("commute") or "—"
    return_home = day_data.get("return_home") or "—"
    free_time = day_data.get("free_time") or "—"
    rest_time = day_data.get("rest_time") or "—"

    return (
        f"📅 <b>{day_name}:</b>\n"
        f"  🚪 Uydan chiqish: <code>{leave_home}</code>\n"
        f"  📚 O'qish/ish: <code>{study_work}</code>\n"
        f"  🚌 Yo'l vaqti: <code>{commute}</code>\n"
        f"  🏠 Uyga qaytish: <code>{return_home}</code>\n"
        f"  ⏳ <b>Bo'sh vaqt:</b> <code>{free_time}</code>\n"
        f"  😴 Dam olish: <code>{rest_time}</code>\n"
    )

def format_schedule_view(sched=None):
    """Barcha 7 kunning to'liq haftalik jadvalini chiqaradi."""
    if not sched:
        sched = load_schedule()

    lines = [
        "🗓 <b>JARVIS — SHAXSIY VAQT JADVALINGIZ</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    days = sched.get("days", {})
    for d_key in DAYS_ORDER:
        d_val = days.get(d_key, get_default_day_schedule(d_key))
        lines.append(format_single_day_view(d_val))

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>Jadvalingiz vakansiyalar ish vaqtiga mos kelishini tekshirishda foydalaniladi.</i>")

    return "\n".join(lines)

def build_schedule_action_keyboard():
    """Jadval ostidagi asosiy tezkor tugmalar."""
    return {
        "inline_keyboard": [
            [
                {"text": "⏳ Bugun qachon bo'shman?", "callback_data": "sc_free_today"},
                {"text": "✏️ Jadvalimni o'zgartir", "callback_data": "sc_edit_menu"}
            ],
            [
                {"text": "🔄 To'liq qayta kiritish", "callback_data": "sc_restart_all"},
                {"text": "📂 Asosiy menyu", "callback_data": "open_menu"}
            ]
        ]
    }

def get_edit_menu_text_and_keyboard():
    """Jadvalni o'zgartirish menyusi: barcha kunlar alohida tugma shaklida."""
    text = (
        "✏️ <b>Qaysi kunning jadvalini o'zgartirmoqchisiz?</b>\n\n"
        "O'zgartirmoqchi bo'lgan kuningizni tanlang yoki 'Hafta kunlarini to'liq qayta kiritish' tugmasini bosing:"
    )
    keyboard = [
        [
            {"text": "Dushanba", "callback_data": "sc_day_monday"},
            {"text": "Seshanba", "callback_data": "sc_day_tuesday"},
            {"text": "Chorshanba", "callback_data": "sc_day_wednesday"}
        ],
        [
            {"text": "Payshanba", "callback_data": "sc_day_thursday"},
            {"text": "Juma", "callback_data": "sc_day_friday"},
            {"text": "Shanba", "callback_data": "sc_day_saturday"}
        ],
        [
            {"text": "Yakshanba", "callback_data": "sc_day_sunday"},
            {"text": "🔄 Barcha kunlar (Ketma-ket)", "callback_data": "sc_restart_all"}
        ],
        [
            {"text": "⬅️ Orqaga", "callback_data": "sc_view"}
        ]
    ]
    return text, {"inline_keyboard": keyboard}

# ─────────────────────────────────────────────────────────────────────────────
# "BUGUN QACHON BO'SHMAN?" MANTIQIY TAHLILI
# ─────────────────────────────────────────────────────────────────────────────

def get_today_free_time_info():
    """
    Bugungi kun va ayni vaqtni tahlil qilib, foydalanuvchiga to'liq
    status va bo'sh vaqtlarini tushunarli hisobot qilib qaytaradi.
    """
    now = datetime.now()
    now_hm = now.strftime("%H:%M")
    day_idx = now.weekday()  # 0: Dushanba, ..., 6: Yakshanba
    day_key = WEEKDAY_INDEX_MAP.get(day_idx, "monday")
    day_name_uz = DAYS_UZ.get(day_key, "Bugun")

    sched = load_schedule()
    today_data = sched.get("days", {}).get(day_key, get_default_day_schedule(day_key))

    is_off = today_data.get("is_day_off", False)
    leave_home = today_data.get("leave_home")
    study_work = today_data.get("study_work")
    return_home = today_data.get("return_home")
    free_time = today_data.get("free_time")
    rest_time = today_data.get("rest_time")

    lines = [
        f"⏰ <b>BUGUNGI BO'SH VAQT TAHLILI</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📅 <b>Bugungi kun:</b> {day_name_uz}",
        f"⌚️ <b>Hozirgi vaqt:</b> <code>{now_hm}</code>\n"
    ]

    if is_off:
        lines.append("🎉 <b>Bugun sizda to'liq dam olish kuni!</b>")
        lines.append("Kun bo'yi hech qanday o'qish yoki rejalashtirilgan ish yo'q, vaqtingiz mutlaqo erkin.")
        lines.append(f"\n😴 <i>Dam olish/uyqu: {rest_time or '23:00 dan'}</i>")
        return "\n".join(lines), build_schedule_action_keyboard()

    # Rejadagi soatlar
    lines.append(f"🚪 Uydan chiqish: <code>{leave_home or '—'}</code>")
    lines.append(f"📚 O'qish/ish: <code>{study_work or '—'}</code>")
    lines.append(f"🏠 Uyga qaytish: <code>{return_home or '—'}</code>")
    lines.append(f"⏳ <b>Bo'sh vaqtingiz:</b> <code>{free_time or '—'}</code>")
    lines.append(f"😴 Dam olish: <code>{rest_time or '—'}</code>\n")

    # Ayni damdagi statusni aniqlash
    # study_work boshlanish va tugash vaqti
    study_start = None
    study_end = None
    if study_work and "-" in study_work:
        parts = study_work.split("-")
        study_start = normalize_time_str(parts[0])
        study_end = normalize_time_str(parts[1])

    # Status xabari
    if study_start and study_end:
        if now_hm < (leave_home or study_start):
            lines.append("🌅 <b>Hozirgi holat:</b> Siz hali uydasiz. O'qish/ishga chiqish vaqti hali kelmadi.")
            lines.append(f"📌 Bugun asosiy bo'sh vaqtingiz <b>{return_home or study_end}</b> dan keyin boshlanadi.")
        elif (leave_home or study_start) <= now_hm < study_start:
            lines.append("🚌 <b>Hozirgi holat:</b> Yo'ldasiz / O'qishga (ishga) yetib borish vaqti.")
            lines.append(f"📌 Bugun asosiy bo'sh vaqtingiz <b>{return_home or study_end}</b> dan keyin boshlanadi.")
        elif study_start <= now_hm < study_end:
            lines.append("📚 <b>Hozirgi holat:</b> Ayni paytda o'qish/ishdagi band vaqtingiz.")
            lines.append(f"⚡️ Bo'sh vaqtingiz soat <b>{return_home or study_end}</b> da boshlanadi va kechqurungacha davom etadi.")
        elif study_end <= now_hm < (return_home or study_end):
            lines.append("🏠 <b>Hozirgi holat:</b> O'qish/ish tugagan, uyga qaytish vaqti.")
            lines.append(f"🟢 Uyga yetib borgach (soat <b>{return_home}</b> dan boshlab) to'liq bo'sh bo'lasiz.")
        elif now_hm >= "23:00":
            lines.append("😴 <b>Hozirgi holat:</b> Rejadagi dam olish va uyqu vaqti.")
        else:
            lines.append("🟢 <b>Hozirgi holat:</b> Siz hozir bo'sh vaqtingizdasiz!")
            lines.append(f"Sizda <b>{now_hm}</b> dan boshlab kechki dam olishgacha erkin vaqt mavjud. Kurslar, amaliyot yoki sevimli loyihalaringiz bilan shug'ullanishingiz mumkin.")
    else:
        lines.append(f"💡 Bugungi asosiy bo'sh vaqtingiz: <b>{free_time}</b>.")

    return "\n".join(lines), build_schedule_action_keyboard()

# ─────────────────────────────────────────────────────────────────────────────
# KELGUSIDA VAKANSIYA ISH VAQTINI JADVAL BILAN TAQQOSLASH (COMPATIBILITY API)
# ─────────────────────────────────────────────────────────────────────────────

def time_to_minutes(time_str):
    """'HH:MM' formatidagi vaqtni daqiqalarga o'tkazadi."""
    if not time_str:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str.strip())
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None

def check_job_schedule_match(job_start_time, job_end_time, job_days=None, is_remote=False):
    """
    Vakansiyadagi ish vaqtini foydalanuvchining jadvali bilan solishtiradi.

    Parametrlar:
      - job_start_time: '14:00' yoki '09:00'
      - job_end_time: '18:00'
      - job_days: ['monday', 'tuesday', ...] yoki None (standart: Dushanba-Juma)
      - is_remote: True / False (agar remote bo'lsa yo'l vaqti hisoblanmaydi)

    Qaytaradi:
      dict: {
        "is_compatible": True/False,
        "conflict_count": int,
        "conflicts": list of dicts,
        "match_percentage": int,
        "summary_uz": str
      }
    """
    sched = load_schedule()
    days_data = sched.get("days", {})

    check_days = job_days if job_days else ["monday", "tuesday", "wednesday", "thursday", "friday"]

    j_start_min = time_to_minutes(normalize_time_str(job_start_time))
    j_end_min = time_to_minutes(normalize_time_str(job_end_time))

    if j_start_min is None or j_end_min is None:
        return {
            "is_compatible": True,
            "conflict_count": 0,
            "conflicts": [],
            "match_percentage": 100,
            "summary_uz": "Vakansiya ish vaqti erkin yoki aniq soatlarsiz ko'rsatilgan. Mos deb qabul qilindi."
        }

    conflicts = []
    total_checked = len(check_days)

    for d_key in check_days:
        day_sched = days_data.get(d_key, {})
        day_name = DAYS_UZ.get(d_key, d_key)

        if day_sched.get("is_day_off"):
            continue

        study_work = day_sched.get("study_work")
        if study_work and "-" in study_work:
            parts = study_work.split("-")
            u_start_min = time_to_minutes(normalize_time_str(parts[0]))
            u_end_min = time_to_minutes(normalize_time_str(parts[1]))

            # Agar yo'l vaqti kerak bo'lsa (on-site ish uchun qaytish vaqti olinadi)
            if not is_remote and day_sched.get("return_home"):
                ret_min = time_to_minutes(normalize_time_str(day_sched.get("return_home")))
                if ret_min and ret_min > u_end_min:
                    u_end_min = ret_min

            if u_start_min is not None and u_end_min is not None:
                # Kesishma (overlap) mavjudligini tekshirish
                overlap_start = max(j_start_min, u_start_min)
                overlap_end = min(j_end_min, u_end_min)

                if overlap_start < overlap_end:
                    overlap_hours = round((overlap_end - overlap_start) / 60, 1)
                    conflicts.append({
                        "day_key": d_key,
                        "day_name": day_name,
                        "user_busy": study_work,
                        "job_time": f"{job_start_time} - {job_end_time}",
                        "overlap_hours": overlap_hours
                    })

    conflict_count = len(conflicts)
    is_compatible = (conflict_count == 0)
    match_percentage = int(((total_checked - conflict_count) / max(total_checked, 1)) * 100)

    if is_compatible:
        summary_uz = (
            f"✅ <b>Vaqt bo'yicha to'liq mos keladi ({match_percentage}%):</b>\n"
            f"Vakansiya vaqti (<code>{job_start_time}–{job_end_time}</code>) "
            f"sizning o'qish/ish jadvalingiz bilan to'qnashmaydi. Bo'sh vaqtingizga to'liq to'g'ri keladi!"
        )
    else:
        conflict_days_str = ", ".join([c["day_name"] for c in conflicts])
        max_overlap = max([c["overlap_hours"] for c in conflicts]) if conflicts else 0
        summary_uz = (
            f"⚠️ <b>Vaqt to'qnashuvi aniqlandi ({conflict_count} ta kunda to'qnashuv, moslik {match_percentage}%):</b>\n"
            f"To'qnashuv kunlari: <b>{conflict_days_str}</b>\n"
            f"Kunda taxminan <b>{max_overlap} soat</b> o'qishingiz bilan ustma-ust tushadi.\n"
            f"💡 <i>Tavsiya: Vakansiyani part-time yoki kechki/masofaviy (Remote) formatda kelishish mumkinligini surishtiring.</i>"
        )

    return {
        "is_compatible": is_compatible,
        "conflict_count": conflict_count,
        "conflicts": conflicts,
        "match_percentage": match_percentage,
        "summary_uz": summary_uz
    }

def get_free_hours_summary():
    """Hafta kunlari bo'yicha bo'sh vaqtlar umumiy tahlili."""
    sched = load_schedule()
    days = sched.get("days", {})
    summary = {}
    for d_key in DAYS_ORDER:
        d_val = days.get(d_key, {})
        summary[d_key] = {
            "day_name": DAYS_UZ.get(d_key, d_key),
            "is_day_off": d_val.get("is_day_off", False),
            "free_time": d_val.get("free_time", "Belgilanmagan")
        }
    return summary
