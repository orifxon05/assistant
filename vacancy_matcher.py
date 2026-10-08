# -*- coding: utf-8 -*-
"""
vacancy_matcher.py - Vakansiyani Shaxsiy Profil Bilan Solishtirish Moduli (Jarvis)

Ushbu modul vakansiya ma'lumotlarini (vacancy_data) foydalanuvchining 6 ta asosiy
profili bilan 7 ta mezon bo'yicha to'liq solishtiradi:

1. 🎯 Qiziqish (Interest Profile)
2. 🕐 Vaqt (Schedule & Free Time)
3. 📍 Joy (Location & Transport & Work Format)
4. 🎓 Tajriba (Experience & Education)
5. 💻 Skill (Technical Skills & Tools)
6. 💰 Maosh (Salary expectations)
7. 🚀 Karyera maqsadi (Career Goal)

Yakuniy natija:
🔥 Juda mos (score >= 80% va vaqt to'qnashuvi yo'q)
🟢 Mos (score >= 65% va vaqt to'qnashuvi yo'q)
🟡 Qisman mos (score >= 45%)
🔴 Mos emas (score < 45% yoki jiddiy vaqt to'qnashuvi mavjud)

Hozircha faqat tahlil natijasini struktura sifatida qaytaradi.
"""

import re
from datetime import datetime
from vacancy_analyzer import analyze_vacancy
from personal_profile import load_personal_profile
from personal_schedule import load_schedule
from location_transport import load_location_profile
from skills_profile import load_skills_profile

# ─────────────────────────────────────────────────────────────────────────────
# 1. VAQT VA DADQIQALARNI HISOBLASH YORDAMCHILARI
# ─────────────────────────────────────────────────────────────────────────────

def time_str_to_minutes(time_str):
    """'HH:MM' formatidagi vaqtni yarim kechadan boshlab daqiqalarga o'tkazadi."""
    if not time_str:
        return None
    time_clean = re.sub(r"[^\d:]", "", str(time_str).strip())
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_clean)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None

def parse_time_range(range_str):
    """'14:00 - 18:00' yoki '09:00–18:00' matnidan start va end daqiqalarini oladi."""
    if not range_str:
        return None, None
    m = re.search(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})", str(range_str))
    if m:
        s_min = time_str_to_minutes(m.group(1))
        e_min = time_str_to_minutes(m.group(2))
        return s_min, e_min
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# 2. 7 TA MEZON BO'YICHA YAKKA BAHOLASH FUNKSIYALARI
# ─────────────────────────────────────────────────────────────────────────────

def check_interest_match(vacancy_data, personal_profile):
    """
    1. 🎯 QIZIQISH (Interest Profile)
    Cybersecurity, SOC, SIEM, Python, Backend, AI va maqsadli sohalarni tekshiradi.
    """
    title = (vacancy_data.get("title") or vacancy_data.get("lavozim") or "").lower()
    raw_text = (vacancy_data.get("raw_text") or "").lower()
    skills = [s.lower() for s in (vacancy_data.get("skill_requirements") or vacancy_data.get("skill_talablari") or [])]
    company = (vacancy_data.get("company") or vacancy_data.get("kompaniya") or "").lower()

    interests = personal_profile.get("professional_interests", [])
    cyber_interests = personal_profile.get("cybersecurity_interests", [])
    industries = personal_profile.get("target_industries", [])

    all_user_interests = []
    # Qiziqishlarni yig'ish
    for it in (interests + cyber_interests):
        if isinstance(it, dict):
            name = it.get("name", "").strip()
            prio = it.get("priority", "HIGH")
            if name:
                all_user_interests.append((name, prio))
        elif isinstance(it, str) and it.strip():
            all_user_interests.append((it.strip(), "HIGH"))

    if not all_user_interests:
        # Standart qiziqishlar
        all_user_interests = [("Cybersecurity", "HIGH"), ("SOC", "HIGH"), ("SIEM", "HIGH"), ("Python", "MEDIUM")]

    matched_interests = []
    score_points = 0
    max_possible = 0

    for name, prio in all_user_interests:
        weight = 3 if prio == "HIGH" else (2 if prio == "MEDIUM" else 1)
        max_possible += weight
        n_low = name.lower()

        # Moslikni qidirish
        is_match = (n_low in title) or (n_low in raw_text) or any(n_low in s for s in skills)
        if is_match:
            score_points += weight
            matched_interests.append(f"{name} ({prio})")

    # Target industries (Bank, Fintech va h.k.)
    industry_matched = []
    for ind in industries:
        ind_name = ind.get("name", "") if isinstance(ind, dict) else str(ind)
        if ind_name and (ind_name.lower() in company or ind_name.lower() in raw_text):
            industry_matched.append(ind_name)
            score_points += 2

    if not matched_interests:
        return {
            "name": "🎯 Qiziqish",
            "status": "Mos emas",
            "score": 0,
            "matched_interests": [],
            "details": "Vakansiya axborot xavfsizligi yoki dasturlash sohangizga mos kelmaydi."
        }

    pct = int((score_points / max(max_possible, 1)) * 100) if max_possible > 0 else 50
    pct = min(100, max(40, pct))

    if pct >= 60:
        status = "Mos"
        details = f"Vakansiya profilingizdagi asosiy qiziqishlarga mos keladi: {', '.join(matched_interests[:4])}."
        if industry_matched:
            details += f" Soha ham mos: {', '.join(industry_matched)}."
    else:
        status = "Qisman mos"
        details = f"Vakansiya qisman sohangizga yaqin: {', '.join(matched_interests[:3])}."

    return {
        "name": "🎯 Qiziqish",
        "status": status,
        "score": pct,
        "matched_interests": matched_interests,
        "details": details
    }


