# -*- coding: utf-8 -*-
"""
test_matcher.py - Test suite for vacancy_matcher.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from vacancy_matcher import match_vacancy_with_profile, format_match_report

# 1-misol: Vaqt mos (14:00 - 18:00, SOC Analyst, Toshkent)
SAMPLE_VACANCY_MATCH = """
Kompaniya: Uzcard Cyber
Lavozim: Junior SOC Analyst
Joylashuv: Toshkent, Chilonzor tumani
Format: Office
Ish vaqti: 14:00 - 18:00
Maosh: $700 - $1000
Tajriba: 0-1 yil (Junior)
Talablar: Python, Linux, SIEM, Wazuh, TCP/IP
Aloqa: @uzcard_hr
"""

# 2-misol: Vaqt to'qnashadi (09:00 - 18:00, o'qish 07:00-13:00 bilan 4 soat to'qnashuv)
SAMPLE_VACANCY_CONFLICT = """
Kompaniya: Bank Ipak Yo'li
Lavozim: Junior SOC Analyst
Joylashuv: Toshkent, Shayxontohur tumani
Format: Office
Ish vaqti: 09:00 - 18:00
Maosh: $800
Tajriba: 1 yil
Talablar: Python, Linux, SIEM, Wazuh, TCP/IP
Aloqa: @ipak_hr
"""

print("=== TEST 1: VAQT MOS (14:00 - 18:00) ===")
res1 = match_vacancy_with_profile(SAMPLE_VACANCY_MATCH)
print(format_match_report(res1))
print("\nOverall Status:", res1["overall_status"])
print("Time Status:", res1["criteria"]["schedule"]["status"])
assert res1["criteria"]["schedule"]["has_conflict"] is False, "Schedule should not have conflict"
assert res1["overall_status"] in ["🔥 Juda mos", "🟢 Mos"], "Overall status should be Juda mos or Mos"
print("TEST 1 PASSED!\n")

print("=== TEST 2: VAQT TO'QNASHADI (09:00 - 18:00) ===")
res2 = match_vacancy_with_profile(SAMPLE_VACANCY_CONFLICT)
print(format_match_report(res2))
print("\nOverall Status:", res2["overall_status"])
print("Time Status:", res2["criteria"]["schedule"]["status"])
print("Conflict Hours:", res2["criteria"]["schedule"]["conflict_hours"])
assert res2["criteria"]["schedule"]["has_conflict"] is True, "Schedule should have conflict"
assert res2["criteria"]["schedule"]["conflict_hours"] == 4.0, "Conflict hours should be 4.0"
assert res2["overall_status"] == "🔴 Mos emas", "Overall status should be Mos emas due to conflict"
print("TEST 2 PASSED!\n")

print("ALL VACANCY MATCHER TESTS PASSED SUCCESSFULLY!")
