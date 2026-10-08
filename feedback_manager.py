# -*- coding: utf-8 -*-
"""
feedback_manager.py - Jarvis Opportunity Feedback va Dinamik Filtrlash Tizimi

Modul vazifalari:
1. Har bir yuborilgan opportunity (vakansiya, kurs, grant va h.k.) uchun:
   - ✅ Kerak
   - ❌ Kerak emas
   - ⭐ Juda foydali
   feedback tugmalarini ta'minlash va ularni qayd qilish.
2. Barcha feedback ma'lumotlarini `feedback.json` faylida saqlash:
   - Ro'yxatdan o'tgan opportunity'lar keshi (registered_items)
   - Tarix (history)
   - Mavzular bo'yicha dinamik vaznlar (topic_weights)
   - Ustuvorligi oshirilgan kalit so'zlar (boosted_keywords)
   - Filtrlangan / kamaytirilgan kalit so'zlar (disliked_keywords)
3. Keyingi filtering jarayonida feedback'ni hisobga olish:
   - "Bu turdagi SOC vakansiyalarini ko'proq yubor" -> SOC priority oshadi (bonus +15..+20 ball, 🔥 90+ darajaga chiqish).
   - "Bu turdagi vakansiyalar kerak emas" -> priority kamayadi (penalty -25..-40 ball), filtr kuchayadi va <75 bo'lib tushib qoladi.
4. Foydalanuvchining tasdig'isiz asosiy profillarni (personal_profile.json, skills_profile.json va h.k.)
   keskin o'zgartirmasdan, faqat feedback.json orqali aqlli boshqaruv.
"""

import os
import re
import json
import hashlib
from datetime import datetime

FEEDBACK_FILE = "feedback.json"

DEFAULT_FEEDBACK_DATA = {
    "version": "1.0",
    "updated_at": "",
    "stats": {
        "total_feedbacks": 0,
        "kerak_count": 0,
        "kerak_emas_count": 0,
        "juda_foydali_count": 0
    },
    "boosted_keywords": [
        "soc", "siem", "cybersecurity", "kiberxavfsizlik", "incident response"
    ],
    "disliked_keywords": [],
    "topic_weights": {
        "soc": {"bonus": 15, "penalty": 0, "status": "high_priority", "count": 1},
        "siem": {"bonus": 12, "penalty": 0, "status": "high_priority", "count": 1},
        "cybersecurity": {"bonus": 10, "penalty": 0, "status": "boosted", "count": 1}
    },
    "registered_items": {},
    "history": []
}

COMMON_TECH_TOPICS = [
    # Cybersecurity
    "soc", "siem", "pentest", "edr", "xdr", "dlp", "ueba", "incident response",
    "network security", "cloud security", "malware", "antifraud", "threat intelligence",
    "kiberxavfsizlik", "cybersecurity", "devsecops", "infosec", "red team", "blue team",
    # Dasturlash va Texnologiyalar
    "python", "linux", "git", "sql", "docker", "fastapi", "django", "bash", "networking",
    "backend", "frontend", "react", "vue", "angular", "node", "javascript", "golang", "java",
    "devops", "kubernetes", "ci/cd", "1c", "php", "flutter",
    # Rollar / Darajalar
    "intern", "internship", "stajyor", "trainee", "junior", "middle", "senior",
    # Ta'lim
    "bootcamp", "kurs", "grant", "scholarship", "hackathon", "sertifikat"
]


def load_feedback_data():
    """
    feedback.json faylidan ma'lumotlarni o'qiydi.
    Agar fayl bo'lmasa, standart tuzilmani yaratadi.
    """
    if not os.path.exists(FEEDBACK_FILE):
        data = DEFAULT_FEEDBACK_DATA.copy()
        data["updated_at"] = datetime.now().isoformat()
        save_feedback_data(data)
        return data

    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Standart maydonlar mavjudligini kafolatlash
        for key, val in DEFAULT_FEEDBACK_DATA.items():
            if key not in data:
                data[key] = val
        return data
    except Exception as e:
        print(f"[FEEDBACK] Yuklashda xatolik: {e}")
        return DEFAULT_FEEDBACK_DATA.copy()