def check_schedule_match(vacancy_data, schedule_data):
    """
    2. 🕐 VAQT (Schedule Match)
    O'qish/ish vaqti bilan vakansiya vaqti to'qnashuvini daqiqasigacha tekshiradi.
    Masalan:
    O'qish: 07:00–13:00, Vakansiya: 14:00–18:00 → vaqt mos.
    Vakansiya: 09:00–18:00 → 4 soat to'qnashadi.
    """
    v_hours = str(vacancy_data.get("working_hours") or vacancy_data.get("ish_vaqti") or "").strip()
    v_hours_lower = v_hours.lower()

    # Dushanba-Juma o'rtacha o'qish/ish soatlari
    days = schedule_data.get("days", {})
    mon = days.get("monday", {})
    study_work_str = mon.get("study_work") or "07:00 - 13:00"
    return_home = mon.get("return_home") or "13:00"

    u_study_start, u_study_end = parse_time_range(study_work_str)
    # Agar 07:00-13:00 topilmasa standart
    if u_study_start is None:
        u_study_start = 7 * 60
        u_study_end = 13 * 60

    u_free_start = time_str_to_minutes(return_home) or u_study_end

    # 1. Erkin grafik yoki moslashuvchan rejim
    if any(w in v_hours_lower for w in ["erkin grafik", "flexible", "moslashuvchan", "свободный"]):
        return {
            "name": "🕐 Vaqt",
            "status": "Mos",
            "score": 95,
            "has_conflict": False,
            "conflict_hours": 0,
            "details": f"Erkin/moslashuvchan ish grafigi. O'qishingizdan ({study_work_str}) so'ng erkin vaqtingizda ishlashingiz mumkin."
        }

    # 2. Vakansiya vaqtini aniqlash
    v_start, v_end = parse_time_range(v_hours)

    if v_start is not None and v_end is not None:
        # To'qnashuv daqiqalari: overlap between [v_start, v_end] and [u_study_start, u_study_end]
        overlap_start = max(v_start, u_study_start)
        overlap_end = min(v_end, u_study_end)
        overlap_min = max(0, overlap_end - overlap_start)

        if overlap_min > 0:
            # To'qnashuv mavjud!
            conflict_hrs = round(overlap_min / 60, 1)
            v_start_fmt = f"{v_start // 60:02d}:{v_start % 60:02d}"
            v_end_fmt = f"{v_end // 60:02d}:{v_end % 60:02d}"
            u_start_fmt = f"{u_study_start // 60:02d}:{u_study_start % 60:02d}"
            u_end_fmt = f"{u_study_end // 60:02d}:{u_study_end % 60:02d}"

            # To'qnashuv qanchalik katta?
            if conflict_hrs >= 2:
                status = "To'qnashadi"
                score = 0
            else:
                status = "Qisman to'qnashadi"
                score = 30

            return {
                "name": "🕐 Vaqt",
                "status": status,
                "score": score,
                "has_conflict": True,
                "conflict_hours": conflict_hrs,
                "user_study_work": study_work_str,
                "vacancy_hours": v_hours,
                "details": f"Vakansiya ({v_start_fmt}–{v_end_fmt}) o'qish vaqtingiz ({u_start_fmt}–{u_end_fmt}) bilan {conflict_hrs} soat to'qnashadi!"
            }
        else:
            # To'qnashuv yo'q!
            # O'qishdan keyin boshlanadimi?
            v_start_fmt = f"{v_start // 60:02d}:{v_start % 60:02d}"
            v_end_fmt = f"{v_end // 60:02d}:{v_end % 60:02d}"
            u_end_fmt = f"{u_study_end // 60:02d}:{u_study_end % 60:02d}"

            return {
                "name": "🕐 Vaqt",
                "status": "Mos",
                "score": 100,
                "has_conflict": False,
                "conflict_hours": 0,
                "user_study_work": study_work_str,
                "vacancy_hours": v_hours,
                "details": f"O'qish: {study_work_str}. Vakansiya: {v_start_fmt}–{v_end_fmt} → vaqt to'liq mos, bo'sh vaqtingizga to'g'ri keladi."
            }

    # 3. Vaqt aniq berilmagan bo'lsa (masalan faqat "Full-time" yoki "Ko'rsatilmagan")
    if "full-time" in v_hours_lower or "to'liq kun" in v_hours_lower or "полный" in v_hours_lower:
        return {
            "name": "🕐 Vaqt",
            "status": "Qisman mos",
            "score": 45,
            "has_conflict": True,
            "conflict_hours": 3,
            "details": f"Vakansiya to'liq kun (Full-time). Kunduzgi o'qish ({study_work_str}) bilan to'qnashishi ehtimoli yuqori."
        }
    elif "part-time" in v_hours_lower or "yarim kun" in v_hours_lower:
        return {
            "name": "🕐 Vaqt",
            "status": "Mos",
            "score": 85,
            "has_conflict": False,
            "conflict_hours": 0,
            "details": f"Yarim stavka (Part-time). O'qishdan keyingi bo'sh vaqtingizga moslashtirish mumkin."
        }

    return {
        "name": "🕐 Vaqt",
        "status": "Noma'lum",
        "score": 65,
        "has_conflict": False,
        "conflict_hours": 0,
        "details": "Vakansiyada aniq soatlar ko'rsatilmagan (suhbatda kelishish lozim)."
    }


