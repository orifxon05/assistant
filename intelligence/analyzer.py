import os
import re
import json
import requests
from .config import build_analyzer_system_prompt, load_user_profile
from .preferences import load_preferences

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

FAST_IGNORE_KEYWORDS = [
    "stavka", "1xbet", "melbet", "parimatch", "kazino", "qimor",
    "kripto signal", "pump and dump", "tekin tarmoq", "vzlom instagram",
    "obunachi ko'paytirish", "like yig'ish", "erotik", "18+"
]

def fast_pre_filter(text):
    """
    Tezkor dastlabki tekshiruv. Agar post juda qisqa bo'lsa yoki spam/kazino bo'lsa darhol rad etadi.
    """
    if not text or len(text.strip()) < 30:
        return False, "Matn juda qisqa"

    lower_text = text.lower()
    for bad_kw in FAST_IGNORE_KEYWORDS:
        if bad_kw in lower_text:
            return False, f"Spam/reklama kalit so'zi ({bad_kw})"

    return True, "O'tdi"

def clean_json_response(raw_response):
    """
    Groq javobidan JSON blokini ajratib oladi.
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

    # Trim to outer braces if any trailing text
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end+1]

    try:
        return json.loads(raw)
    except Exception as e:
        print("[ANALYZER] JSON parse xatolik:", e, "Raw:", raw[:150])
        return None

def analyze_post_with_ai(post_text, channel_title="Kanal", channel_intent="all"):
    """
    Postni Groq LLM orqali tahlil qiladi va strukturalangan tahlil natijasini qaytaradi.
    """
    is_valid, reason = fast_pre_filter(post_text)
    if not is_valid:
        return {
            "is_relevant": False,
            "relevance_score": 0,
            "level": "IGNORE",
            "reason": reason
        }

    profile = load_user_profile()
    system_prompt = build_analyzer_system_prompt(profile)

    prefs = load_preferences()
    disliked = prefs.get("disliked_keywords", [])
    boosted = prefs.get("boosted_keywords", [])

    extra_intent_instruction = ""
    if channel_intent and channel_intent != "all":
        extra_intent_instruction = f"\nEslatma: Foydalanuvchi bu manbadan faqat '{channel_intent}' yo'nalishidagi postlarni kutmoqda."

    user_prompt = f"""[Manba: {channel_title}]{extra_intent_instruction}

Quyidagi Telegram postini tahlil qil va faqat JSON qaytar:

---
{post_text}
---"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        data = response.json()
        if "choices" in data and data["choices"]:
            reply_content = data["choices"][0]["message"]["content"]
            result = clean_json_response(reply_content)
            if result:
                # Apply feedback score adjustments
                score = result.get("relevance_score", 0)
                text_lower = post_text.lower()
                for b in boosted:
                    if b in text_lower:
                        score = min(100, score + 10)
                for d in disliked:
                    if d in text_lower:
                        score = max(0, score - 25)

                result["relevance_score"] = score
                if score >= 90:
                    result["level"] = "URGENT"
                    result["is_relevant"] = True
                elif score >= 80:
                    result["level"] = "USEFUL"
                    result["is_relevant"] = True
                elif score >= 60:
                    result["level"] = "MAYBE"
                    result["is_relevant"] = True
                else:
                    result["level"] = "IGNORE"
                    result["is_relevant"] = False

                return result
            else:
                print("[ANALYZER] AI javobi JSON ga aylanmadi")
        elif "error" in data:
            print("[ANALYZER GROQ XATO]:", data["error"].get("message"))
    except Exception as e:
        print("[ANALYZER] Groq chaqiruvida xatolik:", e)

    return {
        "is_relevant": False,
        "relevance_score": 0,
        "level": "IGNORE",
        "error": "Tahlil jarayonida xatolik yuz berdi"
    }