def save_feedback_data(data):
    """
    feedback.json fayliga ma'lumotlarni saqlaydi.
    """
    try:
        data["updated_at"] = datetime.now().isoformat()
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[FEEDBACK] Saqlashda xatolik: {e}")
        return False


def extract_opportunity_topics(title="", skills=None, full_text="", category=""):
    """
    Imkoniyat matni, lavozim va ko'nikmalardan asosiy kalit so'zlar/mavzularni ajratib oladi.
    """
    combined = f"{title} {category} {full_text} ".lower()
    if skills:
        if isinstance(skills, list):
            combined += " ".join(str(s) for s in skills).lower()
        else:
            combined += str(skills).lower()

    found = set()

    for topic in COMMON_TECH_TOPICS:
        # Regex orqali so'z chegarasi bilan qidirish
        pattern = r"\b" + re.escape(topic) + r"\b"
        if re.search(pattern, combined):
            found.add(topic)

    # Agar maxsus rol lavozim nomida bo'lsa, uni ham qo'shish
    if title:
        title_lower = title.lower()
        for word in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9+#]+", title_lower):
            if len(word) >= 3 and word in COMMON_TECH_TOPICS:
                found.add(word)

    return sorted(list(found))


def register_opportunity(title, company="", category="", skills=None, source="", score=0, link="", raw_text=""):
    """
    Yuborilayotgan opportunity'ni keshga ro'yxatga oladi va uning qisqa ID sini qaytaradi.
    Har bir yuborilgan xabardagi tugma shu ID orqali postni taniydi.
    """
    data = load_feedback_data()
    reg = data.setdefault("registered_items", {})

    # Qisqa va yagona ID yaratish (masalan: opp_8a3f91)
    raw_hash_src = f"{title}_{company}_{link}_{datetime.now().timestamp()}".encode("utf-8")
    short_hash = hashlib.md5(raw_hash_src).hexdigest()[:6]
    opp_id = f"opp_{short_hash}"

    topics = extract_opportunity_topics(title=title, skills=skills, full_text=raw_text, category=category)

    reg[opp_id] = {
        "id": opp_id,
        "title": title or "Imkoniyat",
        "company": company or "Noma'lum",
        "category": category or "Umumiy",
        "topics": topics,
        "source": source or "Kanal",
        "score": score,
        "link": link,
        "created_at": datetime.now().isoformat()
    }

    # Kesh hajmini so'nggi 150 ta bilan cheklash (ortiqcha yuklama bo'lmasligi uchun)
    if len(reg) > 150:
        sorted_keys = sorted(reg.keys(), key=lambda k: reg[k].get("created_at", ""))
        for old_k in sorted_keys[:-150]:
            reg.pop(old_k, None)

    save_feedback_data(data)
    return opp_id


def build_feedback_keyboard(opp_id):
    """
    Telegram inline keyboard yaratadi:
    [ ✅ Kerak ] [ ❌ Kerak emas ]
    [ ⭐ Juda foydali ]
    """
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Kerak", "callback_data": f"fb_k:{opp_id}"},
                {"text": "❌ Kerak emas", "callback_data": f"fb_x:{opp_id}"}
            ],
            [
                {"text": "⭐ Juda foydali", "callback_data": f"fb_s:{opp_id}"}
            ]
        ]
    }


def get_last_registered_opportunity():
    """
    Oxirgi yuborilgan opportunity'ni qaytaradi.
    Foydalanuvchi "Bu turdagi vakansiyalar kerak emas" deb aniq nom aytmasa ishlatiladi.
    """
    data = load_feedback_data()
    reg = data.get("registered_items", {})
    if not reg:
        return None
    sorted_items = sorted(reg.values(), key=lambda x: x.get("created_at", ""), reverse=True)
    return sorted_items[0] if sorted_items else None