def check_location_match(vacancy_data, location_profile):
    """
    3. 📍 JOY (Location & Transport & Work Format)
    Shahar, tuman va Remote/Hybrid/Office formatlarini tekshiradi.
    """
    u_city = (location_profile.get("city") or "Toshkent").lower()
    u_dist = (location_profile.get("district") or "").lower()
    u_rem = (location_profile.get("remote") or "Ha").lower()
    u_hyb = (location_profile.get("hybrid") or "Ha").lower()
    u_ons = (location_profile.get("onsite") or "Ha").lower()

    v_fmt = (vacancy_data.get("work_format") or vacancy_data.get("format") or "Office").lower()
    v_loc = (vacancy_data.get("location") or vacancy_data.get("joy") or "").lower()

    # 1. Remote (Masofaviy)
    if "remote" in v_fmt or "masofaviy" in v_fmt:
        if "yo'q" in u_rem:
            return {"name": "📍 Joy", "status": "Mos emas", "score": 25, "details": "Vakansiya Remote, lekin profilingizda masofaviy format rad etilgan."}
        return {"name": "📍 Joy", "status": "Mos", "score": 100, "details": "Masofaviy (Remote) ish — joylashuv cheklovisiz to'liq mos keladi."}

    # 2. Hybrid (Gibrid)
    if "hybrid" in v_fmt or "gibrid" in v_fmt:
        if u_city in v_loc or "toshkent" in v_loc or not v_loc or v_loc == "ko'rsatilmagan":
            return {"name": "📍 Joy", "status": "Mos", "score": 95, "details": f"Gibrid format ({location_profile.get('city')}). Qisman masofadan, qisman ofisdan ishlash qulay."}
        return {"name": "📍 Joy", "status": "Qisman mos", "score": 60, "details": f"Gibrid format, lekin boshqa shaharda ({vacancy_data.get('location')})."}

    # 3. Office (Ofis / On-site)
    if u_city in v_loc or "toshkent" in v_loc:
        # Tuman tekshiruvi
        if u_dist and u_dist in v_loc:
            return {"name": "📍 Joy", "status": "Mos", "score": 100, "details": f"Ofis o'zingizning tumaningizda joylashgan ({location_profile.get('district')}). Yo'l vaqti minimal."}
        return {"name": "📍 Joy", "status": "Mos", "score": 90, "details": f"Ofis shahringizda ({location_profile.get('city')}, {vacancy_data.get('location')}). Transport qulay (<60 daqiqa)."}
    elif not v_loc or v_loc == "ko'rsatilmagan":
        return {"name": "📍 Joy", "status": "Mos", "score": 80, "details": "Ofis manzili aniq yozilmagan, lekin shahar ichida bo'lishi ehtimoli yuqori."}
    else:
        return {"name": "📍 Joy", "status": "Mos emas", "score": 20, "details": f"Ofis boshqa hududda joylashgan ({vacancy_data.get('location')}). Sizning shahringiz: {location_profile.get('city')}."}


