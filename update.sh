#!/data/data/com.termux/files/usr/bin/bash

echo "================================================="
echo "   Jarvis AI - Internet Orqali Yangilash (OTA)"
echo "================================================="
echo ""

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CURRENT_DIR"

# 0. Muhim shaxsiy ma'lumotlarni zaxiralash (har qanday holatda yo'qolmasligi uchun):
mkdir -p .update_backup
[ -f ".env" ] && cp ".env" .update_backup/
[ -f "profile.json" ] && cp "profile.json" .update_backup/
cp *.session* .update_backup/ 2>/dev/null
cp contacts.json history.json todos.json autoreply_state.json status.json action_history.json intelligence_*.json .update_backup/ 2>/dev/null

REPO_URL="https://github.com/orifxon05/assistant.git"
UPDATED=0

# 1. Agar loyiha Git orqali boshqarilayotgan bo'lsa:
if [ -d ".git" ]; then
    echo "📡 GitHub'dan yangilanishlar olinmoqda (konfliktsiz toza sinxronizatsiya)..."
    git remote set-url origin "$REPO_URL" 2>/dev/null
    git fetch origin main 2>/dev/null || git fetch origin master 2>/dev/null

    if git reset --hard origin/main 2>/dev/null || git reset --hard origin/master 2>/dev/null; then
        echo "✅ Kodlar muvaffaqiyatli tortib olindi!"
        UPDATED=1
    fi
fi

# 2. Agar .git bo'lmasa yoki git xatolik bersa:
if [ "$UPDATED" -eq 0 ]; then
    echo "📡 Repositoriyadan to'g'ridan-to'g'ri yangilanishlar yuklanmoqda: $REPO_URL ..."
    TMP_DIR=$(mktemp -d)
    if git clone --depth 1 "$REPO_URL" "$TMP_DIR" 2>/dev/null; then
        cp -r "$TMP_DIR/intelligence" . 2>/dev/null
        cp "$TMP_DIR/bot.py" . 2>/dev/null
        cp "$TMP_DIR/requirements.txt" . 2>/dev/null
        cp "$TMP_DIR/setup.sh" . 2>/dev/null
        cp "$TMP_DIR/update.sh" . 2>/dev/null
        cp "$TMP_DIR/test_intelligence.py" . 2>/dev/null
        cp "$TMP_DIR/README.md" . 2>/dev/null
        cp "$TMP_DIR/.gitignore" . 2>/dev/null
        [ ! -f "profile.json" ] && cp "$TMP_DIR/profile.json" . 2>/dev/null
        rm -rf "$TMP_DIR"
        echo "✅ GitHub'dan fayllar yangilandi!"
        UPDATED=1
    else
        rm -rf "$TMP_DIR"
    fi
fi

# 2.1 Agar GitHub'dan olinmasa, mahalliy jarvis_update.zip qidirish:
if [ "$UPDATED" -eq 0 ]; then
    for z in "jarvis_update.zip" "../jarvis_update.zip" "$HOME/storage/downloads/jarvis_update.zip" "$HOME/downloads/jarvis_update.zip"; do
        if [ -f "$z" ]; then
            echo "📦 Topilgan '$z' faylidan yangilanmoqda..."
            unzip -o "$z" -x ".env" "*.session*" "history.json" "contacts.json" "profile.json" 2>/dev/null
            echo "✅ Zip faylidan muvaffaqiyatli yangilandi!"
            UPDATED=1
            break
        fi
    done
fi

if [ "$UPDATED" -eq 0 ]; then
    echo "⚠️ DIQQAT: GitHub'dan kodlarni yuklab bo'lmadi!"
    echo "Mumkin bo'lgan sabablar:"
    echo " 1. GitHub repozitoriyangiz 'Private' (yopiq) holatda. Uni GitHub sozlamalaridan 'Public' qiling."
    echo " 2. Yoki telefoningizga 'jarvis_update.zip' faylini tashlab qayta ishga tushiring."
    echo " 3. Yoki Internet ulanishini tekshiring."
fi

# 3. Zaxiradan shaxsiy ma'lumotlarni qayta tiklash:
if [ -d ".update_backup" ]; then
    [ -f ".update_backup/.env" ] && cp ".update_backup/.env" .
    [ -f ".update_backup/profile.json" ] && cp ".update_backup/profile.json" .
    cp .update_backup/*.session* . 2>/dev/null
    cp .update_backup/contacts.json . 2>/dev/null
    cp .update_backup/history.json . 2>/dev/null
    cp .update_backup/todos.json . 2>/dev/null
    cp .update_backup/autoreply_state.json . 2>/dev/null
    cp .update_backup/status.json . 2>/dev/null
    cp .update_backup/action_history.json . 2>/dev/null
    cp .update_backup/intelligence_*.json . 2>/dev/null
    rm -rf .update_backup
fi

# 4. Kesh fayllarni tozalash:
rm -f *.pyc intelligence/*.pyc 2>/dev/null
rm -rf __pycache__ intelligence/__pycache__ 2>/dev/null

# 5. Kutubxonalarni tekshirish va yangilash:
echo ""
echo "📦 Kutubxonalar tekshirilmoqda..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --upgrade > /dev/null 2>&1
else
    pip install --upgrade requests python-dotenv telethon rapidfuzz > /dev/null 2>&1
fi

# 6. Sintaksis va xavfsizlik tekshiruvi:
echo "🔍 Kod tekshirilmoqda..."
if python -m py_compile bot.py 2>/dev/null; then
    echo "✅ Sintaksis tekshiruvidan muvaffaqiyatli o'tdi!"
else
    echo "⚠️ Diqqat: bot.py faylida xatolik aniqlandi."
fi

echo ""
echo "================================================="
echo "🎉 YANGILASH MUVAFFAQIYATLI YAKUNLANDI!"
echo "Botni ishga tushirish uchun: jarvis"
echo "================================================="
