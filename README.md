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

4. **💒 To‘yona Hisobi (Telegram Mini App):**
   - To‘ylar, oshnalar va to‘yona qarzlarini go‘sht ekvivalenti (kg) bo‘yicha aniq hisoblash.
   - Bulutli **Neon PostgreSQL** bazasiga ulangan — telefon alishsa yoki format bo‘lsa ham barcha hisoblar saqlanib qoladi.
   - Termux ichida `jarvis` ishga tushganda Mini App serveri ham lokal ishga tushadi (30-50 soniyalik kutish yoki uxlab qolishlar yo‘q).
   - `/toyona_backup` buyrug‘i bilan istalgan vaqtda barcha ma'lumotlarni JSON fayl ko‘rinishida Telegramga yuklab olib, zaxiraga saqlash mumkin.

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
*Skript barcha kerakli paketlarni (Python, Node.js) o'rnatadi, sizdan kerakli kalitlarni so'rab `.env` faylini avtomatik yaratadi.*

### 3. Botni ishga tushirish:
```bash
jarvis
```

---

## 🌐 Mini App’ni Telegramga ulash (Cloudflare Tunnel)

Mini App Telegram ichida chiroyli oynada ochilishi uchun bepul HTTPS tunnel ishlatiladi:
```bash
pkg install cloudflared
cloudflared tunnel --url http://localhost:3000
```
Chiqqan `https://....trycloudflare.com` manzilini `.env` fayliga `TOYONA_WEBAPP_URL` sifatida qo‘shing yoki BotFather orqali Menu Button qilib sozlang.

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

* `jarvis` — Bot va To‘yona serverini ishga tushirish
* `jarvis update` — GitHub'dan yangilanishlarni olish
* `/menu` — Telegramda boshqaruv menyusini ochish
* `/toyona` — To‘yona hisobi Mini App holati va menyusi
* `/toyona_backup` — Neon bazasidagi to‘yona ma'lumotlarini JSON fayl qilib Telegramga jo‘natish
* `/version` — Versiya va tizim holatini tekshirish
* `/update` — Tizimni yangilash