def check_experience_match(vacancy_data, skills_profile):
    """
    4. 🎓 TAJRIBA (Experience Match)
    Talab etilgan tajriba darajasini foydalanuvchi darajasi bilan solishtiradi.
    """
    v_exp = (vacancy_data.get("experience_required") or vacancy_data.get("tajriba_talabi") or "").lower()
    title = (vacancy_data.get("title") or vacancy_data.get("lavozim") or "").lower()

    u_exp_obj = skills_profile.get("experience", {})
    u_level = u_exp_obj.get("level", "Beginner") if isinstance(u_exp_obj, dict) else "Beginner"

    # Junior / Boshlovchi kalit so'zlari
    junior_keywords = ["junior", "stajyor", "trainee", "internship", "amaliyot", "boshlovchi", "0-1", "1 yil", "talab etilmaydi"]
    is_junior_job = any(k in v_exp or k in title for k in junior_keywords)

    senior_keywords = ["senior", "lead", "team lead", "bosh mutaxassis", "katta", "3+", "4+", "5+"]
    is_senior_job = any(k in v_exp or k in title for k in senior_keywords)

    middle_keywords = ["middle", "mid-level", "2-3", "2+", "kamida 2 yil"]
    is_middle_job = any(k in v_exp or k in title for k in middle_keywords)

    if is_senior_job:
        return {
            "name": "🎓 Tajriba",
            "status": "Mos emas",
            "score": 20,
            "details": f"Vakansiya Senior / 3+ yillik katta tajriba talab qiladi ({vacancy_data.get('experience_required')})."
        }
    elif is_middle_job:
        return {
            "name": "🎓 Tajriba",
            "status": "Qisman mos",
            "score": 55,
            "details": f"2+ yillik tajriba talab etiladi. Kuchli portfolio va loyihalar orqali sinab ko'rish mumkin."
        }
    elif is_junior_job or not v_exp or v_exp == "ko'rsatilmagan":
        return {
            "name": "🎓 Tajriba",
            "status": "Mos",
            "score": 100,
            "details": f"Vakansiya talabi: {vacancy_data.get('experience_required') or 'Junior / Boshlovchi'}. Sizning darajangizga to'liq mos!"
        }

    return {
        "name": "🎓 Tajriba",
        "status": "Mos",
        "score": 80,
        "details": f"Vakansiya tajriba talabi: {vacancy_data.get('experience_required')}."
    }


def check_skills_match(vacancy_data, skills_profile):
    """
    5. 💻 SKILL (Technical Skills Match)
    Python, Linux, SIEM, Networking, Git va tillarni solishtiradi.
    """
    v_skills = vacancy_data.get("skill_requirements") or vacancy_data.get("skill_talablari") or []
    if isinstance(v_skills, str):
        v_skills = [s.strip() for s in v_skills.split(",") if s.strip()]

    # Foydalanuvchi ko'nikmalarini yig'ish
    user_skill_keys = [
        "python", "linux", "networking", "siem", "git_github",
        "programming_languages", "cybersecurity_knowledge", "english", "russian"
    ]
    user_skills_dict = {}
    for k in user_skill_keys:
        obj = skills_profile.get(k, {})
        if isinstance(obj, dict):
            lvl = obj.get("level", "Intermediate")
            items = [str(x).lower() for x in obj.get("items", [])]
            user_skills_dict[k] = {"level": lvl, "items": items}

    # Aliaslar xaritasi
    skill_aliases = {
        "python": ["python", "telethon", "django", "fastapi", "aiogram"],
        "linux": ["linux", "ubuntu", "kali", "debian", "bash"],
        "networking": ["networking", "tcp/ip", "osi", "wireshark", "dns", "dhcp", "vpn", "firewall"],
        "siem": ["siem", "splunk", "wazuh", "elk", "sentinel", "qradar"],
        "git_github": ["git", "github", "gitlab"],
        "cybersecurity_knowledge": ["soc", "incident response", "pentest", "edr", "xdr", "security", "kiberxavfsizlik"],
        "programming_languages": ["sql", "c++", "c#", "java", "bash"]
    }

    matched_skills = []
    missing_skills = []

    for vs in v_skills:
        vs_clean = vs.lower().strip()
        matched = False

        for category, aliases in skill_aliases.items():
            if any(a in vs_clean for a in aliases) or vs_clean in aliases:
                matched = True
                lvl = user_skills_dict.get(category, {}).get("level", "Intermediate")
                matched_skills.append(f"{vs} [{lvl}]")
                break

        if not matched:
            missing_skills.append(vs)

    total_v = len(v_skills)
    if total_v == 0:
        pct = 85
        status = "Mos"
        details = "Aniq texnik talablar ko'rsatilmagan. Asosiy profildagi ko'nikmalaringiz yetarli."
    else:
        ratio = len(matched_skills) / total_v
        pct = int(ratio * 100)
        pct = min(100, max(20, pct))

        if ratio >= 0.65:
            status = "Mos"
            details = f"Talab qilingan {total_v} ta skilldan {len(matched_skills)} tasi mavjud: {', '.join([s.split()[0] for s in matched_skills[:5]])}."
        elif ratio >= 0.40:
            status = "Qisman mos"
            details = f"Asosiy skilllaringiz mos, lekin ba'zi texnologiyalar yetishmaydi: {', '.join(missing_skills[:3])}."
        else:
            status = "Mos emas"
            details = f"Vakansiyada talab qilingan asosiy skilllar yetishmaydi: {', '.join(missing_skills[:4])}."

    return {
        "name": "💻 Skill",
        "status": status,
        "score": pct,
        "matching_skills": matched_skills,
        "missing_skills": missing_skills,
        "details": details
    }


