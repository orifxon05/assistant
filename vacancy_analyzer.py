# -*- coding: utf-8 -*-
"""
vacancy_analyzer.py - Telegram Vakansiya Postlarini Tahlil Qilish Moduli (Jarvis)

Vazifasi:
Telegram kanallari va guruhlaridagi vakansiya e'lonlarini tahlil qilib,
quyidagi 11 ta asosiy maydonni avtomatik ajratib olish:

1. Lavozim (Job Title / Position)
2. Kompaniya (Company)
3. Joy (Location / City, District)
4. Remote/Hybrid/Office (Work format)
5. Ish vaqti (Working hours / Schedule)
6. Maosh (Salary)
7. Tajriba talabi (Experience required)
8. Til talabi (Language requirements)
9. Skill talablari (Technical skills / Technologies)
10. Deadline (Application deadline / Muddat)
11. Link (Aloqa, havola, @username, email, bot)

Natija:
Standartlashtirilgan `vacancy_data` lug'ati (dictionary) sifatida qaytariladi.
Hozircha foydalanuvchiga yuborish yoki scoring qilinmaydi.
"""

import os
import re
import json
from datetime import datetime
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Tillar va texnologiyalar uchun ma'lumotlar bazasi (Heuristics uchun)
KNOWN_TECH_SKILLS = [
    "Python", "Bash", "Linux", "Ubuntu", "Kali Linux", "Debian", "CentOS",
    "SOC", "SIEM", "Splunk", "Wazuh", "ELK", "Elasticsearch", "Logstash", "Kibana",
    "Microsoft Sentinel", "QRadar", "AlienVault", "Suricata", "Snort", "Zeek",
    "Wireshark", "TCP/IP", "OSI", "DNS", "DHCP", "VPN", "Firewall", "Palo Alto",
    "Fortinet", "Cisco", "CCNA", "CompTIA Security+", "CEH", "EJPT", "OSCP",
    "Incident Response", "Digital Forensics", "Malware Analysis", "Reverse Engineering",
    "Pentest", "Penetration Testing", "Metasploit", "Nmap", "Burp Suite", "OWASP",
    "EDR", "XDR", "CrowdStrike", "Defender", "DLP", "UEBA", "IAM", "Active Directory",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
    "Docker", "Kubernetes", "Git", "GitHub", "GitLab", "CI/CD",
    "FastAPI", "Django", "Flask", "Telethon", "Aiogram", "REST API", "GraphQL",
    "C", "C++", "C#", ".NET", "Java", "Spring", "Go", "Golang", "Rust",
    "JavaScript", "TypeScript", "Node.js", "React", "Vue", "Angular",
    "AWS", "Azure", "GCP", "Cloud Security", "DevSecOps", "Cryptography"
]

KNOWN_CITIES = [
    "Toshkent", "Samarqand", "Farg'ona", "Andijon", "Namangan",
    "Buxoro", "Qarshi", "Navoiy", "Urganch", "Jizzax", "Nukus", "Termiz"
]

