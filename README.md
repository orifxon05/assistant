# 🤖 Jarvis AI Assistant & Telegram Intelligence Monitor

**Jarvis** — bu shaxsiy Telegram assistenti va aqlli kanallar monitoringi tizimi. U Termux (Android) va Linux muhitida to'liq avtonom ishlaydi.

---

## 🌟 Asosiy Imkoniyatlar

1. **📂 Telegram Intelligence Monitoring:**
   - Telegramdagi `📂 Intelligence` papkasiga qo'shilgan barcha kanallarni avtomatik kuzatadi.
   - Har bir yangi postni AI (Groq) orqali chuqur tahlil qiladi (spam, kazino va keraksiz reklamalarni avtomatik filtrlaydi).
   - Sizning yo'nalishingiz (Cybersecurity, Python Backend, AI, Frontend, Mobile...) bo'yicha eng mos **Vakansiyalar**, **Internship/Amaliyotlar**, **Bepul kurslar** va **Grantlar**ni saralab Telegramga yetkazadi.
   - Har bir e'lon uchun **🧠 Jarvis amaliy xulosasi va maslahati**ni yozib beradi (masalan: *"Talablar mos, talaba bo'lsangiz ham aloqaga chiqib grafikni kelishib ko'ring"*).

2. **🎯 Shaxsiy Qiziqishlar Testi (Anketa):**
   - Birinchi ishga tushganda yoki istalgan payt `/quiz` buyrug'i orqali qiziqishlaringizni aniqlaydi.
   - Soha, maqsad (Ish, Kurs, Grant, Amaliyot), tajriba va joylashuvni alohida inobatga oladi.

3. **💬 Tirik va Aqlli Avtojavob (Userbot):**
   - Oflayn vaqtingizda shaxsiy hisobingizga kelgan xabarlarga xuddi tirik yordamchidek muloyim va zehnli javob qaytaradi.
   - Suhbat tugagach, egasiga 3 soniyada tushunarli **ixcham hisobot** yuboradi.

4. **⚡ To'liq Telegram Boshqaruvi:**
   - Profil, bio, ism-familiya, username, fotosuratlar, 2FA holati, maxfiylik, papkalar, seanslar va guruhlarni bot menyusi orqali boshqarish.

---

## 🚀 O'rnatish (Termux - Android)

### 1. Repositoriyani klon qilish:
```bash
git clone https://github.com/USERNAME/REPO_NAME.git jarvis
cd jarvis
```

### 2. O'rnatish skriptini ishga tushirish:
```bash
bash setup.sh
```
*Skript barcha paketlarni o'rnatadi, sizdan Bot Token, Groq API, API ID/Hash va Ismingizni so'rab `.env` faylini avtomatik yaratadi.*

### 3. Botni ishga tushirish:
```bash
jarvis
```

---

## 🔄 Yangilanishlarni olish (OTA Update)

Koddagi yangilanishlarni bir zumda tortib olish uchun:
```bash
jarvis update
# yoki
bash update.sh
```
*(Bu buyruq sizning shaxsiy `.env` va sessiyangizga tegmasdan, faqat yangi kodlarni yangilab beradi).*

---

## 📌 Foydali Buyruqlar

* `jarvis` — Botni fonda ishga tushirish
* `jarvis update` — GitHub'dan yangilanishlarni olish
* `jarvis test` — Dry-run xavfsiz tahlil testini o'tkazish
* `/menu` — Telegramda boshqaruv menyusini ochish
* `/tahlil` — Kuzatuvdagi barcha kanallarni oxirgi 24 soatlik postlarini darhol tahlil qilish
* `/quiz` — Qiziqishlar anketasini qayta topshirish