def check_salary_match(vacancy_data, personal_profile):
    """
    6. 💰 MAOSH (Salary Match)
    Minimal kutilgan maosh bilan taklif qilingan maoshni solishtiradi.
    """
    v_sal = str(vacancy_data.get("salary") or vacancy_data.get("maosh") or "Kelishiladi").strip()
    sal_conf = personal_profile.get("salary", {})
    min_sal_str = sal_conf.get("min_salary") or "500$"

    # Raqamli qiymatni ajratish
    v_num = re.search(r"\d[\d\s.,]*", v_sal)
    v_val = 0
    if v_num:
        raw_digits = re.sub(r"[^\d]", "", v_num.group(0))
        if raw_digits:
            v_val = int(raw_digits)

    # Dollar yoki so'm
    is_usd = "$" in v_sal or "usd" in v_sal.lower()
    is_uzs = "so'm" in v_sal.lower() or "сум" in v_sal.lower()

    if is_uzs and v_val > 0:
        # So'mni taxminan dollarga o'tkazish ($1 ~ 12 800)
        approx_usd = v_val / 12800
    elif is_usd and v_val > 0:
        approx_usd = v_val
    else:
        approx_usd = None

    if "kelishiladi" in v_sal.lower() or "suhbat" in v_sal.lower() or not v_val:
        return {
            "name": "💰 Maosh",
            "status": "Mos",
            "score": 85,
            "details": f"Maosh suhbat asosida belgilanadi ({v_sal}). Talablaringizni erkin bildira olasiz."
        }

    if approx_usd:
        if approx_usd >= 500:
            return {
                "name": "💰 Maosh",
                "status": "Mos",
                "score": 100,
                "details": f"Taklif qilingan maosh ({v_sal}) minimal kutilmangizdan ({min_sal_str}) yuqori."
            }
        else:
            return {
                "name": "💰 Maosh",
                "status": "Qisman mos",
                "score": 55,
                "details": f"Taklif qilingan maosh ({v_sal}) kutilgan miqdordan ({min_sal_str}) biroz kamroq."
            }

    return {
        "name": "💰 Maosh",
        "status": "Mos",
        "score": 80,
        "details": f"Maosh taklifi: {v_sal}."
    }