def record_opportunity_feedback(opp_id, action_code, feedback_source="button", user_note=""):
    """
    Foydalanuvchi feedback berganda feedback.json ga saqlaydi va
    mavzular bo'yicha vaznlarni qayta hisoblaydi.

    action_code:
      - 'k' yoki 'kerak' -> ✅ Kerak
      - 'x' yoki 'kerak_emas' -> ❌ Kerak emas
      - 's' yoki 'juda_foydali' -> ⭐ Juda foydali
    """
    data = load_feedback_data()
    reg = data.get("registered_items", {})
    history = data.setdefault("history", [])
    weights = data.setdefault("topic_weights", {})
    boosted = data.setdefault("boosted_keywords", [])
    disliked = data.setdefault("disliked_keywords", [])
    stats = data.setdefault("stats", {
        "total_feedbacks": 0, "kerak_count": 0, "kerak_emas_count": 0, "juda_foydali_count": 0
    })

    # Opportunity ma'lumotlarini olish
    item = reg.get(opp_id)
    if not item:
        # Fallback: oxirgi postni tekshirish
        item = get_last_registered_opportunity()

    item_title = item.get("title", "Vakansiya / Imkoniyat") if item else "Vakansiya"
    item_topics = item.get("topics", []) if item else []
    if not item_topics and item:
        item_topics = extract_opportunity_topics(title=item_title, full_text=item.get("category", ""))

    # Harakat turini normallashtirish
    action = "kerak"
    if action_code in ["s", "juda_foydali", "star"]:
        action = "juda_foydali"
    elif action_code in ["x", "kerak_emas", "dislike"]:
        action = "kerak_emas"
    else:
        action = "kerak"

    # Mavzularni yangilash
    affected_topics = item_topics if item_topics else ["umumiy"]

    if action == "juda_foydali":
        stats["total_feedbacks"] += 1
        stats["juda_foydali_count"] += 1
        for top in affected_topics:
            t = top.lower()
            if t not in boosted:
                boosted.append(t)
            if t in disliked:
                disliked.remove(t)
            cur = weights.setdefault(t, {"bonus": 0, "penalty": 0, "status": "normal", "count": 0})
            cur["bonus"] = min(25, cur.get("bonus", 0) + 15)
            cur["penalty"] = max(0, cur.get("penalty", 0) - 10)
            cur["status"] = "high_priority"
            cur["count"] = cur.get("count", 0) + 1

        response_msg = (
            f"⭐ <b>Juda foydali deb belgilandi!</b>\n\n"
            f"🎯 <b>{item_title}</b> bo‘yicha ustuvorlik (priority) maksimal oshirildi.\n"
            f"Kelgusida aynan shu turdagi (<b>{', '.join(affected_topics)}</b>) vakansiyalar birinchi navbatda va ko‘proq yetkaziladi."
        )

    elif action == "kerak":
        stats["total_feedbacks"] += 1
        stats["kerak_count"] += 1
        for top in affected_topics:
            t = top.lower()
            if t not in boosted:
                boosted.append(t)
            if t in disliked:
                disliked.remove(t)
            cur = weights.setdefault(t, {"bonus": 0, "penalty": 0, "status": "normal", "count": 0})
            cur["bonus"] = min(20, cur.get("bonus", 0) + 7)
            cur["penalty"] = max(0, cur.get("penalty", 0) - 5)
            cur["status"] = "boosted"
            cur["count"] = cur.get("count", 0) + 1

        response_msg = (
            f"✅ <b>Qabul qilindi: Kerak</b>\n\n"
            f"📌 <b>{item_title}</b> kabi e'lonlar sizga maqbul deb qayd etildi.\n"
            f"Ushbu yo'nalish (<b>{', '.join(affected_topics)}</b>) uchun saralash ustuvorligi oshirildi."
        )

    else:  # kerak_emas
        stats["total_feedbacks"] += 1
        stats["kerak_emas_count"] += 1
        for top in affected_topics:
            t = top.lower()
            if t not in disliked:
                disliked.append(t)
            if t in boosted:
                boosted.remove(t)
            cur = weights.setdefault(t, {"bonus": 0, "penalty": 0, "status": "normal", "count": 0})
            cur["penalty"] = min(50, cur.get("penalty", 0) + 30)
            cur["bonus"] = max(0, cur.get("bonus", 0) - 15)
            cur["status"] = "suppressed"
            cur["count"] = cur.get("count", 0) + 1

        response_msg = (
            f"❌ <b>Belgilandi: Kerak emas</b>\n\n"
            f"🚫 <b>{item_title}</b> turidagi e'lonlar uchun ustuvorlik keskin kamaytirildi va filtrlash kuchaytirildi.\n"
            f"Kelgusida bu kabi postlar (<b>{', '.join(affected_topics)}</b>) sizni bezovta qilmasligi uchun o'tkazib yuboriladi."
        )

    # Tarixga qo'shish
    history_entry = {
        "id": f"fb_{int(datetime.now().timestamp())}",
        "item_id": opp_id,
        "title": item_title,
        "action": action,
        "affected_topics": affected_topics,
        "source": feedback_source,
        "user_note": user_note,
        "timestamp": datetime.now().isoformat()
    }
    history.append(history_entry)
    data["history"] = history[-200:]  # Oxirgi 200 ta yozuv

    save_feedback_data(data)
    return True, response_msg, affected_topics


