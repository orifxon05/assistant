# To‘yona hisobi — Telegram Mini App

Telegram Mini App uchun deploy qilishga tayyor boshlang‘ich loyiha:
- Mobilga mos, o‘zbekcha interfeys
- Telegram `initData` serverda tekshiriladi
- PostgreSQL orqali bulutli saqlash va qurilmalararo sinxronlash
- Oshnalar, to‘ylar, to‘yona yozuvlari, qidiruv va tahrirlash
- To‘y bo‘yicha jami so‘m/kg, minimum to‘yona va qarzdorlik ko‘rsatkichlari
- CSV hisobot yuklab olish
- Muhim yozuvlarni tasodifiy o‘chirishdan tasdiq

## Arxitektura
- `public/`: oddiy JavaScript frontend, Telegram WebApp SDK
- `server.js`: Express API, Telegram initData tekshiruvi
- `db.js`: PostgreSQL jadval va migratsiya
- `Dockerfile` + `docker-compose.yml`: mahalliy ishga tushirish

> Muhim: bulutda ishlashi uchun server va PostgreSQL’ni Render, Railway, Fly.io yoki boshqa HTTPS qo‘llaydigan hostingga joylashtiring. Bu loyiha foydalanuvchi ma’lumotlarini server tomonida ajratadi. Bir Telegram bot uchun bir nechta foydalanuvchi ishlatganda, har birining ma’lumoti o‘z Telegram ID’si bilan ajratiladi.

## 1. Telegram bot yaratish
1. Telegram’da `@BotFather` orqali bot yarating.
2. Bot tokenini oling.
3. Mini App URL uchun deploy qilingan HTTPS manzilni ishlating.
4. BotFather → bot → Bot Settings → Menu Button orqali Mini App URL’ni belgilang.

## 2. Muhit sozlamalari
`.env.example` faylini `.env` nomiga ko‘chiring va qiymatlarni kiriting:
- `BOT_TOKEN`: BotFather tokeni
- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: server porti

## 3. Ishga tushirish (Node.js 20+)
```bash
cp .env.example .env
npm install
npm run dev
```
Brauzerda local preview uchun `DEV_AUTH=true` va `DEV_TELEGRAM_ID=123456789` ni faqat lokal sinovda ishlating. Production’da `DEV_AUTH=false` bo‘lishi shart.

## 4. Docker orqali
```bash
cp .env.example .env
docker compose up --build
```
Docker Compose PostgreSQL va serverni ishga tushiradi. `.env` dagi `DATABASE_URL` qiymatini Compose tarmog‘i uchun `postgres://toyona:toyona_local_password@db:5432/toyona` qilib qo‘ying.

## Hisoblash qoidalari
- Har bir to‘yona yozuvi **so‘mda** saqlanadi.
- To‘y sanasidagi go‘sht narxi va kilogramm ekvivalenti tarixiy yozuv sifatida saqlanadi.
- Bugungi narx faqat umumiy ko‘rsatkichni taxminiy baholash uchun ishlatiladi.
- “Qarzdorlik” bu ilovada ikki alohida ko‘rsatkich: (1) do‘stning har bir to‘yda bergan to‘yonasi, (2) uning o‘z to‘yida avvalgi to‘yonalarni qaytarish uchun tavsiya etiladigan summa. Bu ijtimoiy kelishuvni avtomatik majburiyat deb talqin qilmaydi.
- Har bir do‘st uchun qaytarish tavsiyasi: avvalgi to‘ylarda ushbu do‘st bergan kg ekvivalentlari yig‘indisi × hozir tanlangan narx. Do‘stning o‘z to‘yida kiritilgan to‘yona bu tavsiyadan ayriladi.

## Production eslatmalari
- `BOT_TOKEN` va `DATABASE_URL` ni hech qachon frontendga joylamang.
- HTTPS majburiy.
- Hostingda avtomatik backup va PostgreSQL backup yoqing.
- Birinchi deploydan oldin test ma’lumotlari bilan qarzdorlik formulalarini tekshiring.