def check_career_goal_match(vacancy_data, personal_profile):
    """
    7. 🚀 KARYERA MAQSADI (Career Goals Match)
    Keyingi 6-12 oylik reja bilan rolni solishtiradi.
    """
    goal_data = personal_profile.get("career_goal", {})
    goal_str = (goal_data.get("goal") or "SOC Analyst bo'lib ishga kirish").lower()

    title = (vacancy_data.get("title") or vacancy_data.get("lavozim") or "").lower()
    raw = (vacancy_data.get("raw_text") or "").lower()

    # Agar maqsad SOC bo'lsa
    if "soc" in goal_str:
        if "soc" in title or "soc analyst" in raw or "incident" in title:
            return {
                "name": "🚀 Karyera maqsadi",
                "status": "Mos",
                "score": 100,
                "details": "Vakansiya bevosita 6 oylik asosiy maqsadingizga ('SOC Analyst bo'lish') 100% mos keladi!"
            }
        elif any(k in title for k in ["kiberxavfsizlik", "security", "pentest", "analyst"]):
            return {
                "name": "🚀 Karyera maqsadi",
                "status": "Mos",
                "score": 85,
                "details": "Kiberxavfsizlik yo'nalishidagi lavozim, SOC mutaxassisi bo'lish maqsadingiz sari kuchli tramplin."
            }
        elif "python" in title or "backend" in title:
            return {
                "name": "🚀 Karyera maqsadi",
                "status": "Qisman mos",
                "score": 75,
                "details": "Python/Dasturlash roli. Kiberxavfsizlikka tutash soha bo'lib, amaliy tajriba beradi."
            }

    return {
        "name": "🚀 Karyera maqsadi",
        "status": "Mos emas",
        "score": 15,
        "details": f"Vakansiya karyera maqsadingiz ({goal_data.get('goal', 'Kiberxavfsizlik')})ga mos kelmaydi."
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. ASOSIY TAHLIL VA BAHOLASH (ENTRY POINT)
# ─────────────────────────────────────────────────────────────────────────────

def match_vacancy_with_profile(vacancy_input):
    """
    Vakansiyani foydalanuvchining barcha profillari bilan birlashtirilgan
    6 ta asosiy mezon bo'yicha qat'iy tekshiradi:
    "Bu Orifxonga QIZIQARLIMI + VAQTIGA SIG‘ADIMI + JOYI MOSMI + SKILLIGA TO‘G‘RI KELADIMI + TAJRIBASIGA MOSMI + KARYERA MAQSADIGA FOYDALI MI?"

    PRINSIP: "Ko'p ma'lumot emas, kerakli ma'lumot. 100 tadan 5 tasi mos bo'lsa, faqat o'sha 5 tasi o'tadi."
    """
    # 1. Agar matn kelsa, avval tahlil qilish
    if isinstance(vacancy_input, str):
        v_data = analyze_vacancy(vacancy_input, use_ai=True)
    elif isinstance(vacancy_input, dict):
        v_data = vacancy_input
    else:
        v_data = {}

    # 2. Profillarni yuklash
    p_profile = load_personal_profile()
    p_schedule = load_schedule()
    p_location = load_location_profile()
    p_skills = load_skills_profile()

    # 3. Mezonlar bo'yicha tekshirish
    c_interest = check_interest_match(v_data, p_profile)
    c_schedule = check_schedule_match(v_data, p_schedule)
    c_location = check_location_match(v_data, p_location)
    c_experience = check_experience_match(v_data, p_skills)
    c_skills = check_skills_match(v_data, p_skills)
    c_salary = check_salary_match(v_data, p_profile)
    c_career = check_career_goal_match(v_data, p_profile)

    # 4. Feedback asosida dinamik moslash
    from feedback_manager import apply_feedback_adjustments
    raw_v_text = vacancy_input if isinstance(vacancy_input, str) else json.dumps(v_data, ensure_ascii=False)
    fb_adj = apply_feedback_adjustments(
        item_title=v_data.get("title") or v_data.get("lavozim") or "",
        skills=v_data.get("skills_required") or [],
        full_text=raw_v_text,
        category="Vakansiya",
        base_score=75
    )
    feedback_reasons = fb_adj.get("reasons", [])
    is_fb_suppressed = fb_adj.get("is_suppressed", False)

    # 5. Vaznlar
    weights = {
        "interest": 0.20,
        "schedule": 0.25,     # Vaqt eng muhim mezon!
        "location": 0.10,
        "experience": 0.15,
        "skills": 0.15,
        "salary": 0.05,
        "career_goal": 0.10
    }

    # ─── 6 MEZONNING INDIVIDUAL XULOSALARI ──────────────────────────────
    # 1. 🎯 QIZIQARLIMI?
    has_interests = len(c_interest.get("matched_interests", [])) > 0
    qiziqarlimi = has_interests and c_interest.get("status") in ["Mos", "Qisman mos"]
    interest_verdict = ("Mos (" + ", ".join(c_interest.get("matched_interests", [])[:2]) + ")") if has_interests else "Mos emas"

    # 2. 🕐 VAQTIGA SIG'ADIMI?
    has_time_conflict = c_schedule.get("has_conflict", False)
    conflict_hours = c_schedule.get("conflict_hours", 0)
    vaqt_sigadimi = not has_time_conflict or conflict_hours < 1.5
    v_hours_str = str(v_data.get("working_hours") or v_data.get("ish_vaqti") or "")
    if vaqt_sigadimi:
        if v_hours_str and v_hours_str != "Ko'rsatilmagan" and len(v_hours_str) <= 25:
            vaqt_verdict = f"Sig'adi ({v_hours_str})"
        else:
            vaqt_verdict = "Sig'adi (O'qishdan keyin)"
    else:
        vaqt_verdict = f"Sig'maydi ({conflict_hours} soat to'qnashuv)"

    # 3. 📍 JOYI MOSMI?
    joy_mosmi = c_location.get("status") in ["Mos", "Qisman mos"]
    v_loc_str = str(v_data.get("location") or v_data.get("joy") or "Toshkent")
    v_fmt_str = str(v_data.get("work_format") or v_data.get("format") or "")
    if joy_mosmi:
        if "remote" in v_fmt_str.lower() or "masofaviy" in v_fmt_str.lower():
            joy_verdict = "Mos (Remote)"
        elif "hybrid" in v_fmt_str.lower():
            joy_verdict = f"Mos ({v_loc_str} / Hybrid)"
        else:
            joy_verdict = f"Mos ({v_loc_str})"
    else:
        joy_verdict = f"Mos emas ({v_loc_str})"

    # 4. 💻 SKILLIGA TO'G'RI KELADIMI?
    skill_mosmi = c_skills.get("status") in ["Mos", "Qisman mos"]
    matched_skills_list = c_skills.get("matched_skills", [])
    if skill_mosmi and matched_skills_list:
        clean_s = [s.split("[")[0].strip() for s in matched_skills_list[:3]]
        skill_verdict = f"Mos ({', '.join(clean_s)})"
    elif skill_mosmi:
        skill_verdict = "Mos (Junior daraja)"
    else:
        skill_verdict = "To'g'ri kelmaydi"

    # 5. 🎓 TAJRIBASIGA MOSMI?
    tajriba_mosmi = c_experience.get("status") in ["Mos", "Qisman mos"]
    v_exp_str = str(v_data.get("experience_required") or v_data.get("tajriba_talabi") or "Junior/Intern")
    if tajriba_mosmi:
        tajriba_verdict = f"Mos ({v_exp_str})"
    else:
        tajriba_verdict = f"Mos emas ({v_exp_str})"

    # 6. 🚀 KARYERA MAQSADIGA FOYDALI MI?
    karyera_foydalimi = c_career.get("status") in ["Mos", "Qisman mos"] and not is_fb_suppressed
    if is_fb_suppressed:
        karyera_verdict = "Rad etilgan (Fikrlar bo'yicha filtrlangan)"
    elif karyera_foydalimi:
        karyera_verdict = "Foydali (SOC Analyst sari qadam)"
    else:
        karyera_verdict = "Foydasiz (Boshqa soha)"

    six_pillars = {
        "interest": {"name": "🎯 Qiziqish", "passed": qiziqarlimi, "verdict": interest_verdict, "status": c_interest.get("status")},
        "schedule": {"name": "🕐 Vaqt", "passed": vaqt_sigadimi, "verdict": vaqt_verdict, "status": c_schedule.get("status")},
        "location": {"name": "📍 Joy", "passed": joy_mosmi, "verdict": joy_verdict, "status": c_location.get("status")},
        "skills": {"name": "💻 Skill", "passed": skill_mosmi, "verdict": skill_verdict, "status": c_skills.get("status")},
        "experience": {"name": "🎓 Tajriba", "passed": tajriba_mosmi, "verdict": tajriba_verdict, "status": c_experience.get("status")},
        "career": {"name": "🚀 Karyera", "passed": karyera_foydalimi, "verdict": karyera_verdict, "status": c_career.get("status")}
    }

    failed_pillars = [p["name"] for p in six_pillars.values() if not p["passed"]]

    # ─── QAT'IY FILTRLASH: "Ko'p ma'lumot emas, kerakli ma'lumot" ───
    # 100 ta postdan faqat haqiqatan barcha 6 mezonni qanoatlantirganlari o'tadi!
    if failed_pillars:
        is_qualified = False
        overall_score = min(35, c_interest["score"], c_schedule["score"])
        overall_status = "🔴 Mos emas"
        status_note = f"6 mezon talabiga javob bermaydi ({', '.join(failed_pillars)})"
    else:
        is_qualified = True
        weighted_score = (
            c_interest["score"] * weights["interest"] +
            c_schedule["score"] * weights["schedule"] +
            c_location["score"] * weights["location"] +
            c_experience["score"] * weights["experience"] +
            c_skills["score"] * weights["skills"] +
            c_salary["score"] * weights["salary"] +
            c_career["score"] * weights["career_goal"]
        )
        overall_score = int(round(weighted_score)) + fb_adj.get("bonus", 0)
        overall_score = max(0, min(100, overall_score))

        if overall_score >= 90:
            overall_status = "🔥 Juda mos"
            status_note = "Barcha 6 mezon bo'yicha ideal moslik"
        elif overall_score >= 75:
            overall_status = "🟢 Mos"
            status_note = "Barcha 6 mezon bo'yicha yaxshi moslik"
        else:
            overall_status = "🟡 Qisman mos"
            status_note = "Umumiy ball 75 ga yetmadi"

    match_result = {
        "overall_status": overall_status,
        "overall_score": overall_score,
        "is_qualified": is_qualified,
        "status_note": status_note,
        "six_pillars": six_pillars,
        "failed_pillars": failed_pillars,
        "has_time_conflict": has_time_conflict,
        "conflict_hours": conflict_hours,
        "feedback_reasons": feedback_reasons,
        "feedback_adjustment": fb_adj,
        "criteria": {
            "interest": c_interest,
            "schedule": c_schedule,
            "location": c_location,
            "experience": c_experience,
            "skills": c_skills,
            "salary": c_salary,
            "career_goal": c_career
        },
        "vacancy_summary": {
            "title": v_data.get("title") or v_data.get("lavozim") or "Ko'rsatilmagan",
            "company": v_data.get("company") or v_data.get("kompaniya") or "Ko'rsatilmagan",
            "location": v_data.get("location") or v_data.get("joy") or "Ko'rsatilmagan",
            "work_format": v_data.get("work_format") or v_data.get("format") or "Office",
            "working_hours": v_data.get("working_hours") or v_data.get("ish_vaqti") or "Ko'rsatilmagan",
            "salary": v_data.get("salary") or v_data.get("maosh") or "Kelishiladi",
            "link": v_data.get("link") or "Ko'rsatilmagan"
        },
        "analyzed_at": datetime.now().isoformat()
    }

    return match_result

# ─────────────────────────────────────────────────────────────────────────────
# 4. CHROYLI HISOBOT FORMATTERI (REPORT VIEW)
# ─────────────────────────────────────────────────────────────────────────────

def format_match_report(match_result):
    """Tahlil natijasini chiroyli va o'qilishi qulay formatga keltiradi."""
    v = match_result.get("vacancy_summary", {})
    c = match_result.get("criteria", {})
    status = match_result.get("overall_status", "🟡 Qisman mos")
    score = match_result.get("overall_score", 0)

    lines = [
        "📊 <b>VAKANSIYA VA SHAXSIY PROFIL MOSLIGI TAHLILI</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💼 <b>Lavozim:</b> {v.get('title')}",
        f"🏢 <b>Kompaniya:</b> {v.get('company')}",
        f"📍 <b>Joy:</b> {v.get('location')} ({v.get('work_format')})",
        f"⏰ <b>Ish vaqti:</b> {v.get('working_hours')}",
        f"💰 <b>Maosh:</b> {v.get('salary')}",
        "",
        f"🏆 <b>YAKUNIY NATIJA:</b> {status} <b>({score}%)</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    # 7 ta mezon
    lines.append(f"🎯 <b>Qiziqish:</b> [{c.get('interest', {}).get('status')}] — {c.get('interest', {}).get('details')}")
    lines.append(f"🕐 <b>Vaqt:</b> [{c.get('schedule', {}).get('status')}] — {c.get('schedule', {}).get('details')}")
    lines.append(f"📍 <b>Joy:</b> [{c.get('location', {}).get('status')}] — {c.get('location', {}).get('details')}")
    lines.append(f"🎓 <b>Tajriba:</b> [{c.get('experience', {}).get('status')}] — {c.get('experience', {}).get('details')}")
    lines.append(f"💻 <b>Skill:</b> [{c.get('skills', {}).get('status')}] — {c.get('skills', {}).get('details')}")
    lines.append(f"💰 <b>Maosh:</b> [{c.get('salary', {}).get('status')}] — {c.get('salary', {}).get('details')}")
    lines.append(f"🚀 <b>Karyera:</b> [{c.get('career_goal', {}).get('status')}] — {c.get('career_goal', {}).get('details')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if match_result.get("has_time_conflict"):
        lines.append(f"⚠️ <b>Diqqat:</b> O'qish/ish jadvalingiz bilan {match_result.get('conflict_hours')} soat to'qnashuv bor!")
    else:
        lines.append("✨ <b>Xulosa:</b> Vaqt to'qnashuvi yo'q, kunlik bo'sh vaqtingizga to'g'ri keladi.")

    return "\n".join(lines)
