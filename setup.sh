#!/data/data/com.termux/files/usr/bin/bash

echo "================================================="
echo "   Jarvis AI Assistant - O'rnatish Skripti"
echo "================================================="
echo ""

echo "1/4: Tizim paketlarini yangilash..."
pkg update -y && pkg upgrade -y
pkg install python git nano nodejs-lts -y

echo ""
echo "2/4: Python va Node.js kutubxonalarini o'rnatish..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install requests python-dotenv telethon rapidfuzz psycopg2-binary
fi

if [ -d "toyona" ] && [ -f "toyona/package.json" ]; then
    echo "📦 To‘yona Mini App kutubxonalari o'rnatilmoqda..."
    (cd toyona && npm install --silent)
fi

echo ""
echo "3/4: Sozlamalar va API kalitlari (.env)"
echo "-------------------------------------------------"

# Agar boshqa telefondan tayyor sessiya fayli nusxalangan bo'lsa:
if [ -f "orifxon_session.session" ] || [ -f "jarvis_session.session" ]; then
    echo "⚠️ Diqqat: Mavjud Telegram sessiya fayli topildi."
    read -p "Bu yangi hisobmi? Yangi login qilish uchun eski sessiya o'chirilsinmi? (h/y) [standart: h]: " RESET_SESS
    RESET_SESS=${RESET_SESS:-h}
    if [ "$RESET_SESS" = "h" ] || [ "$RESET_SESS" = "H" ] || [ "$RESET_SESS" = "ha" ]; then
        rm -f *.session *.session-journal 2>/dev/null
        echo "✅ Eski sessiya tozalandi. Birinchi ishga tushganda o'z raqamingiz so'raladi."
    fi
fi

read -p "Telegram Bot Token (BotFather'dan): " BOT_TOKEN
read -p "Groq API Key (console.groq.com): " GROQ_KEY
read -p "Telegram API ID (my.telegram.org - 7-8 xonali son): " API_ID

while [ -n "$API_ID" ] && [ "$API_ID" -gt 2147483647 ] 2>/dev/null; do
    echo "❌ XATO: Kiritilgan API_ID ($API_ID) juda katta son!"
    echo "Siz adashib o'z Telegram profil ID (Admin ID) yoki telefon raqamingizni kiritdingiz."
    echo "API_ID faqat https://my.telegram.org saytidan olinadi (masalan: 28491024)."
    read -p "Iltimos, to'g'ri API_ID ni kiriting (my.telegram.org): " API_ID
done

read -p "Telegram API Hash (my.telegram.org): " API_HASH
read -p "Ismingiz (masalan: Rustam) [standart: Telegram profilingizdan olinadi]: " OWNER_NAME
OWNER_NAME=${OWNER_NAME:-Foydalanuvchi}
read -p "To‘yona Neon Database URL (bo'sh qoldirsangiz keyin .env ga kiritishingiz mumkin): " TOYONA_DB_URL


cat > .env << ENVEOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
GROQ_API_KEY=$GROQ_KEY
TELEGRAM_API_ID=$API_ID
TELEGRAM_API_HASH=$API_HASH
ADMIN_ID=$ADMIN_ID
OWNER_NAME=$OWNER_NAME
SESSION_NAME=jarvis_session
TOYONA_PORT=3000
TOYONA_DATABASE_URL=$TOYONA_DB_URL
TOYONA_WEBAPP_URL=
ENVEOF

echo ""
echo "✅ .env fayli muvaffaqiyatli yaratildi!"

echo ""
echo "4/4: 'jarvis' buyrug'ini Termux tizimiga biriktirish..."

RUNNER_PATH="$PREFIX/bin/jarvis"
CURRENT_DIR=$(pwd)

cat > "$RUNNER_PATH" << 'RUNNEREOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null
CURRENT_DIR="__DIR__"
cd "$CURRENT_DIR"

if [ "$1" = "update" ]; then
    bash update.sh
else
    python bot.py
fi
RUNNEREOF

sed -i "s|__DIR__|$CURRENT_DIR|g" "$RUNNER_PATH"
chmod +x "$RUNNER_PATH"

echo "✅ 'jarvis' buyrug'i o'rnatildi!"
echo ""
echo "================================================="
echo "BARCHA SOZLAMALAR TAYYOR!"
echo "================================================="
echo ""
echo "Foydali buyruqlar:"
echo "👉 jarvis         - Botni ishga tushirish"
echo "👉 jarvis update  - Internet orqali kodni yangilash"
echo "👉 jarvis"
echo "deb yozsangiz bot avtomatik ishga tushadi!"
echo ""
echo "Birinchi marta ishga tushganda telefon raqamingiz va"
echo "Telegram'dan kelgan SMS-kod so'raladi (Telethon uchun)."
echo "================================================="