def record_topic_adjustment(topic, action="boost", note=""):
    """
    Foydalanuvchi matnli ko'rinishda buyruq berganda (masalan: 'SOC ni ko'proq yubor'
    yoki 'frontend kerak emas') feedback.json ni moslashtiradi.
    """
    data = load_feedback_data()
    boosted = data.setdefault("boosted_keywords", [])
    disliked = data.setdefault("disliked_keywords", [])
    weights = data.setdefault("topic_weights", {})
    history = data.setdefault("history", [])

    clean_topic = topic.strip().lower()

    if action in ["boost", "ko'proq", "juda_foydali", "oshir"]:
        if clean_topic not in boosted:
            boosted.append(clean_topic)
        if clean_topic in disliked:
            disliked.remove(clean_topic)
        cur = weights.setdefault(clean_topic, {"bonus": 0, "penalty": 0, "status": "normal", "count": 0})
        cur["bonus"] = min(25, cur.get("bonus", 0) + 15)
        cur["penalty"] = 0
        cur["status"] = "high_priority"
        cur["count"] = cur.get("count", 0) + 1

        msg = (
            f"🎯 <b>{topic.upper()} bo‘yicha ustuvorlik oshirildi!</b>\n\n"
            f"Keyingi filtrlashda {topic.upper()} yo‘nalishidagi vakansiyalar ko‘proq va "
            f"birinchi navbatda (🔥 90+ ball bilan) yetkaziladi."
        )
    else:  # reduce / dislike / kerak_emas
        if clean_topic not in disliked:
            disliked.append(clean_topic)
        if clean_topic in boosted:
            boosted.remove(clean_topic)
        cur = weights.setdefault(clean_topic, {"bonus": 0, "penalty": 0, "status": "normal", "count": 0})
        cur["penalty"] = min(50, cur.get("penalty", 0) + 35)
        cur["bonus"] = 0
        cur["status"] = "suppressed"
        cur["count"] = cur.get("count", 0) + 1

        msg = (
            f"🚫 <b>{topic.upper()} uchun ustuvorlik kamaytirildi!</b>\n\n"
            f"Filtrlash qat'iylashtirildi. Ushbu turdagi vakansiyalar keyingi tahlillarda o‘tkazib yuboriladi."
        )

    history.append({
        "id": f"fb_txt_{int(datetime.now().timestamp())}",
        "item_id": "manual_text",
        "title": f"Mavzu: {clean_topic}",
        "action": action,
        "affected_topics": [clean_topic],
        "source": "text_command",
        "user_note": note,
        "timestamp": datetime.now().isoformat()
    })
    data["history"] = history[-200:]
    save_feedback_data(data)

    return True, msg, clean_topic


