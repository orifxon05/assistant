import os
import json

PROFILE_FILE = "profile.json"
DEFAULT_FOLDER_NAMES = ["Intelligence", "Addek", "intelligence", "addek", "📂 Intelligence", "📂 Addek"]

CATEGORIES = [
    "JOB",
    "INTERNSHIP",
    "CYBERSECURITY",
    "PYTHON",
    "AI",
    "PROGRAMMING",
    "EDUCATION",
    "GRANT",
    "NEWS",
    "TECHNOLOGY",
    "OTHER"
]

def load_user_profile():
    if not os.path.exists(PROFILE_FILE):
        default_profile = {
            "name": os.getenv("OWNER_NAME", "Foydalanuvchi"),
            "university": "",
            "year": "",
            "status": "Talaba",
            "primary_field": "Cybersecurity",
            "goals": ["Cybersecurity sohasida tajriba yig'ish", "Internship/shogirdlik orqali kirish"],
            "primary_directions": ["Cybersecurity", "SOC", "Incident Monitoring", "Incident Response", "Antifraud", "Security Analyst"],
            "secondary_directions": ["Python", "Backend", "AI", "Telegram bot", "Linux"],
            "opportunity_types": ["Internship", "Trainee", "Junior", "Apprentice / Shogird", "Grant", "Kurs"],
            "allowed_experience": ["No experience", "0 years", "0-1 years", "Junior", "Intern", "Trainee", "Student"],
            "primary_location": "Toshkent, O'zbekiston",
            "allow_remote": True,
            "allow_uzbekistan": True,
            "allow_global_online": True,
            "min_relevance_score_to_send": 80,
            "onboarding_completed": False
        }
        save_user_profile(default_profile)
        return default_profile

    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[CONFIG] profile.json o'qishda xatolik:", e)
        return {}

def save_user_profile(profile_data):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("[CONFIG] profile.json saqlashda xatolik:", e)
        return False