TASHKENT_DISTRICTS = [
    "Shayxontohur", "Yunusobod", "Chilonzor", "Mirzo Ulug'bek",
    "Yakkasaroy", "Mirobod", "Olmazor", "Uchtepa", "Yashnobod",
    "Sergeli", "Bektemir", "Yangihayot"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. VAKANSIYA POSTINI ANIQLASH (PRE-FILTER)
# ─────────────────────────────────────────────────────────────────────────────

VACANCY_KEYWORDS = [
    "vakansiya", "вакансия", "vacancy", "hiring", "ishga taklif", "ish bor",
    "ishga qabul", "talab qilinadi", "требуется", "ищем", "lavozim", "должность",
    "oylik maosh", "зарплата", "salary", "ish haqi", "majburiyatlar", "обязанности",
    "talablar", "требования", "requirements", "ish grafigi", "график работы",
    "ish vaqti", "aloqa", "резюме", "rezyume", "cv", "portfolio"
]

def is_vacancy_post(text: str) -> bool:
    """
    Berilgan Telegram posti ish vakansiyasi ekanligini tezkor tekshiradi.
    """
    if not text or len(text.strip()) < 35:
        return False

    t_lower = text.lower()
    matches = sum(1 for kw in VACANCY_KEYWORDS if kw in t_lower)
    return matches >= 2

# ─────────────────────────────────────────────────────────────────────────────
# 2. JSON RESPONSE CLEANER
# ─────────────────────────────────────────────────────────────────────────────

def clean_json_response(raw_response: str):
    """
    AI model javobidan sof JSON obyektini xavfsiz ajratib oladi.
    """
    if not raw_response:
        return None
    raw = raw_response.strip()

    match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    elif raw.startswith("```") and raw.endswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end+1]

    try:
        return json.loads(raw)
    except Exception as e:
        print(f"[VACANCY_ANALYZER] JSON parse xatolik: {e}, Raw: {raw[:120]}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 3. AI ORQALI VAKANSIYANI TAHLIL QILISH (TIER 1 - LLM EXTRACTION)
# ─────────────────────────────────────────────────────────────────────────────

AI_EXTRACTION_SYSTEM_PROMPT = """Sen Telegram vakansiya postlarini chuqur tahlil qiluvchi yuqori aniqlikdagi AI tizimisan.
Vakansiya e'lonidan quyidagi 11 ta parametrni aniq ajratib ol va FAQAT JSON formatida qaytar:

1. title: Lavozim nomi (masalan: "Junior SOC Analyst", "Python Backend Developer")
2. company: Kompaniya yoki tashkilot nomi (agar ko'rsatilmagan bo'lsa "Ko'rsatilmagan")
3. location: Joylashuv (Shahar, tuman yoki manzil, masalan: "Toshkent, Shayxontohur tumani")
4. work_format: "Remote", "Hybrid", yoki "Office" (agar bir nechtasi bo'lsa "Hybrid / Office" kabi)
5. working_hours: Ish vaqti va tartibi (masalan: "09:00 - 18:00 (5/2)", "Full-time", "Erkin grafik")
6. salary: Maosh miqdori (masalan: "$600 - $1000", "8 000 000 so'm", yoki "Kelishiladi")
7. experience_required: Talab etiladigan ish tajribasi (masalan: "1+ yil", "Kamida 6 oy", "Boshlovchi / Tajribasiz")
8. language_requirements: Til bilish talablari ro'yxati (masalan: ["Ingliz tili B2", "Rus tili erkin"])
9. skill_requirements: Texnik ko'nikmalar, texnologiyalar va vositalar ro'yxati (masalan: ["Python", "Linux", "SIEM", "TCP/IP"])
10. deadline: Ariza topshirish oxirgi muddati (masalan: "15-oktabr", "2026-10-20" yoki "Ko'rsatilmagan")
11. link: Aloqa, havola, @username, email, bot yoki ariza yuborish linki (masalan: "@hr_manager", "https://t.me/...", "hr@company.uz")

QAT'IY QOIDALAR:
- O'zingdan ma'lumot to'qima. Matnda yo'q bo'lsa "Ko'rsatilmagan" yoki bo'sh ro'yxat [] deb yoz.
- Javob faqat va faqat yagona JSON obyekti bo'lsin. Hech qanday kirish yoki xulosa matni qo'shma."""

def extract_with_ai(post_text: str, channel_title: str = "Telegram Kanal") -> dict:
    """
    Groq LLM orqali postdan barcha 11 ta maydonni ajratib oladi.
    Model band bo'lsa zaxira modellarga o'tadi.
    """
    if not GROQ_API_KEY:
        return {}

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    primary_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    models_to_try = [
        primary_model,
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b"
    ]
    # Takrorlanmas qilib tartiblash
    seen = set()
    unique_models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            unique_models.append(m)

    user_prompt = f"""[Manba: {channel_title}]

Quyidagi Telegram vakansiya postini tahlil qil va 11 ta parametr bo'yicha JSON qaytar:

---
{post_text}
---"""

    for model in unique_models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": AI_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=22)
            data = resp.json()
            if "choices" in data and data["choices"]:
                raw_text = data["choices"][0]["message"]["content"]
                parsed = clean_json_response(raw_text)
                if parsed and isinstance(parsed, dict) and "title" in parsed:
                    return parsed
            elif "error" in data:
                err_code = data["error"].get("code", "")
                err_msg = data["error"].get("message", "")
                print(f"[VACANCY AI {model}]: {err_code or err_msg}")
        except Exception as e:
            print(f"[VACANCY AI {model} XATOLIK]: {e}")
            continue

    return {}

# ─────────────────────────────────────────────────────────────────────────────
# 4. QOIDALAR VA REGEX BO'YICHA TAHLIL QILISH (TIER 2 - HEURISTIC ENGINE)
# ─────────────────────────────────────────────────────────────────────────────

def extract_with_heuristics(post_text: str, channel_title: str = "Telegram Kanal") -> dict:
    """
    AI ishlamay qolganda yoki oflayn rejimda barcha 11 ta maydonni
    matndan qidirib topuvchi qoidalarga asoslangan kuchli parser.
    """
    text = post_text.strip()
    text_lower = text.lower()
    res = {}

    # 1. LAVOZIM (TITLE)
    title = None
    title_match = re.search(
        r"(?:lavozim|vakansiya|position|job title|вакансия|должность|ищем|требуется|hiring|we are hiring|we're hiring|role|роль|kerak|qidirilmoqda)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Birinchi qator yoki ma'lum kasb nomlari
        common_roles = [
            "SOC Analyst", "Security Analyst", "Cybersecurity Specialist", "Pentester",
            "Python Developer", "Backend Developer", "Frontend Developer", "Full Stack Developer",
            "DevOps Engineer", "System Administrator", "Data Analyst", "QA Engineer",
            "Tarmoq muhandisi", "Dasturchi", "Kiberxavfsizlik mutaxassisi"
        ]
        for role in common_roles:
            if role.lower() in text_lower:
                title = role
                break
        if not title:
            # 1-qatorni sinab ko'rish
            first_line = text.split("\n")[0].strip("#* \t")
            if len(first_line) < 60 and ("dasturchi" in first_line.lower() or "analyst" in first_line.lower() or "engineer" in first_line.lower() or "developer" in first_line.lower() or "mutaxassis" in first_line.lower()):
                title = first_line

    res["title"] = title or "Ko'rsatilmagan"

    # 2. KOMPANIYA (COMPANY)
    company = None
    comp_match = re.search(
        r"(?:kompaniya|korxona|tashkilot|компания|организация|company|employer)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if comp_match:
        company = comp_match.group(1).strip()
    else:
        quote_match = re.search(r'[«"“]([A-Za-z0-9\s]{2,30})[»"”]\s*(?:MCHJ|LLC|AJ|kompaniyasi|bank|holding)?', text)
        if quote_match:
            company = quote_match.group(1).strip()
        elif channel_title and channel_title not in ["Telegram Kanal", "Kanal"]:
            company = channel_title

    res["company"] = company or "Ko'rsatilmagan"

    # 3. JOY (LOCATION)
    found_city = None
    for c in KNOWN_CITIES:
        if c.lower() in text_lower:
            found_city = c
            break

    found_district = None
    for d in TASHKENT_DISTRICTS:
        if d.lower() in text_lower:
            found_district = d
            break

    loc_match = re.search(
        r"(?:manzil|joy|lokatsiya|joylashuv|адрес|локация|город|location|city)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if loc_match:
        res["location"] = loc_match.group(1).strip()
    elif found_city and found_district:
        res["location"] = f"{found_city}, {found_district} tumani"
    elif found_city:
        res["location"] = found_city
    elif found_district:
        res["location"] = f"Toshkent, {found_district} tumani"
    else:
        res["location"] = "Ko'rsatilmagan"

    # 4. REMOTE / HYBRID / OFFICE (WORK FORMAT)
    formats = []
    if any(w in text_lower for w in ["remote", "masofaviy", "удаленно", "удалённо"]):
        formats.append("Remote")
    if any(w in text_lower for w in ["hybrid", "gibrid", "гибрид"]):
        formats.append("Hybrid")
    if any(w in text_lower for w in ["office", "ofis", "офис", "on-site", "onsite"]):
        formats.append("Office")

    if formats:
        res["work_format"] = " / ".join(formats)
    else:
        res["work_format"] = "Office"

    # 5. ISH VAQTI (WORKING HOURS)
    hours = None
    time_range_match = re.search(r"\b(\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2})\b", text)
    schedule_match = re.search(
        r"(?:ish vaqti|ish grafigi|grafik|график|режим работы|working hours|schedule)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    days_match = re.search(r"\b(5/2|6/1|2/2)\b", text)

    if schedule_match:
        hours = schedule_match.group(1).strip()
    elif time_range_match:
        hours = time_range_match.group(1)
        if days_match:
            hours += f" ({days_match.group(1)})"
    elif any(w in text_lower for w in ["full time", "full-time", "to'liq kun", "полный рабочий день"]):
        hours = "Full-time (To'liq kun)"
    elif any(w in text_lower for w in ["part time", "part-time", "yarim kun"]):
        hours = "Part-time (Yarim stavka)"
    elif any(w in text_lower for w in ["erkin grafik", "flexible", "свободный график"]):
        hours = "Erkin grafik (Flexible)"

    res["working_hours"] = hours or "Ko'rsatilmagan"

    # 6. MAOSH (SALARY)
    salary = None
    sal_match = re.search(
        r"(?:maosh|oylik|ish haqi|зарплата|зп|salary|compensation)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if sal_match:
        salary = sal_match.group(1).strip()
    else:
        # Raqamli naqsh ($600-$1000 yoki 10 000 000 so'm)
        amt_match = re.search(
            r"(\$?\s*\d[\d\s.,]*\s*(?:[-–—]\s*\$?\s*\d[\d\s.,]*)?\s*(?:so['ʻ`ʼ]?m|сум|\$|usd|uzs))",
            text,
            re.IGNORECASE
        )
        if amt_match:
            salary = amt_match.group(1).strip()
        elif any(w in text_lower for w in ["kelishiladi", "suhbat asosida", "dogovor", "договорная", "negotiable"]):
            salary = "Kelishiladi / Suhbat asosida"

    res["salary"] = salary or "Kelishiladi"

    # 7. TAJRIBA TALABI (EXPERIENCE REQUIRED)
    exp = None
    exp_match = re.search(
        r"(?:tajriba|ish tajribasi|staj|опыт работы|опыт|experience)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if exp_match:
        exp = exp_match.group(1).strip()
    else:
        exp_range = re.search(
            r"(\b\d+\s*(?:[-–—]\s*\d+)?\s*(?:yil|oy|лет|года|лет опыта|years|year))\b",
            text,
            re.IGNORECASE
        )
        if exp_range:
            exp = f"Kamida {exp_range.group(1)}"
        elif any(w in text_lower for w in ["boshlovchi", "stajyor", "trainee", "internship", "amaliyot", "bez opita", "tajribasiz"]):
            exp = "Talab etilmaydi (Stajyor / Junior)"

    res["experience_required"] = exp or "Ko'rsatilmagan"

    # 8. TIL TALABI (LANGUAGE REQUIREMENTS)
    languages = []
    if re.search(r"\b(ingliz\w*|english\w*|английск\w*|ielts|toefl)\b", text_lower):
        lvl = ""
        lvl_m = re.search(r"(?:ingliz|english|английск)[^\n\r,]*\b(a1|a2|b1|b2|c1|c2|intermediate|advanced|fluent|erkin)\b", text_lower)
        if lvl_m:
            lvl = f" ({lvl_m.group(1).upper()})"
        languages.append(f"Ingliz tili{lvl}")

    if re.search(r"\b(rus\w*|russian\w*|русск\w*)\b", text_lower):
        lvl = ""
        if "erkin" in text_lower or "свободн" in text_lower:
            lvl = " (Erkin)"
        elif "razgovorn" in text_lower or "so'zlashuv" in text_lower:
            lvl = " (So'zlashuv)"
        languages.append(f"Rus tili{lvl}")

    if re.search(r"\b(o['ʻ`ʼ]?zbek\w*|узбекск\w*|uzbek\w*)\b", text_lower):
        languages.append("O'zbek tili")

    res["language_requirements"] = languages

    # 9. SKILL TALABLARI (SKILL REQUIREMENTS)
    detected_skills = []
    for skill in KNOWN_TECH_SKILLS:
        # Exact word match
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            if skill not in detected_skills:
                detected_skills.append(skill)

    res["skill_requirements"] = detected_skills

    # 10. DEADLINE (ARIZA MUDDATI)
    deadline = None
    dl_match = re.search(
        r"(?:deadline|oxirgi muddat|ariza muddati|qabul muddati|muddati?|ariza topshirish|дедлайн|срок|до)\s*[:\-–—]\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )
    if dl_match:
        deadline = dl_match.group(1).strip()
    else:
        month_match = re.search(
            r"(\b\d{1,2}\s*[-–—]?\s*(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentabr|oktabr|noyabr|dekabr|января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|january|february|march|april|may|june|july|august|september|october|november|december)[a-z]*)\b",
            text,
            re.IGNORECASE
        )
        date_match = re.search(r"\b(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)\b", text)
        if month_match:
            deadline = month_match.group(1).strip()
        elif date_match and date_match.group(1) not in ["5/2", "6/1", "2/2"]:
            deadline = date_match.group(1).strip()

    res["deadline"] = deadline or "Ko'rsatilmagan"

    # 11. LINK (ALOQA / REZYUME YUBORISH)
    links = []
    # Telegram username
    usernames = re.findall(r"@[A-Za-z0-9_]{4,}", text)
    if usernames:
        links.extend(usernames)

    # URL
    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        links.extend(urls)

    # Email
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if emails:
        links.extend(emails)

    # Telefon
    phones = re.findall(r"\+998\s*\(?\d{2}\)?\s*\d{3}[\s-]?\d{2}[\s-]?\d{2}", text)
    if phones:
        links.extend(phones)

    res["link"] = links[0] if links else "Ko'rsatilmagan"

    return res

# ─────────────────────────────────────────────────────────────────────────────
# 5. MA'LUMOTLARNI STANDARTLASHTIRISH (NORMALIZATION TO vacancy_data)
# ─────────────────────────────────────────────────────────────────────────────

def build_vacancy_data(raw_data: dict, original_text: str = "", source_channel: str = "") -> dict:
    """
    AI yoki Heuristic orqali olingan xom ma'lumotlarni qat'iy
    standartlashtirilgan `vacancy_data` tuzilmasiga o'tkazadi.
    Ingliz va O'zbek kalitlarini teng ta'minlaydi.
    """
    title = str(raw_data.get("title") or "Ko'rsatilmagan").strip()
    company = str(raw_data.get("company") or "Ko'rsatilmagan").strip()
    location = str(raw_data.get("location") or "Ko'rsatilmagan").strip()
    work_format = str(raw_data.get("work_format") or "Office").strip()
    working_hours = str(raw_data.get("working_hours") or "Ko'rsatilmagan").strip()
    salary = str(raw_data.get("salary") or "Kelishiladi").strip()
    experience = str(raw_data.get("experience_required") or raw_data.get("tajriba_talabi") or "Ko'rsatilmagan").strip()

    # Tillar ro'yxati
    lang_raw = raw_data.get("language_requirements") or raw_data.get("til_talabi") or []
    if isinstance(lang_raw, str):
        languages = [lang_raw.strip()]
    elif isinstance(lang_raw, list):
        languages = [str(x).strip() for x in lang_raw if str(x).strip()]
    else:
        languages = []

    # Skilllar ro'yxati
    skills_raw = raw_data.get("skill_requirements") or raw_data.get("skills") or raw_data.get("skill_talablari") or []
    if isinstance(skills_raw, str):
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills = [str(s).strip() for s in skills_raw if str(s).strip()]
    else:
        skills = []

    # Dublikatlarni tozalash
    skills_unique = []
    for s in skills:
        if s not in skills_unique:
            skills_unique.append(s)

    deadline = str(raw_data.get("deadline") or "Ko'rsatilmagan").strip()
    link = str(raw_data.get("link") or "Ko'rsatilmagan").strip()

    # vacancy_data strukturasi
    vacancy_data = {
        # 11 ta asosiy standart kalitlar (English)
        "title": title,
        "company": company,
        "location": location,
        "work_format": work_format,
        "working_hours": working_hours,
        "salary": salary,
        "experience_required": experience,
        "language_requirements": languages,
        "skill_requirements": skills_unique,
        "deadline": deadline,
        "link": link,

        # O'zbekcha qulay aliaslar (so'ralgan nomlar bilan)
        "lavozim": title,
        "kompaniya": company,
        "joy": location,
        "format": work_format,
        "ish_vaqti": working_hours,
        "maosh": salary,
        "tajriba_talabi": experience,
        "til_talabi": languages,
        "skill_talablari": skills_unique,

        # Metadata va yordamchi maydonlar
        "is_vacancy": is_vacancy_post(original_text),
        "source_channel": source_channel,
        "raw_text": original_text,
        "extracted_at": datetime.now().isoformat()
    }

    return vacancy_data

# ─────────────────────────────────────────────────────────────────────────────
# 6. ASOSIY TAHLIL FUNKSIYASI (ENTRY POINT)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_vacancy(post_text: str, channel_title: str = "Telegram Kanal", use_ai: bool = True) -> dict:
    """
    Telegram vakansiya postini tahlil qiladi va `vacancy_data` strukturasini qaytaradi.
    
    Bosqichlar:
    1. AI (Groq LLM) orqali tahlil qilishga harakat qiladi.
    2. Agar AI javob bermasa yoki yetarli bo'lmasa, qoidalar asosidagi Heuristic parser ishlaydi.
    3. Ikkala natija birlashtirilib, qat'iy `vacancy_data` obyekti hosil qilinadi.
    4. Hech qanday scoring yoki foydalanuvchiga xabar yuborish bajarilmaydi.
    """
    if not post_text or not post_text.strip():
        return build_vacancy_data({}, "", channel_title)

    extracted_data = {}

    # 1-bosqich: AI orqali sinash
    if use_ai and GROQ_API_KEY:
        try:
            ai_data = extract_with_ai(post_text, channel_title)
            if ai_data and isinstance(ai_data, dict) and ai_data.get("title") not in [None, "", "Ko'rsatilmagan"]:
                extracted_data = ai_data
        except Exception as e:
            print(f"[VACANCY_ANALYZER] AI extraction error: {e}")

    # 2-bosqich: Heuristic orqali yetishmayotgan qismlarni to'ldirish yoki zaxira
    heuristic_data = extract_with_heuristics(post_text, channel_title)

    if not extracted_data:
        extracted_data = heuristic_data
    else:
        # AI bo'sh qoldirgan maydonlarni Heuristic bilan to'ldirish
        for key in ["title", "company", "location", "work_format", "working_hours", "salary", "experience_required", "deadline", "link"]:
            if extracted_data.get(key) in [None, "", "Ko'rsatilmagan"] and heuristic_data.get(key) not in [None, "", "Ko'rsatilmagan"]:
                extracted_data[key] = heuristic_data[key]

        # Skilllar va tillarni boyitish
        if not extracted_data.get("skill_requirements") and heuristic_data.get("skill_requirements"):
            extracted_data["skill_requirements"] = heuristic_data["skill_requirements"]
        if not extracted_data.get("language_requirements") and heuristic_data.get("language_requirements"):
            extracted_data["language_requirements"] = heuristic_data["language_requirements"]

    # 3-bosqich: Standart vacancy_data tuzish
    vacancy_data = build_vacancy_data(extracted_data, original_text=post_text, source_channel=channel_title)
    return vacancy_data

# ─────────────────────────────────────────────────────────────────────────────
# 7. FORMATLASH YORDAMCHISI (DEBUG / LOGGING UCHUN)
# ─────────────────────────────────────────────────────────────────────────────

def format_vacancy_summary(v_data: dict) -> str:
    """
    `vacancy_data` obyektini qulay o'qiladigan xulosa matniga aylantiradi.
    """
    skills_str = ", ".join(v_data.get("skill_requirements", [])) or "Ko'rsatilmagan"
    langs_str = ", ".join(v_data.get("language_requirements", [])) or "Ko'rsatilmagan"

    return (
        f"📋 Lavozim: {v_data.get('lavozim')}\n"
        f"🏢 Kompaniya: {v_data.get('kompaniya')}\n"
        f"📍 Joy: {v_data.get('joy')}\n"
        f"💼 Format: {v_data.get('format')}\n"
        f"⏰ Ish vaqti: {v_data.get('ish_vaqti')}\n"
        f"💰 Maosh: {v_data.get('maosh')}\n"
        f"⏳ Tajriba talabi: {v_data.get('tajriba_talabi')}\n"
        f"🗣 Til talabi: {langs_str}\n"
        f"🛠 Skill talablari: {skills_str}\n"
        f"📅 Deadline: {v_data.get('deadline')}\n"
        f"🔗 Link: {v_data.get('link')}"
    )