def apply_feedback_adjustments(item_title="", skills=None, full_text="", category="", base_score=75):
    """
    Vakansiya yoki imkoniyat balliga feedback.json asosida bonus yoki jazo (penalty) qo'llaydi.

    Qaytaradi:
      dict: {
        "final_score": int,
        "bonus": int,
        "penalty": int,
        "reasons": list,
        "is_suppressed": bool
      }
    """
    data = load_feedback_data()
    boosted = data.get("boosted_keywords", [])
    disliked = data.get("disliked_keywords", [])
    weights = data.get("topic_weights", {})

    topics = extract_opportunity_topics(title=item_title, skills=skills, full_text=full_text, category=category)
    combined_str = f"{item_title} {category} {full_text} {' '.join(skills or [])}".lower()

    bonus = 0
    penalty = 0
    reasons = []
    is_suppressed = False

    # 1. Boosted tekshiruvi (⭐ Juda foydali yoki ✅ Kerak)
    for b in boosted:
        b_clean = b.lower()
        if b_clean in topics or (len(b_clean) >= 3 and b_clean in combined_str):
            w_bonus = weights.get(b_clean, {}).get("bonus", 10)
            if w_bonus > bonus:
                bonus = w_bonus
            reasons.append(f"Siz ma'qullagan yo'nalish ({b_clean.upper()} ⭐)")

    # 2. Disliked tekshiruvi (❌ Kerak emas)
    for d in disliked:
        d_clean = d.lower()
        if d_clean in topics or (len(d_clean) >= 3 and d_clean in combined_str):
            w_penalty = weights.get(d_clean, {}).get("penalty", 30)
            if w_penalty > penalty:
                penalty = w_penalty
            is_suppressed = True
            reasons.append(f"Kerak emas deb belgilangan ({d_clean.upper()})")

    # Ballni hisoblash
    calc_score = base_score + bonus - penalty

    # Agar jiddiy kerak emas deb belgilangan bo'lsa (penalty >= 25),
    # qat'iy ravishda 75 dan past qilib tushiramiz, toki yuborilmasin!
    if is_suppressed and penalty >= 25:
        calc_score = min(calc_score, 40)

    final_score = max(0, min(100, calc_score))

    return {
        "final_score": final_score,
        "bonus": bonus,
        "penalty": penalty,
        "reasons": list(dict.fromkeys(reasons)),  # duplicates olib tashlanadi
        "is_suppressed": is_suppressed
    }