def build_analyzer_system_prompt(profile=None):
    if not profile:
        profile = load_user_profile()

    name = profile.get("name", "Orifxon")
    uni = profile.get("university", "TATU")
    year = profile.get("year", "")
    status = profile.get("status", "Talaba")
    primary_field = profile.get("primary_field", "Cybersecurity")
    goals = ", ".join(profile.get("goals", ["SOC Analyst bo'lib ishga kirish"]))
    p_dirs = ", ".join(profile.get("primary_directions", ["Cybersecurity", "SOC", "Incident Monitoring"]))
    s_dirs = ", ".join(profile.get("secondary_directions", ["Python", "Linux", "Networking", "SIEM"]))
    opps = ", ".join(profile.get("opportunity_types", ["Internship", "Junior", "Trainee"]))
    exp_levels = ", ".join(profile.get("allowed_experience", ["0-1 yil", "Junior", "Intern"]))
    loc = profile.get("primary_location", "Toshkent")

    prompt = f"""Sen {name}ning shaxsiy "Opportunity & Intelligence Filter" tahlilchisisan.
Vazifang Telegram postini o'qib, uni {name}ning barcha profillari (Interest, Schedule, Location, Skills, Experience, Career Goals) bilan birlashtirib,
"Bu {name}ga kerakmi?" deb emas, balki qat'iy ravishda quyidagi savolga javob berish:

"BU {name.upper()}GA QIZIQARLIMI + VAQTIGA SIG‘ADIMI + JOYI MOSMI + SKILLIGA TO‘G‘RI KELADIMI + TAJRIBASIGA MOSMI + KARYERA MAQSADIGA FOYDALI MI?"

ENG MUHIM PRINSIP:
"Ko‘p ma'lumot emas, kerakli ma'lumot. 100 ta postdan 5 tasi haqiqatan mos bo‘lsa, faqat o‘sha 5 tasini yubor."

{name.upper()}NING PROFIL MA'LUMOTLARI:
- Ism: {name}
- Ta'lim va dars jadvali: {uni} {year} {status}. Dushanba-Juma kunlari 07:00–13:00 dars vaqti. Ish/amaliyot o'qishdan keyingi bo'sh vaqtga (14:00+) yoki erkin grafik/part-time/remote bo'lishi shart!
- Qiziqishlar (Interest): {primary_field}, {p_dirs}, {s_dirs} (Kiberxavfsizlik, SOC, SIEM, Python, Linux, Tarmoqlar).
- Joylashuv (Location): {loc} (Toshkentda ofis, yoki Remote/Hybrid). Boshqa shahar/davlat ofislari rad etiladi.
- Ko'nikmalar (Skills): Cybersecurity (SOC, SIEM, Incident Response), Linux, Networking, Python, Git/GitHub.
- Tajriba (Experience): {exp_levels} (Talaba, Junior, Intern, 0-1 yil. 2-3+ yil talab qilingan Senior/Middle postlar qat'iyan rad etiladi!).
- Karyera maqsadi (Career): {goals}.

6 TA ASOSIY MEZON (QAT'IY VETO QOIDALARI):
1. 🎯 QIZIQARLIMI? (Cybersecurity, SOC, Pentest, IT, Dasturlash yo'nalishlariga mosmi?)
2. 🕐 VAQTIGA SIG‘ADIMI? (07:00–13:00 o'qish vaqtiga to'sqinlik qilmaydimi? 14:00+, part-time, erkin grafikmi?)
3. 📍 JOYI MOSMI? (Toshkentda yoki Masofaviy (Remote) / Gibridmi?)
4. 💻 SKILLIGA TO‘G‘RI KELADIMI? (Cyber, Python, Linux, SIEM, Network bilimlariga mosmi?)
5. 🎓 TAJRIBASIGA MOSMI? (Talaba/Intern/Junior 0-1 yilgacha darajadami?)
6. 🚀 KARYERA MAQSADIGA FOYDALI MI? (Kiberxavfsizlik / SOC Analyst bo'lishiga xizmat qiladimi?)

Agar shu 6 ta mezondan birortasi qat'iyan buzilsa (masalan: dars vaqtida to'liq kunlik ofis ishi, boshqa viloyatdagi ofis, 3+ yil tajriba, yoki ITdan tashqari soha bo'lsa), RELEVANCE_SCORE ni 35 dan past qil va rad et!

FILTRLASH VA RELEVANCE SCORE QOIDALARI:
- 90–100: "🔥 Juda mos" (Barcha 6 mezon 100% ideal mos: SOC/Cyber/Python Internship yoki Junior, 14:00+ yoki remote, Toshkent, 0-1 yil tajriba).
- 75–89: "🟢 Mos" (Barcha 6 mezonga mos keladi, yaxshi IT imkoniyat yoki bepul nufuzli kurs/grant).
- 40–74: "IGNORE" (Umumiy ball 75 ga yetmadi, filtrdan o'tmaydi).
- 0–39: "IGNORE" (Mos emas yoki veto qoidalariga uchradi).

JAVOBINGNI FAQAT VA FAQAT QUYIDAGI JSON FORMATIDA QAYTAR (boshqa hech qanday so'z qo'shma):
{{
  "is_relevant": true yoki false (agar score >= 75 bo'lsa true, aks holda false),
  "relevance_score": 0 dan 100 gacha butun son,
  "level": "URGENT" (score >= 90), "USEFUL" (75 <= score < 90), "IGNORE" (score < 75),
  "categories": ["JOB", "INTERNSHIP", "COURSE", "GRANT", va h.k.],
  "title": "Post sarlavhasi yoki lavozim/kurs nomi",
  "company": "Kompaniya yoki tashkilot nomi (agar bo'lmasa 'Ko\\'rsatilmagan')",
  "location": "Joylashuv (masalan: 'Toshkent', 'Remote')",
  "salary": "Maosh miqdori yoki 'Kelishiladi'",
  "experience_required": "Talab qilingan tajriba (masalan: '0-1 yil', 'Junior/Intern')",
  "key_requirements": "Asosiy talablar (qisqa)",
  "deadline": "Topshirish muddati (agar bo'lsa)",
  "why_matches": [
    "Cybersecurity / IT yo'nalishi",
    "O‘qishdan keyingi vaqtga mos (14:00–18:00)",
    "Toshkent / Remote",
    "Junior/Intern (0–1 yil)"
  ],
  "action_advice": "Rezyume yoki ariza topshirish bo'yicha qisqa amaliy maslahat",
  "drawbacks": "Cheklovlar (agar bo'lsa)"
}}
"""
    return prompt
