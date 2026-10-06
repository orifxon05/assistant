# -*- coding: utf-8 -*-
"""
location_transport.py - Jarvis Location & Transport Module

Modul vazifalari:
1. Foydalanuvchining joylashuv va transport profilini boshqarish:
   - Asosiy shahar (city)
   - Mahalla / tuman (district)
   - Remotega munosabat (remote)
   - Hybridga munosabat (hybrid)
   - On-sitega munosabat (onsite)
   - Maksimal yo'l vaqti (max_commute_minutes)
   - Qaysi transportlardan foydalanishi (transport_modes)
2. Barcha ma'lumotlarni `location_profile.json` faylida saqlash.
3. Asosiy buyruqlar:
   - "Manzilimni ko'rsat" / "Joylashuvimni ko'rsat"
   - "Manzilimni o'zgartir" / "Joylashuvimni o'zgartir"
4. Kelgusida vakansiya joylashuvi va ish formatini solishtirish uchun
   moslashuvchan taqqoslash (compatibility) API'si.
   (Hozircha xarita yoki route hisoblash kiritilmaydi).
"""

import os
import re
import json
from datetime import datetime

LOCATION_FILE = "location_profile.json"

POPULAR_CITIES = [
    "Toshkent", "Samarqand", "Farg'ona", "Andijon", "Namangan",
    "Buxoro", "Qarshi", "Navoiy", "Urganch", "Jizzax", "Nukus", "Termiz"
]

TASHKENT_DISTRICTS = [
    "Shayxontohur", "Yunusobod", "Chilonzor", "Mirzo Ulug'bek",
    "Yakkasaroy", "Mirobod", "Olmazor", "Uchtepa", "Yashnobod",
    "Sergeli", "Bektemir", "Yangihayot"
]

TRANSPORT_OPTIONS = [
    "Metro",
    "Avtobus",
    "Yandex Go (Taksi)",
    "Shaxsiy mashina",
    "Piyoda",
    "Samokat / Velosiped"
]

