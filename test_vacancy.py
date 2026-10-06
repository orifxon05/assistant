# -*- coding: utf-8 -*-
"""
test_vacancy.py - Test suite for vacancy_analyzer.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from vacancy_analyzer import analyze_vacancy, format_vacancy_summary, is_vacancy_post

SAMPLE_POST_1 = """
🏢 Kompaniya: "SecureTech LLC"
💼 Lavozim: Junior SOC Analyst
📍 Joylashuv: Toshkent, Chilonzor tumani
🏢 Ish shakli: Ofis (On-site), hybrid ham ko'rib chiqiladi
⏰ Ish vaqti: 09:00 - 18:00 (5/2)
💰 Maosh: $600 - $900
⏳ Tajriba: Kamida 1 yil (SOC yoki kiberxavfsizlikda)
🗣 Til bilish: Rus tili (erkin), Ingliz tili (B1)
🛠 Talablar:
- SIEM (Wazuh, Splunk) asoslari
- Linux (Ubuntu, Kali Linux) terminali
- TCP/IP, OSI tarmoq protokollari
- Python skriptlar
📅 Ariza muddati: 15-oktabrgacha
📩 Aloqa / Rezyume: @securetech_hr yoki cv@securetech.uz
"""

SAMPLE_POST_2 = """
#вакансия
Компания: Uzum Market
Вакансия: Python Backend Developer
Локация: Ташкент, Мирабадский район
Формат работы: Удаленно (Remote)
График: 10:00 - 19:00 (5/2)
Зарплата: от 12 000 000 до 18 000 000 сум
Опыт: от 1 до 3 лет
Требования: Python, FastAPI, PostgreSQL, Docker, Git.
Языки: Русский язык, Английский B2.
Дедлайн: 30-oktabr
Резюме отправлять: https://t.me/uzum_jobs_bot
"""

SAMPLE_POST_3 = """
Hiring: Junior Information Security Specialist
Company: Apex Fintech
Location: Tashkent
Work Type: Hybrid
Working hours: 09:00 - 18:00
Salary: $800 - $1200
Experience: 1-2 years
Skills needed: Network Security, Linux, Python, Git, Wireshark, SQL
Languages: English, Russian
Deadline: November 15
Apply here: https://apexfintech.com/careers
"""

print("=== TEST 1: IS_VACANCY_POST ===")
assert is_vacancy_post(SAMPLE_POST_1) is True
assert is_vacancy_post(SAMPLE_POST_2) is True
assert is_vacancy_post("Bugun havo juda yaxshi, hammaga xayrli kun!") is False
print("is_vacancy_post PASSED")

print("\n=== TEST 2: ANALYZE_VACANCY (POST 1 - SOC ANALYST) ===")
# We test with use_ai=False first to verify heuristic robustness, then with AI if available
data1 = analyze_vacancy(SAMPLE_POST_1, channel_title="Kiberxavfsizlik Ish", use_ai=False)
print(format_vacancy_summary(data1))

# Check all 11 fields
assert data1["title"] != "Ko'rsatilmagan", "Title missing"
assert "SecureTech" in data1["company"], "Company missing"
assert "Chilonzor" in data1["location"], "Location missing"
assert "Office" in data1["work_format"] or "Hybrid" in data1["work_format"], "Work format missing"
assert "09:00" in data1["working_hours"], "Working hours missing"
assert "$600" in data1["salary"] or "900" in data1["salary"], "Salary missing"
assert "1 yil" in data1["experience_required"], "Experience missing"
assert len(data1["language_requirements"]) >= 1, "Language requirements missing"
assert any(s in ["SIEM", "Wazuh", "Splunk", "Linux", "Python", "TCP/IP"] for s in data1["skill_requirements"]), "Skills missing"
assert "15-oktabr" in data1["deadline"], "Deadline missing"
assert "@securetech_hr" in data1["link"] or "cv@" in data1["link"], "Link missing"

# Check Uzbek aliases
assert data1["lavozim"] == data1["title"]
assert data1["kompaniya"] == data1["company"]
assert data1["joy"] == data1["location"]
assert data1["format"] == data1["work_format"]
assert data1["ish_vaqti"] == data1["working_hours"]
assert data1["maosh"] == data1["salary"]
assert data1["tajriba_talabi"] == data1["experience_required"]
assert data1["til_talabi"] == data1["language_requirements"]
assert data1["skill_talablari"] == data1["skill_requirements"]
print("Post 1 assertions PASSED")

print("\n=== TEST 3: ANALYZE_VACANCY (POST 2 - RUSSIAN VACANCY) ===")
data2 = analyze_vacancy(SAMPLE_POST_2, channel_title="DevJobs UZ", use_ai=False)
print(format_vacancy_summary(data2))
assert "Python" in data2["title"]
assert "Uzum" in data2["company"]
assert "Remote" in data2["work_format"]
assert "12 000 000" in data2["salary"]
assert "https://t.me/uzum_jobs_bot" in data2["link"]
print("Post 2 assertions PASSED")

print("\n=== TEST 4: ANALYZE_VACANCY (POST 3 - ENGLISH VACANCY) ===")
data3 = analyze_vacancy(SAMPLE_POST_3, channel_title="Apex Careers", use_ai=False)
print(format_vacancy_summary(data3))
assert "Information Security" in data3["title"] or "Security" in data3["title"]
assert "Apex" in data3["company"]
assert "Hybrid" in data3["work_format"]
assert "$800" in data3["salary"]
assert "Wireshark" in data3["skill_requirements"] or "Python" in data3["skill_requirements"]
print("Post 3 assertions PASSED")

print("\nALL VACANCY ANALYZER TESTS PASSED SUCCESSFULLY!")
