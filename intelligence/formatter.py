# -*- coding: utf-8 -*-
"""
formatter.py - Intelligence xabarlarini formatlash moduli
"""

def format_matched_vacancy_notification(match_result, source_title="Kanal", post_link=""):
    """
    Vakansiya moslik tahlili natijasidan foydalanuvchiga yuboriladigan
    yuqori aniqlikdagi, chiroyli Telegram xabari va inline tugmalari.
    Faqat 90+ va 75+ ballik postlar uchun mo'ljallangan.
    """
    score = match_result.get("overall_score", 0)
    v = match_result.get("vacancy_summary", {})
    c = match_result.get("criteria", {})

    # Sarlavha
    if score >= 90:
        header = "🔥 <b>Senga juda mos vakansiya</b>"
    else:
        header = "🟢 <b>Senga mos vakansiya</b>"

    title = v.get("title") or "Vakansiya"
    company = v.get("company") or "Ko'rsatilmagan"
    location = v.get("location") or "Toshkent"
    work_fmt = v.get("work_format")
    if work_fmt and work_fmt.lower() not in location.lower() and work_fmt != "Office":
        location = f"{location} ({work_fmt})"

    hours = v.get("working_hours") or "Ko'rsatilmagan"
    salary = v.get("salary") or "Kelishiladi"
    exp_short = v.get("experience_required") or "0–1 yil"

    # "Nega mos:" bandlarini shakllantirish
    reasons = []

    # 1. Qiziqish / Soha
    matched_interests = c.get("interest", {}).get("matched_interests", [])
    if matched_interests:
        clean_ints = [i.split("(")[0].strip() for i in matched_interests[:2]]
        reasons.append(f"• {' / '.join(clean_ints)}")
    else:
        reasons.append("• Cybersecurity / IT yo'nalishi")

    # 2. Vaqt jadvali
    sched_info = c.get("schedule", {})
    if not sched_info.get("has_conflict"):
        if "14:00" in hours or "13:00" in hours or "erkin" in hours.lower() or "part-time" in hours.lower():
            reasons.append("• O‘qishdan keyingi vaqtga mos")
        else:
            reasons.append("• O‘qish jadvalingiz bilan to'qnashuv yo'q")

    # 3. Joylashuv
    if "remote" in location.lower() or "masofaviy" in location.lower():
        reasons.append("• Masofaviy (Remote)")
    elif "toshkent" in location.lower():
        reasons.append("• Toshkent")
    else:
        reasons.append(f"• {location}")

    # 4. Tajriba / Daraja
    if any(k in title.lower() or k in exp_short.lower() for k in ["intern", "stajyor", "trainee"]):
        reasons.append("• Junior/Intern")
    elif "junior" in title.lower() or "1 yil" in exp_short.lower() or "0-1" in exp_short:
        reasons.append("• Junior/Intern (0–1 yil)")
    else:
        reasons.append("• Tajriba talabi mos")

    # 5. Skilllar
    matched_skills = c.get("skills", {}).get("matching_skills", [])
    if matched_skills:
        clean_skills = [s.split("[")[0].strip() for s in matched_skills[:3]]
        reasons.append(f"• Ko'nikmalar: {', '.join(clean_skills)}")

    lines = [
        f"{header}\n",
        f"💼 <b>{title}</b>",
        f"🏢 <b>Kompaniya:</b> {company}",
        f"📍 <b>{location}</b>",
        f"🕐 <b>{hours}</b>",
        f"💰 <b>{salary}</b>",
        f"🎓 <b>Tajriba:</b> {exp_short}\n",
        "<b>Nega mos:</b>\n"
    ]
    lines.extend(reasons)

    # Havola (Link)
    link_url = post_link or v.get("link")
    if link_url and (link_url.startswith("http") or link_url.startswith("https")):
        lines.append(f"\n🔗 <a href='{link_url}'>Original link</a> ({source_title})")
    elif link_url and link_url.startswith("@"):
        lines.append(f"\n🔗 <b>Aloqa:</b> {link_url} ({source_title})")
    elif post_link:
        lines.append(f"\n🔗 <a href='{post_link}'>Original link</a> ({source_title})")
    else:
        lines.append(f"\n📢 <b>Manba:</b> {source_title}")

    text = "\n".join(lines)

    # Inline feedback buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👍 Foydali", "callback_data": "intel_fb_like"},
                {"text": "👎 Keraksiz", "callback_data": "intel_fb_dislike"}
            ],
            [
                {"text": "🚫 Bu manbani o'chir", "callback_data": "intel_src_mute"}
            ]
        ]
    }
    return text, keyboard


