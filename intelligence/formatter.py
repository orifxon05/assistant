def format_intelligence_message(analysis_data, source_title="Kanal", post_link=""):
    """
    Tahlil qilingan post ma'lumotlaridan chiroyli va qulay Telegram xabari va inline tugmalarini shakllantiradi.
    """
    level = analysis_data.get("level", "USEFUL")
    score = analysis_data.get("relevance_score", 0)

    if level == "URGENT":
        badge = "🔥 JUDA MOS"
    elif level == "USEFUL":
        badge = "🟢 MOS"
    else:
        badge = "🟡 EHTIMOL FOYDALI"

    title = analysis_data.get("title", "Muhim imkoniyat")
    company = analysis_data.get("company", "Ko'rsatilmagan")
    location = analysis_data.get("location", "Toshkent / Masofaviy")
    salary = analysis_data.get("salary", "Ko'rsatilmagan")
    exp = analysis_data.get("experience_required", "0–1 yil (Talabalar)")
    reqs = analysis_data.get("key_requirements", "")
    deadline = analysis_data.get("deadline", "Ko'rsatilmagan")
    why_list = analysis_data.get("why_matches", [])
    drawbacks = analysis_data.get("drawbacks", "")

    lines = []
    lines.append(f"{badge} | {title}")
    lines.append(f"🏢 <b>Kompaniya:</b> {company}")
    lines.append(f"📍 <b>Joy:</b> {location}")
    lines.append(f"💰 <b>Maosh:</b> {salary}")
    lines.append(f"🧑‍💻 <b>Tajriba talabi:</b> {exp}")
    if reqs:
        lines.append(f"📚 <b>Asosiy talablar:</b> {reqs}")
    if deadline and deadline != "Ko'rsatilmagan":
        lines.append(f"⏰ <b>Muddati (Deadline):</b> {deadline}")

    if why_list:
        lines.append("\n💡 <b>Nega sizga mos:</b>")
        for w in why_list:
            lines.append(f"• {w}")

    advice = analysis_data.get("action_advice", "")
    if advice:
        lines.append(f"\n🧠 <b>Jarvis xulosasi va maslahati:</b>\n{advice}")

    if drawbacks:
        lines.append(f"\n⚠️ <b>E'tibor bering:</b> {drawbacks}")

    if post_link:
        lines.append(f"\n🔗 <a href='{post_link}'>Original postni ko'rish ({source_title})</a>")
    else:
        lines.append(f"\n📢 <b>Manba:</b> {source_title}")

    text = "\n".join(lines)

    # Inline feedback buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👍 Foydali", "callback_data": f"intel_fb_like"},
                {"text": "👎 Keraksiz", "callback_data": f"intel_fb_dislike"}
            ],
            [
                {"text": "🚫 Bu manbani o'chir", "callback_data": f"intel_src_mute"}
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
