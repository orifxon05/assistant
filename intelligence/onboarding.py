import json
from .config import load_user_profile, save_user_profile

ONBOARDING_STATES = {}  # {chat_id: {"step": 1, "data": {...}}}

def start_onboarding_quiz(chat_id):
    ONBOARDING_STATES[chat_id] = {"step": 1, "data": {}}
    text = (
        "🎯 <b>Shaxsiy Qiziqishlar va Monitoring Testi</b>\n\n"
        "Kanallar va guruhlardagi yuzlab postlar ichidan faqat <b>sizga eng mos va qimmatli</b> "
        "vakansiya, kurs yoki grantlarni saralashim uchun quyidagi qisqa testdan o'ting.\n\n"
        "<b>1-savol:</b> Asosiy qiziqqan IT yo'nalishingiz qaysi?"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🛡 Axborot xavfsizligi (Cybersecurity)", "callback_data": "ob_field_cyber"}],
            [{"text": "🐍 Python / Backend dasturlash", "callback_data": "ob_field_python"}],
            [{"text": "🤖 AI, Data Science & ML", "callback_data": "ob_field_ai"}],
            [{"text": "🌐 Frontend / Fullstack dasturlash", "callback_data": "ob_field_web"}],
            [{"text": "📱 Mobile (Flutter / Android / iOS)", "callback_data": "ob_field_mobile"}],
            [{"text": "💻 Umumiy IT / Boshqa soha", "callback_data": "ob_field_other"}]
        ]
    }
    return text, keyboard

