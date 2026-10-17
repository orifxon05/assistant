# 🤖 Jarvis AI Assistant & Telegram Userbot

**Jarvis** — bu shaxsiy aqlli Telegram assistenti va userbot tizimi. U Termux (Android) va Linux muhitida to'liq avtonom ishlaydi.

---

## 🌟 Asosiy Imkoniyatlar

1. **💬 Tirik va Aqlli Avtojavob (Userbot):**
   - Oflayn vaqtingizda shaxsiy hisobingizga kelgan xabarlarga xuddi tirik insondek tabiiy, muloyim va aqlli javob qaytaradi.
   - Har bir suhbatdosh uchun kunlik limit va kontakt filtrlari (faqat tanlanganlarga yoki tanlanganlardan tashqari hammaga).
   - Suhbat yakunlangach, egasiga 3 soniyada tushunarli **ixcham hisobot** tayyorlab yuboradi.

2. **⚙️ To'liq Telegram Boshqaruvi:**
   - Profil, bio, ism-familiya, username, fotosuratlar.
   - Maxfiylik va xavfsizlik (2FA holati, seanslar, bloklanganlar).
   - Chat papkalari (folderlar), kanallar, guruhlar, bildirishnomalar va akkaunt TTL boshqaruvi.

3. **🔄 Avtomatik Yangilanish (OTA):**
   - Kodlardagi yangilanishlarni GitHub orqali bot menyusidan bir tugma orqali yoki Termux terminalidan tortib olish.

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
*Skript barcha kerakli paketlarni o'rnatadi, sizdan Bot Token, Groq API, API ID/Hash va Ismingizni so'rab `.env` faylini avtomatik yaratadi.*

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

* `jarvis` — Botni ishga tushirish
* `jarvis update` — GitHub'dan yangilanishlarni olish
* `/menu` — Telegramda boshqaruv menyusini ochish
* `/version` — Versiya va tizim holatini tekshirish
* `/update` — Tizimni yangilash