def process_natural_language_feedback(user_message):
    """
    Foydalanuvchining chatdagi xabarlarini tahlil qilib, feedback ekanligini aniqlaydi.
    Masalan:
      - "Bu turdagi SOC vakansiyalarini ko‘proq yubor"
      - "Bu turdagi vakansiyalar kerak emas"
      - "SOC vakansiyalarini ko'proq yubor"
      - "Frontend vakansiyalari kerak emas"
    """
    if not user_message:
        return False, None

    msg = user_message.strip()
    msg_lower = msg.lower()

    # 1. Boost naqshlari (ko'proq yubor, priority oshsin, ko'paytir, kerak)
    boost_triggers = [
        "ko'proq yubor", "ko‘proq yubor", "koproq yubor",
        "ko'proq kerak", "ko‘proq kerak", "koproq kerak",
        "ko'proq tashla", "ko‘proq tashla", "koproq tashla",
        "priority oshsin", "ustuvorlikni oshir", "ustuvorlik oshsin",
        "ko'paytir", "kopaytir", "ko'proq bo'lsin"
    ]

    # 2. Reduce/Dislike naqshlari (kerak emas, yuborma, kamaytir, yoqmadi)
    reduce_triggers = [
        "kerak emas", "keremas", "yuborma", "tashlama",
        "keragi yo'q", "keragi yoq", "kamaytir", "filtr kuchaysin",
        "filter kuchaysin", "yoqmadi", "qiziq emas"
    ]

    has_boost = any(trig in msg_lower for trig in boost_triggers)
    has_reduce = any(trig in msg_lower for trig in reduce_triggers)

    if not has_boost and not has_reduce:
        return False, None

    # Topic qidirish
    detected_topic = None
    for topic in COMMON_TECH_TOPICS:
        if re.search(r"\b" + re.escape(topic) + r"\b", msg_lower):
            detected_topic = topic
            break

    # Agar maxsus mavzu nomi aytilmagan bo'lsa (masalan "Bu turdagi vakansiyalar kerak emas")
    if not detected_topic:
        if "bu turdagi" in msg_lower or "shu turdagi" in msg_lower or "bunday" in msg_lower:
            last_item = get_last_registered_opportunity()
            if last_item:
                last_topics = last_item.get("topics", [])
                if last_topics:
                    detected_topic = last_topics[0]
                else:
                    detected_topic = last_item.get("title", "vakansiya")

    if not detected_topic:
        # Xabardan umumiy kalit so'zlarni ajratishga urinish
        words = re.findall(r"[a-zA-Zа-яА-ЯёЁ]{3,}", msg_lower)
        filter_words = {"vakansiya", "vakansiyalar", "post", "postlar", "turdagi", "yubor", "kerak", "emas"}
        candidate_words = [w for w in words if w not in filter_words]
        if candidate_words:
            detected_topic = candidate_words[0]

    if not detected_topic:
        detected_topic = "oxirgi_vakansiya"

    action = "boost" if has_boost else "reduce"
    _, reply_msg, _ = record_topic_adjustment(detected_topic, action=action, note=msg)
    return True, reply_msg


def get_feedback_summary_text():
    """
    Foydalanuvchiga hozirgi feedback holati va ustuvorliklarini ko'rsatish uchun chiroyli matn.
    """
    data = load_feedback_data()
    boosted = data.get("boosted_keywords", [])
    disliked = data.get("disliked_keywords", [])
    weights = data.get("topic_weights", {})
    stats = data.get("stats", {})

    b_lines = []
    for b in boosted:
        w = weights.get(b, {}).get("bonus", 10)
        status = weights.get(b, {}).get("status", "boosted")
        badge = "⭐ Yuqori ustuvorlik" if status == "high_priority" else "✅ Ma'qullangan"
        b_lines.append(f"• <b>{b.upper()}</b> — {badge} (+{w} ball)")

    d_lines = []
    for d in disliked:
        p = weights.get(d, {}).get("penalty", 30)
        d_lines.append(f"• <b>{d.upper()}</b> — 🚫 Filtrlangan (-{p} ball)")

    lines = [
        "📊 <b>Jarvis Opportunity Feedback Tizimi</b>\n",
        f"Jami bildirilgan fikrlar: <b>{stats.get('total_feedbacks', 0)}</b> ta",
        f"• ⭐ Juda foydali: {stats.get('juda_foydali_count', 0)} ta",
        f"• ✅ Kerak: {stats.get('kerak_count', 0)} ta",
        f"• ❌ Kerak emas: {stats.get('kerak_emas_count', 0)} ta\n",
        "🎯 <b>Ustuvor yo'nalishlar (ko'proq yuboriladi):</b>"
    ]

    if b_lines:
        lines.extend(b_lines)
    else:
        lines.append("<i>Hozircha belgilanmagan.</i>")

    lines.append("\n🚫 <b>Filtrlangan yo'nalishlar (o'tkazib yuboriladi):</b>")
    if d_lines:
        lines.extend(d_lines)
    else:
        lines.append("<i>Hozircha cheklovlar yo'q.</i>")

    lines.append("\n💡 <i>Fikr bildirish uchun xabarlardagi tugmalarni bosing yoki 'SOC ko'proq yubor', 'Frontend kerak emas' deb yozing.</i>")

    return "\n".join(lines)
