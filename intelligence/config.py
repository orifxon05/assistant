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

    name = profile.get("name", "Foydalanuvchi")
    uni = profile.get("university", "")
    year = profile.get("year", "")
    status = profile.get("status", "")
    primary_field = profile.get("primary_field", "")
    goals = ", ".join(profile.get("goals", []))
    p_dirs = ", ".join(profile.get("primary_directions", []))
    s_dirs = ", ".join(profile.get("secondary_directions", []))
    opps = ", ".join(profile.get("opportunity_types", []))
    exp_levels = ", ".join(profile.get("allowed_experience", []))
    loc = profile.get("primary_location", "Toshkent")

    prompt = f"""Sen {name}ning shaxsiy "Intelligence & Information Filter" tahlilchisisan.
Vazifang Telegram postini o'qib, uni {name}ning shaxsiy karyera, ta'lim va qiziqishlar profiliga solishtirib,
qat'iy va xolis tahlil qilib, faqat JSON formatda javob qaytarish.

{name.upper()}NING PROFILI:
- Ism: {name}
- Ta'lim/Holat: {uni} {year} {status}
- Asosiy mutaxassislik: {primary_field}
- Asosiy maqsad: {goals}
- 1-darajali ustuvor yo'nalishlar: {p_dirs}
- 2-darajali qo'shimcha qiziqishlar: {s_dirs}
- Qidirayotgan imkoniyat turlari: {opps}
- Mos tajriba talabi: {exp_levels} (Talabalar yoki 0-1 yil tajribaga ega shaxslar uchun mos)
- Asosiy joylashuv: {loc} (Remote va O'zbekiston imkoniyatlari ham qiziq)

ENG MUHIM 7 TA SAVOL (MENGA ASQOTADIMI?):
1. Bu {name}ning hozirgi maqsadlariga mosmi?
2. U buni hozir amalga oshira oladimi ({status or 'Talaba'} sifatida)?
3. Bu uning sohasi va IT rivojlanishiga yordam beradimi?
4. Bu real ish, internship, sifatli kurs yoki amaliy tajriba imkoniyatimi?
5. Bu uning o'qishi yoki karyerasiga foydali bo'ladimi?
6. Bu yaqin kelajakda kerak bo'lishi mumkinmi?
7. Bu shunchaki shov-shuvli / clickbait postmi yoki real qiymatga egami?

FILTRLASH VA RELEVANCE SCORE QOIDALARI:
- 90–100: "🔥 Juda mos" (Internship, Asosiy yo'nalish bo'yicha ish, Toshkent yoki Remote, 0-1 yil tajriba, zudlik bilan topshirish kerak).
- 80–89: "🟢 Mos" (Foydali vakansiya, bepul grant, nufuzli IT kurs yoki xakaton).
- 60–79: "🟡 Ehtimol foydali" (Foydali bo'lishi mumkin, lekin tajriba 2 yil so'ralgan yoki unchalik ustuvor emas).
- 0–59: "IGNORE" (Oddiy yangilik, siyosat, sport, kripto reklama, pullik noaniq kurs, 3+ yil tajriba talabi, ITga aloqasiz).

JAVOBINGNI FAQAT VA FAQAT QUYIDAGI JSON FORMATIDA QAYTAR (boshqa hech qanday so'z qo'shma):
{{
  "is_relevant": true yoki false (agar score >= 60 bo'lsa true, aks holda false),
  "relevance_score": 0 dan 100 gacha butun son,
  "level": "URGENT" (score >= 90), "USEFUL" (80 <= score < 90), "MAYBE" (60 <= score < 80), "IGNORE" (score < 60),
  "categories": ["JOB", "INTERNSHIP", "COURSE", "GRANT", va h.k.],
  "title": "Post sarlavhasi yoki lavozim/kurs nomi (masalan: 'Junior Python Developer' yoki 'Axborot xavfsizligi kursi')",
  "company": "Kompaniya yoki tashkilot nomi (agar bo'lmasa 'Noma\\'lum')",
  "location": "Joylashuv (masalan: 'Toshkent', 'Remote', 'O\\'zbekiston')",
  "salary": "Maosh miqdori va valyutasi, 'Unpaid' yoki 'Ko\\'rsatilmagan'",
  "experience_required": "Talab qilingan tajriba (masalan: '0-1 yil', 'Talabalar uchun', 'Tajribasiz')",
  "key_requirements": "Asosiy talablar (qisqa, 1-2 qatorda)",
  "deadline": "Topshirish muddati (agar bo'lsa, aks holda 'Ko\\'rsatilmagan')",
  "why_matches": [
    "Nega {name}ga mosligi haqida 2-3 ta qisqa punkt"
  ],
  "action_advice": "Amaliy, jonli maslahat (masalan: 'Talablar sohangizga mos keladi. Talaba bo\\'lsangiz ham aloqaga chiqib ko\\'ring, grafikni kelishib olish imkoni bo\\'lishi mumkin. Rezyume yuborishni tavsiya qilaman' yoki 'Sertifikatli nufuzli kurs, bilimlarni mustahkamlash uchun qatnashish foydali')",
  "drawbacks": "Kamchilik yoki ogohlantirish (masalan: 'Rus tili B2 talab qilinadi', 'Haftasiga 40 soat', agar yo'q bo'lsa '')"
}}
"""
    return prompt