def get_default_location_profile():
    """Standart boshlang'ich joylashuv profili."""
    return {
        "city": "Toshkent",
        "district": "Shayxontohur",
        "remote": "Ha",
        "hybrid": "Ha",
        "onsite": "Ha",
        "max_commute_minutes": 60,
        "transport_modes": ["Metro", "Avtobus", "Yandex Go (Taksi)"],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_configured": False
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# JSON FAYLNI O'QISH VA SAQLASH
# ─────────────────────────────────────────────────────────────────────────────

def load_location_profile():
    """location_profile.json faylini o'qiydi. Fayl yo'q bo'lsa standart shablonni qaytaradi."""
    if not os.path.exists(LOCATION_FILE):
        default_data = get_default_location_profile()
        save_location_profile(default_data)
        return default_data
    try:
        with open(LOCATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Yetishmayotgan kalitlarni to'ldirish
            defaults = get_default_location_profile()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"[LOCATION] Faylni o'qishda xatolik: {e}")
        return get_default_location_profile()

def save_location_profile(data):
    """location_profile.json fayliga ma'lumotlarni saqlaydi."""
    try:
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["updated_at"] = datetime.now().isoformat()
        with open(LOCATION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[LOCATION] Saqlashda xatolik: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MATNDAN JOYLASHUV VA TRANSPORT MA'LUMOTLARINI AJRATISH (SMART PARSER)
# ─────────────────────────────────────────────────────────────────────────────

def parse_location_input(raw_text):
    """
    Foydalanuvchi yozgan ixtiyoriy matndan joylashuv va transport parametrlarini ajratadi.
    Masalan:
    'Toshkent, Shayxontohur. Maksimal yo'l 60 daqiqa, Remote Ha, Hybrid Ha. Metro va avtobus'
    """
    text = raw_text.strip()
    text_lower = text.lower()
    prof = load_location_profile()

    # 1. Shaharni aniqlash
    for city in POPULAR_CITIES:
        if city.lower() in text_lower:
            prof["city"] = city
            break

    # 2. Tumanni aniqlash
    for dist in TASHKENT_DISTRICTS:
        if dist.lower() in text_lower:
            prof["district"] = dist
            break

    # Agar boshqa tuman kiritilgan bo'lsa (masalan: 'Chilonzor tumani', 'Yunusobod mavzesi')
    dist_match = re.search(r"([A-Za-z'ʻ`ʼ]+)\s*(?:tumani|mahalla|massiv|tumanida)", text, re.IGNORECASE)
    if dist_match:
        prof["district"] = dist_match.group(1).capitalize()

    # 3. Maksimal yo'l vaqti (daqiqalarda)
    commute_match = re.search(r"(\d{1,3})\s*(?:daqiqa|minut|min|daq)", text_lower)
    if commute_match:
        prof["max_commute_minutes"] = int(commute_match.group(1))
    else:
        hour_match = re.search(r"(\d{1,2}(?:\.5)?)\s*soat", text_lower)
        if hour_match:
            prof["max_commute_minutes"] = int(float(hour_match.group(1)) * 60)

    # 4. Remote munosabat
    if "remote" in text_lower or "masofaviy" in text_lower:
        if any(w in text_lower for w in ["remote yo'q", "remote emas", "masofaviy yo'q"]):
            prof["remote"] = "Yo'q"
        elif any(w in text_lower for w in ["remote afzal", "remote juda ma'qul"]):
            prof["remote"] = "Ha (Afzal)"
        else:
            prof["remote"] = "Ha"

    # 5. Hybrid munosabat
    if "hybrid" in text_lower or "gibrid" in text_lower:
        if any(w in text_lower for w in ["hybrid yo'q", "gibrid yo'q", "hybrid emas"]):
            prof["hybrid"] = "Yo'q"
        elif any(w in text_lower for w in ["hybrid afzal", "gibrid afzal"]):
            prof["hybrid"] = "Ha (Afzal)"
        else:
            prof["hybrid"] = "Ha"

    # 6. Onsite munosabat
    if "onsite" in text_lower or "ofis" in text_lower or "ofisda" in text_lower:
        if any(w in text_lower for w in ["onsite yo'q", "ofis yo'q", "ofisda yo'q"]):
            prof["onsite"] = "Yo'q"
        elif any(w in text_lower for w in ["faqat yaqin", "yaqin bo'lsa"]):
            prof["onsite"] = "Faqat yaqin bo'lsa"
        else:
            prof["onsite"] = "Ha"

    # 7. Transport turlari
    detected_transports = []
    if "metro" in text_lower:
        detected_transports.append("Metro")
    if "avtobus" in text_lower:
        detected_transports.append("Avtobus")
    if any(w in text_lower for w in ["taksi", "taxi", "yandex"]):
        detected_transports.append("Yandex Go (Taksi)")
    if any(w in text_lower for w in ["mashina", "avtomobil", "shaxsiy mashina"]):
        detected_transports.append("Shaxsiy mashina")
    if "piyoda" in text_lower:
        detected_transports.append("Piyoda")
    if any(w in text_lower for w in ["samokat", "velosiped", "velo"]):
        detected_transports.append("Samokat / Velosiped")

    if detected_transports:
        prof["transport_modes"] = detected_transports

    prof["metadata"]["is_configured"] = True
    save_location_profile(prof)
    return prof

# ─────────────────────────────────────────────────────────────────────────────
# INTERAKTIV SOZLASH SESSIYALARI (LOCATION_SESSIONS)
# ─────────────────────────────────────────────────────────────────────────────

LOCATION_SESSIONS = {}

def is_in_location_setup(chat_id):
    """Foydalanuvchi joylashuv sozlash jarayonidami?"""
    return chat_id in LOCATION_SESSIONS

def cancel_location_setup(chat_id):
    """Joylashuv sozlashni bekor qilish."""
    if chat_id in LOCATION_SESSIONS:
        del LOCATION_SESSIONS[chat_id]
        return True
    return False

def start_location_setup(chat_id):
    """Joylashuv sozlashni 1-bosqichdan boshlaydi."""
    LOCATION_SESSIONS[chat_id] = {
        "step": 1,
        "data": load_location_profile()
    }
    return get_location_step_prompt(chat_id)

def get_location_step_prompt(chat_id):
    """Joriy bosqich savoli va inline tugmalarini qaytaradi."""
    session = LOCATION_SESSIONS.get(chat_id)
    if not session:
        return "Sessiya topilmadi.", None

    step = session.get("step", 1)

    # ─── 1-BOSQICH: Asosiy shahar ───
    if step == 1:
        text = (
            "📍 <b>1/5: Asosiy shahar</b>\n\n"
            "Qaysi shaharda istiqomat qilasiz yoki asosan qayerda ish qidiryapsiz?\n"
            "<i>(Tugmalardan tanlang yoki shahar nomini yozing)</i>"
        )
        keyboard = [
            [
                {"text": "Toshkent", "callback_data": "loc_set_city_Toshkent"},
                {"text": "Samarqand", "callback_data": "loc_set_city_Samarqand"}
            ],
            [
                {"text": "Farg'ona", "callback_data": "loc_set_city_Farg'ona"},
                {"text": "Andijon", "callback_data": "loc_set_city_Andijon"},
                {"text": "Namangan", "callback_data": "loc_set_city_Namangan"}
            ],
            [
                {"text": "Buxoro", "callback_data": "loc_set_city_Buxoro"},
                {"text": "Qarshi", "callback_data": "loc_set_city_Qarshi"},
                {"text": "Navoiy", "callback_data": "loc_set_city_Navoiy"}
            ],
            [
                {"text": "❌ Bekor qilish", "callback_data": "loc_cancel"}
            ]
        ]
        return text, {"inline_keyboard": keyboard}

    # ─── 2-BOSQICH: Tuman / Mahalla ───
    if step == 2:
        city = session["data"].get("city", "Toshkent")
        text = (
            f"🏘 <b>2/5: Tuman yoki mahalla ({city})</b>\n\n"
            "Shaharning qaysi tumani yoki mahallasida yashaysiz?\n"
            "<i>(Masalan: Shayxontohur, Chilonzor, Yunusobod...)</i>"
        )
        keyboard = []
        if city == "Toshkent":
            keyboard = [
                [
                    {"text": "Shayxontohur", "callback_data": "loc_set_dist_Shayxontohur"},
                    {"text": "Yunusobod", "callback_data": "loc_set_dist_Yunusobod"}
                ],
                [
                    {"text": "Chilonzor", "callback_data": "loc_set_dist_Chilonzor"},
                    {"text": "Mirzo Ulug'bek", "callback_data": "loc_set_dist_Mirzo Ulug'bek"}
                ],
                [
                    {"text": "Yakkasaroy", "callback_data": "loc_set_dist_Yakkasaroy"},
                    {"text": "Mirobod", "callback_data": "loc_set_dist_Mirobod"}
                ],
                [
                    {"text": "Olmazor", "callback_data": "loc_set_dist_Olmazor"},
                    {"text": "Uchtepa", "callback_data": "loc_set_dist_Uchtepa"}
                ],
                [
                    {"text": "Yashnobod", "callback_data": "loc_set_dist_Yashnobod"},
                    {"text": "Sergeli", "callback_data": "loc_set_dist_Sergeli"}
                ]
            ]
        keyboard.append([{"text": "⏩ O'tkazish", "callback_data": "loc_skip_step"}])
        return text, {"inline_keyboard": keyboard}

    # ─── 3-BOSQICH: Ish formatlariga munosabat ───
    if step == 3:
        cur_rem = session["data"].get("remote", "Ha")
        cur_hyb = session["data"].get("hybrid", "Ha")
        cur_ons = session["data"].get("onsite", "Ha")
        text = (
            "🏢 <b>3/5: Ish formatlariga munosabat</b>\n\n"
            f"• 🏠 <b>Remote (Masofaviy):</b> {cur_rem}\n"
            f"• 🔄 <b>Hybrid (Gibrid):</b> {cur_hyb}\n"
            f"• 🏢 <b>On-site (Ofis):</b> {cur_ons}\n\n"
            "Kerakli variantni o'zgartirish uchun quyidagi tugmalarni bosing:"
        )
        keyboard = [
            [
                {"text": f"Remote: {cur_rem}", "callback_data": "loc_toggle_remote"},
                {"text": f"Hybrid: {cur_hyb}", "callback_data": "loc_toggle_hybrid"}
            ],
            [
                {"text": f"On-site: {cur_ons}", "callback_data": "loc_toggle_onsite"}
            ],
            [
                {"text": "➡️ Keyingi bosqich", "callback_data": "loc_next_step"}
            ]
        ]
        return text, {"inline_keyboard": keyboard}

    # ─── 4-BOSQICH: Maksimal yo'l vaqti ───
    if step == 4:
        text = (
            "⏱ <b>4/5: Maksimal yo'l vaqti</b>\n\n"
            "Ofisga (ishga) borish uchun bir tomonga ko'pi bilan necha daqiqa yo'l bosishga tayyorsiz?\n"
            "<i>(Masalan: 60 daqiqa)</i>"
        )
        keyboard = [
            [
                {"text": "30 daqiqa", "callback_data": "loc_set_commute_30"},
                {"text": "45 daqiqa", "callback_data": "loc_set_commute_45"}
            ],
            [
                {"text": "60 daqiqa (1 soat)", "callback_data": "loc_set_commute_60"},
                {"text": "90 daqiqa", "callback_data": "loc_set_commute_90"}
            ],
            [
                {"text": "120 daqiqa (2 soat)", "callback_data": "loc_set_commute_120"}
            ]
        ]
        return text, {"inline_keyboard": keyboard}

    # ─── 5-BOSQICH: Transport turlari ───
    if step == 5:
        chosen = session["data"].get("transport_modes", [])
        text = (
            "🚇 <b>5/5: Qaysi transportlardan foydalanasiz?</b>\n\n"
            "Kerakli transport vositalarini tanlang (bir nechtasini belgilash mumkin):\n"
            f"📌 <b>Tanlandi:</b> {', '.join(chosen) if chosen else 'Hech narsa tanlanmagan'}"
        )
        keyboard = []
        for opt in TRANSPORT_OPTIONS:
            is_sel = opt in chosen
            prefix = "✅ " if is_sel else "➕ "
            keyboard.append([{"text": f"{prefix}{opt}", "callback_data": f"loc_tgl_tr_{opt}"}])
        keyboard.append([
            {"text": "💾 Saqlash va yakunlash", "callback_data": "loc_finish_setup"}
        ])
        return text, {"inline_keyboard": keyboard}

    return "Yakunlandi.", None

def process_location_input(chat_id, user_text):
    """Foydalanuvchi yuborgan matnni qabul qilib, joriy bosqich qiymatini saqlash."""
    session = LOCATION_SESSIONS.get(chat_id)
    if not session:
        return None, None

    step = session.get("step", 1)
    text_clean = user_text.strip()

    # 1-bosqich: Shahar nomi yozilsa
    if step == 1:
        session["data"]["city"] = text_clean.capitalize()
        session["step"] = 2
        return get_location_step_prompt(chat_id)

    # 2-bosqich: Tuman nomi yozilsa
    if step == 2:
        session["data"]["district"] = text_clean.capitalize()
        session["step"] = 3
        return get_location_step_prompt(chat_id)

    # 3-bosqich: Ish formati
    if step == 3:
        session["step"] = 4
        return get_location_step_prompt(chat_id)

    # 4-bosqich: Yo'l vaqti (raqam yoki soat)
    if step == 4:
        m = re.search(r"\d+", text_clean)
        if m:
            val = int(m.group(0))
            if "soat" in text_clean.lower() and val <= 4:
                val = val * 60
            session["data"]["max_commute_minutes"] = val
        session["step"] = 5
        return get_location_step_prompt(chat_id)

    # 5-bosqich: Transport
    if step == 5:
        # Vergul bilan yozilgan bo'lsa
        parts = [p.strip() for p in text_clean.split(",") if p.strip()]
        if parts:
            session["data"]["transport_modes"] = parts
        return finalize_location_setup(chat_id)

    return get_location_step_prompt(chat_id)

def finalize_location_setup(chat_id):
    """Barcha ma'lumotlarni location_profile.json fayliga yozib yakunlaydi."""
    session = LOCATION_SESSIONS.pop(chat_id, None)
    if not session:
        return "Sessiya topilmadi.", None

    prof = session.get("data", {})
    prof["metadata"]["is_configured"] = True
    save_location_profile(prof)

    text = (
        "🎉 <b>Joylashuv va transport profili muvaffaqiyatli saqlandi!</b>\n"
        "Barcha ma'lumotlar <code>location_profile.json</code> fayliga yozildi.\n\n"
        f"{format_location_view(prof)}"
    )
    return text, build_location_action_keyboard()

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER (loc_ PREFIKSI BILAN)
# ─────────────────────────────────────────────────────────────────────────────

def handle_location_callback(chat_id, data):
    """Inline tugmalardan kelgan loc_ callback'larni boshqarish."""
    # ─── BEKOR QILISH ───
    if data == "loc_cancel":
        cancel_location_setup(chat_id)
        return "❌ Joylashuv sozlash bekor qilindi.", {"inline_keyboard": [[{"text": "📍 Manzilimni ko'rsat", "callback_data": "loc_view"}]]}

    # ─── MANZILNI KO'RSATISH ───
    if data == "loc_view":
        prof = load_location_profile()
        return format_location_view(prof), build_location_action_keyboard()

    # ─── TAHRIRLASHNI BOSHLASH ───
    if data == "loc_start_setup":
        return start_location_setup(chat_id)

    # ─── O'TKAZIB YUBORISH ───
    if data == "loc_skip_step":
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            session["step"] += 1
            return get_location_step_prompt(chat_id)

    # ─── KEYINGI BOSQICH ───
    if data == "loc_next_step":
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            session["step"] += 1
            return get_location_step_prompt(chat_id)

    # ─── SHAHARNI TANLASH (loc_set_city_NAME) ───
    if data.startswith("loc_set_city_"):
        city_name = data.replace("loc_set_city_", "")
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            session["data"]["city"] = city_name
            session["step"] = 2
            return get_location_step_prompt(chat_id)

    # ─── TUMANNI TANLASH (loc_set_dist_NAME) ───
    if data.startswith("loc_set_dist_"):
        dist_name = data.replace("loc_set_dist_", "")
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            session["data"]["district"] = dist_name
            session["step"] = 3
            return get_location_step_prompt(chat_id)

    # ─── REMOTE NI ALMASHTIRISH ───
    if data == "loc_toggle_remote":
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            cur = session["data"].get("remote", "Ha")
            cycle = {"Ha": "Ha (Afzal)", "Ha (Afzal)": "Yo'q", "Yo'q": "Ha"}
            session["data"]["remote"] = cycle.get(cur, "Ha")
            return get_location_step_prompt(chat_id)

    # ─── HYBRID NI ALMASHTIRISH ───
    if data == "loc_toggle_hybrid":
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            cur = session["data"].get("hybrid", "Ha")
            cycle = {"Ha": "Ha (Afzal)", "Ha (Afzal)": "Yo'q", "Yo'q": "Ha"}
            session["data"]["hybrid"] = cycle.get(cur, "Ha")
            return get_location_step_prompt(chat_id)

    # ─── ONSITE NI ALMASHTIRISH ───
    if data == "loc_toggle_onsite":
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            cur = session["data"].get("onsite", "Ha")
            cycle = {"Ha": "Faqat yaqin bo'lsa", "Faqat yaqin bo'lsa": "Yo'q", "Yo'q": "Ha"}
            session["data"]["onsite"] = cycle.get(cur, "Ha")
            return get_location_step_prompt(chat_id)

    # ─── YO'L VAQTINI TANLASH (loc_set_commute_MINUTES) ───
    if data.startswith("loc_set_commute_"):
        mins = int(data.replace("loc_set_commute_", ""))
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            session["data"]["max_commute_minutes"] = mins
            session["step"] = 5
            return get_location_step_prompt(chat_id)

    # ─── TRANSPORT TURINI TOGGLE QILISH (loc_tgl_tr_NAME) ───
    if data.startswith("loc_tgl_tr_"):
        tr_name = data.replace("loc_tgl_tr_", "")
        session = LOCATION_SESSIONS.get(chat_id)
        if session:
            cur_modes = session["data"].setdefault("transport_modes", [])
            if tr_name in cur_modes:
                cur_modes.remove(tr_name)
            else:
                cur_modes.append(tr_name)
            return get_location_step_prompt(chat_id)

    # ─── YAKUNLASH ───
    if data == "loc_finish_setup":
        return finalize_location_setup(chat_id)

    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# PROFILNI KO'RSATISH VA TUGMALAR
# ─────────────────────────────────────────────────────────────────────────────

def format_location_view(prof=None):
    """Joylashuv va transport profilining chiroyli HTML ko'rinishi."""
    if not prof:
        prof = load_location_profile()

    city = prof.get("city") or "Toshkent"
    district = prof.get("district") or "Belgilanmagan"
    remote = prof.get("remote") or "Ha"
    hybrid = prof.get("hybrid") or "Ha"
    onsite = prof.get("onsite") or "Ha"
    commute = prof.get("max_commute_minutes", 60)
    transports = prof.get("transport_modes", [])
    trans_str = ", ".join(transports) if transports else "Belgilanmagan"

    lines = [
        "📍 <b>JARVIS — JOYLASHUV VA TRANSPORT PROFILI</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏙 <b>Asosiy shahar:</b> <code>{city}</code>",
        f"🏘 <b>Tuman / Mahalla:</b> <code>{district}</code>\n",
        "💼 <b>Ish formatlariga munosabat:</b>",
        f"  • 🏠 <b>Remote (Masofaviy):</b> {remote}",
        f"  • 🔄 <b>Hybrid (Gibrid):</b> {hybrid}",
        f"  • 🏢 <b>On-site (Ofis):</b> {onsite}\n",
        f"⏱ <b>Maksimal yo'l vaqti:</b> <code>{commute} daqiqa</code>",
        f"🚇 <b>Foydalanadigan transportlar:</b> <i>{trans_str}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 <i>Ushbu ma'lumotlar vakansiyalarning manzili va ish formatiga mos kelishini aniqlashda qo'llaniladi.</i>"
    ]
    return "\n".join(lines)

def build_location_action_keyboard():
    """Joylashuv profili ostidagi tezkor inline tugmalar."""
    return {
        "inline_keyboard": [
            [
                {"text": "✏️ Manzilimni o'zgartir", "callback_data": "loc_start_setup"},
                {"text": "📂 Asosiy menyu", "callback_data": "open_menu"}
            ]
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# KELGUSIDA VAKANSIYA MANZILINI SOLISHTIRISH (COMPATIBILITY API)
# ─────────────────────────────────────────────────────────────────────────────

def check_location_compatibility(job_city="Toshkent", job_district=None, job_format="On-site", estimated_commute_min=None):
    """
    Vakansiya joylashuvi va formatini foydalanuvchi profili bilan solishtiradi.
    (Hozircha real-time xarita yoki route hisoblash qilinmaydi, analitik solishtirish).

    Parametrlar:
      - job_city: Vakansiya shahri
      - job_district: Vakansiya joylashgan tuman
      - job_format: 'Remote', 'Hybrid', 'On-site' (Ofis)
      - estimated_commute_min: Taxminiy yo'l vaqti (agar ma'lum bo'lsa)

    Qaytaradi:
      dict: {
        "is_compatible": True/False,
        "match_level": "Full" / "Partial" / "No",
        "summary_uz": str
      }
    """
    prof = load_location_profile()
    u_city = (prof.get("city") or "Toshkent").lower()
    u_dist = (prof.get("district") or "").lower()
    u_rem = (prof.get("remote") or "Ha").lower()
    u_hyb = (prof.get("hybrid") or "Ha").lower()
    u_ons = (prof.get("onsite") or "Ha").lower()
    max_min = prof.get("max_commute_minutes", 60)

    j_fmt = (job_format or "On-site").lower()
    j_city = (job_city or "Toshkent").lower()
    j_dist = (job_district or "").lower()

    # 1. REMOTE
    if "remote" in j_fmt or "masofaviy" in j_fmt:
        if "yo'q" in u_rem or "emas" in u_rem:
            return {
                "is_compatible": False,
                "match_level": "No",
                "summary_uz": "⚠️ Vakansiya masofaviy (Remote), lekin profilingizda Remote ish xohlanmagan."
            }
        return {
            "is_compatible": True,
            "match_level": "Full",
            "summary_uz": "✅ <b>To'liq mos keladi:</b> Masofaviy (Remote) ish formati — joylashuv cheklovisiz sizga mos!"
        }

    # 2. HYBRID
    if "hybrid" in j_fmt or "gibrid" in j_fmt:
        if "yo'q" in u_hyb or "emas" in u_hyb:
            return {
                "is_compatible": False,
                "match_level": "No",
                "summary_uz": "⚠️ Vakansiya gibrid (Hybrid), lekin profilingizda gibrid format belgilanmagan."
            }
        if j_city and j_city != u_city:
            return {
                "is_compatible": False,
                "match_level": "No",
                "summary_uz": f"⚠️ Vakansiya boshqa shaharda ({job_city}) joylashgan. Sizning shahringiz: {prof.get('city')}."
            }
        return {
            "is_compatible": True,
            "match_level": "Full",
            "summary_uz": f"✅ <b>Gibrid mos keladi:</b> Vakansiya sizning shahringizda ({prof.get('city')}) va gibrid formatga rozisiz."
        }

    # 3. ON-SITE / OFIS
    if "yo'q" in u_ons or "emas" in u_ons:
        return {
            "is_compatible": False,
            "match_level": "No",
            "summary_uz": "⚠️ Vakansiya ofisda (On-site), lekin siz faqat masofaviy/gibrid formatlarni ko'rib chiqmoqdasiz."
        }

    if j_city and j_city != u_city:
        return {
            "is_compatible": False,
            "match_level": "No",
            "summary_uz": f"❌ <b>Boshqa shahar:</b> Vakansiya {job_city}da, siz esa {prof.get('city')}dasiz."
        }

    # Bir xil tuman bo'lsa
    if j_dist and u_dist and j_dist in u_dist:
        return {
            "is_compatible": True,
            "match_level": "Full",
            "summary_uz": f"✅ <b>Juda yaqin:</b> Vakansiya aynan sizning tumaningizda ({prof.get('district')}) joylashgan!"
        }

    # Yo'l vaqti hisoblangan bo'lsa
    if estimated_commute_min:
        if estimated_commute_min <= max_min:
            return {
                "is_compatible": True,
                "match_level": "Full",
                "summary_uz": f"✅ <b>Mos keladi:</b> Taxminiy yo'l vaqti (~{estimated_commute_min} daqiqa) sizning cheklovingizga ({max_min} daqiqa) to'g'ri keladi."
            }
        else:
            return {
                "is_compatible": False,
                "match_level": "Partial",
                "summary_uz": f"⚠️ <b>Uzoqroq:</b> Taxminiy yo'l vaqti (~{estimated_commute_min} daqiqa) sizning maksimal yo'l me'yoringizdan ({max_min} daqiqa) ko'proq."
            }

    return {
        "is_compatible": True,
        "match_level": "Full",
        "summary_uz": f"✅ <b>Mos keladi:</b> Vakansiya sizning shahringizda ({prof.get('city')}) joylashgan."
    }