def format_intelligence_message(analysis_data, source_title="Kanal", post_link=""):
    """
    Umumiy ta'lim, grant yoki konferensiya e'lonlari uchun chiroyli Telegram xabari.
    Faqat 90+ va 75+ ballik postlar uchun yuboriladi.
    """
    score = analysis_data.get("relevance_score", 0)

    if score >= 90:
        badge = "🔥 <b>Senga juda mos imkoniyat</b>"
    else:
        badge = "🟢 <b>Senga mos imkoniyat</b>"

    title = analysis_data.get("title", "Muhim imkoniyat")
    company = analysis_data.get("company", "Ko'rsatilmagan")
    location = analysis_data.get("location", "Toshkent / Masofaviy")
    salary = analysis_data.get("salary", "Ko'rsatilmagan")
    exp = analysis_data.get("experience_required", "0–1 yil (Talabalar)")
    reqs = analysis_data.get("key_requirements", "")
    deadline = analysis_data.get("deadline", "Ko'rsatilmagan")
    why_list = analysis_data.get("why_matches", [])

    lines = [
        f"{badge} ({score}%)\n",
        f"🎯 <b>{title}</b>",
        f"🏢 <b>Tashkilot:</b> {company}",
        f"📍 <b>Joy:</b> {location}"
    ]

    if salary and salary != "Ko'rsatilmagan":
        lines.append(f"💰 <b>Maosh/Grant:</b> {salary}")
    if exp and exp != "Ko'rsatilmagan":
        lines.append(f"🧑‍💻 <b>Tajriba:</b> {exp}")
    if reqs:
        lines.append(f"📚 <b>Talablar:</b> {reqs}")
    if deadline and deadline != "Ko'rsatilmagan":
        lines.append(f"⏰ <b>Muddati:</b> {deadline}")

    if why_list:
        lines.append("\n<b>Nega mos:</b>")
        for w in why_list[:4]:
            lines.append(f"• {w}")

    if post_link:
        lines.append(f"\n🔗 <a href='{post_link}'>Original link</a> ({source_title})")
    else:
        lines.append(f"\n📢 <b>Manba:</b> {source_title}")

    text = "\n".join(lines)

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👍 Foydali", "callback_data": "intel_fb_like"},
                {"text": "👎 Keraksiz", "callback_data": "intel_fb_dislike"}
            ],
            [
                {"text": "🚫 Bu manbani o'chir", "callback_data": "intel_src_mute"}
            ]
        ]
    }
    return text, keyboard


def format_digest_message(date_str, stats_dict, top_items):
    """
    Kunlik xulosa (Daily Digest) xabarini formatlaydi.
    """
    lines = []
    lines.append(f"📊 <b>BUGUNGI INTELLIGENCE XULOSASI ({date_str})</b>\n")
    for cat, count in stats_dict.items():
        if count > 0:
            lines.append(f"• {cat}: {count} ta")

    if top_items:
        lines.append("\n⭐ <b>Eng asosiy topilmalar:</b>")
        for idx, item in enumerate(top_items[:5], 1):
            lines.append(f"{idx}. <b>{item.get('title', 'Imkoniyat')}</b> ({item.get('company', '')}) - {item.get('link', '')}")
    else:
        lines.append("\nBugun yangi muhim e'lonlar chiqmadi.")

    return "\n".join(lines)