def handle_onboarding_callback(chat_id, data):
    state = ONBOARDING_STATES.get(chat_id)
    if not state:
        return None, None

    step = state.get("step", 1)

    # ─── 1-QADAM: Soha / Yo'nalish ───
    if step == 1 and data.startswith("ob_field_"):
        field_code = data.replace("ob_field_", "")
        field_map = {
            "cyber": {
                "field": "Cybersecurity / Axborot xavfsizligi",
                "p_dirs": ["Cybersecurity", "SOC", "Incident Response", "Pentest", "SIEM", "Network Security", "Security Analyst"],
                "s_dirs": ["Python", "Linux", "Networking", "DevOps"]
            },
            "python": {
                "field": "Python / Backend dasturlash",
                "p_dirs": ["Python", "Django", "FastAPI", "PostgreSQL", "Backend API", "Telegram Bot", "Docker"],
                "s_dirs": ["Linux", "Git", "Redis", "Celery", "AI Integration"]
            },
            "ai": {
                "field": "AI & Data Science",
                "p_dirs": ["AI Engineering", "Machine Learning", "LLM", "Deep Learning", "Data Analysis", "Python AI", "NLP"],
                "s_dirs": ["Python", "FastAPI", "PyTorch", "Prompt Engineering"]
            },
            "web": {
                "field": "Frontend / Fullstack",
                "p_dirs": ["JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Fullstack"],
                "s_dirs": ["TailwindCSS", "Git", "REST API"]
            },
            "mobile": {
                "field": "Mobile dasturlash",
                "p_dirs": ["Flutter", "Dart", "Android", "iOS", "Swift", "Kotlin", "Mobile App"],
                "s_dirs": ["REST API", "Firebase", "Git"]
            },
            "other": {
                "field": "Umumiy IT va Dasturlash",
                "p_dirs": ["IT", "Dasturlash", "Kompyuter savodxonligi", "Texnologiya"],
                "s_dirs": ["Boshlang'ich kurslar", "Karyera"]
            }
        }
        info = field_map.get(field_code, field_map["cyber"])
        state["data"]["primary_field"] = info["field"]
        state["data"]["primary_directions"] = info["p_dirs"]
        state["data"]["secondary_directions"] = info["s_dirs"]
        state["step"] = 2

        text = "<b>2-savol:</b> Sizga asosan qanday imkoniyatlar kerak?"
        keyboard = {
            "inline_keyboard": [
                [{"text": "💼 Faqat Ish va Vakansiyalar", "callback_data": "ob_opp_job"}],
                [{"text": "🎓 Internship va Shogirdlik (Amaliyot)", "callback_data": "ob_opp_intern"}],
                [{"text": "📚 Bepul IT Kurslar, Bootcamp va Ta'lim", "callback_data": "ob_opp_course"}],
                [{"text": "🎁 Grantlar, Stipendiyalar & Xakatonlar", "callback_data": "ob_opp_grant"}],
                [{"text": "⚡ Barchasi (Ish, Kurs, Grant, Amaliyot)", "callback_data": "ob_opp_all"}]
            ]
        }
        return text, keyboard

    # ─── 2-QADAM: Imkoniyat turlari ───
    elif step == 2 and data.startswith("ob_opp_"):
        opp_code = data.replace("ob_opp_", "")
        opp_map = {
            "job": ["Junior", "Entry-level", "Full-time", "Part-time", "Vakansiya", "Ish"],
            "intern": ["Internship", "Trainee", "Shogirdlik", "Talabalar uchun dastur", "Amaliyot"],
            "course": ["Bepul kurs", "Bootcamp", "IT sertifikat", "Online kurs", "Ta'lim dasturi"],
            "grant": ["Grant", "Stipendiya", "Hackathon", "Musobaqa", "Xalqaro dastur"],
            "all": ["Internship", "Trainee", "Junior", "Vakansiya", "Kurs", "Bootcamp", "Grant", "Hackathon"]
        }
        state["data"]["opportunity_types"] = opp_map.get(opp_code, opp_map["all"])
        state["step"] = 3

        text = "<b>3-savol:</b> Hozirgi tajriba darajangiz yoki maomingiz qanday?"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎓 Talaba / 0 tajriba (boshlovchi)", "callback_data": "ob_exp_student"}],
                [{"text": "🧑‍💻 Junior (0–1 yil tajriba)", "callback_data": "ob_exp_junior"}],
                [{"text": "💼 Middle (1–3 yil tajriba)", "callback_data": "ob_exp_middle"}],
                [{"text": "🚀 Senior (3+ yil tajriba)", "callback_data": "ob_exp_senior"}]
            ]
        }
        return text, keyboard

    # ─── 3-QADAM: Tajriba darajasi ───
    elif step == 3 and data.startswith("ob_exp_"):
        exp_code = data.replace("ob_exp_", "")
        exp_map = {
            "student": {
                "allowed": ["No experience", "0 years", "0-1 years", "Student", "Intern", "Trainee", "Shogird", "Talaba"],
                "status": "Talaba"
            },
            "junior": {
                "allowed": ["0-1 years", "Junior", "Entry-level", "Intern"],
                "status": "Junior mutaxassis"
            },
            "middle": {
                "allowed": ["1-3 years", "Middle", "Mutaxassis"],
                "status": "Middle mutaxassis"
            },
            "senior": {
                "allowed": ["3+ years", "Senior", "Lead"],
                "status": "Senior mutaxassis"
            }
        }
        exp_info = exp_map.get(exp_code, exp_map["student"])
        state["data"]["allowed_experience"] = exp_info["allowed"]
        state["data"]["status"] = exp_info["status"]
        state["step"] = 4

        text = "<b>4-savol:</b> Asosiy joylashuvingiz va qulay ish shakli?"
        keyboard = {
            "inline_keyboard": [
                [{"text": "📍 Toshkent (Ofis / Gibrid)", "callback_data": "ob_loc_tashkent"}],
                [{"text": "🌐 Masofaviy (Faqat Remote)", "callback_data": "ob_loc_remote"}],
                [{"text": "🇺🇿 O'zbekiston viloyatlari", "callback_data": "ob_loc_uzb"}],
                [{"text": "✈️ Global / Xorij (Masofaviy yoki Relokatsiya)", "callback_data": "ob_loc_global"}]
            ]
        }
        return text, keyboard

    # ─── 4-QADAM: Joylashuv va Saqlash ───
    elif step == 4 and data.startswith("ob_loc_"):
        loc_code = data.replace("ob_loc_", "")
        loc_map = {
            "tashkent": "Toshkent, O'zbekiston",
            "remote": "Remote / Masofaviy",
            "uzb": "O'zbekiston viloyatlari",
            "global": "Global / Xorij"
        }
        state["data"]["primary_location"] = loc_map.get(loc_code, "Toshkent, O'zbekiston")
        state["data"]["allow_remote"] = True
        state["data"]["allow_uzbekistan"] = True
        state["data"]["allow_global_online"] = (loc_code in ["remote", "global"])
        state["data"]["onboarding_completed"] = True

        prof = load_user_profile()
        prof.update(state["data"])
        save_user_profile(prof)

        del ONBOARDING_STATES[chat_id]

        opp_str = ", ".join(prof.get("opportunity_types", [])[:3])
        text = (
            "🎉 <b>Qiziqishlaringiz muvaffaqiyatli saqlandi!</b>\n\n"
            f"• <b>Soha:</b> {prof.get('primary_field')}\n"
            f"• <b>Daraja:</b> {prof.get('status')}\n"
            f"• <b>Izlanayotgan:</b> {opp_str}...\n"
            f"• <b>Joylashuv:</b> {prof.get('primary_location')}\n\n"
            "🔍 Endi Telegramdagi <b>'📂 Intelligence'</b> papkasiga qiziqqan kanallaringizni qo'shing. "
            "Jarvis ularni muntazam kuzatib boradi va har bir e'lon uchun <b>aqlli xulosa va maslahatlar</b> beradi!"
        )
        menu_btn = {
            "inline_keyboard": [
                [{"text": "📊 Kanallarni hozir tahlil qilish", "callback_data": "run_full_analysis"}],
                [{"text": "📂 Asosiy menyu", "callback_data": "open_menu"}]
            ]
        }
        return text, menu_btn

    return None, None
