#!/data/data/com.termux/files/usr/bin/bash

echo "================================================="
echo "   Jarvis AI - Internet Orqali Yangilash (OTA)"
echo "================================================="
echo ""

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CURRENT_DIR"

# 1. Agar loyiha Git orqali klon qilingan bo'lsa:
if [ -d ".git" ]; then
    echo "📡 GitHub'dan yangi kodlar olinmoqda (git pull)..."
    git pull origin main || git pull origin master
    echo "✅ Kodlar muvaffaqiyatli yangilandi!"
else
    # 2. Agar .git bo'lmasa, to'g'ridan-to'g'ri repo'dan yangilash:
    REPO_URL=""
    if [ -f ".env" ]; then
        REPO_URL=$(grep "^GITHUB_REPO_URL=" .env | cut -d '=' -f2 | tr -d ' "')
    fi
    if [ -z "$REPO_URL" ]; then
        REPO_URL="https://github.com/orifxon05/assistant.git"
    fi

    UPDATED=0
    if [ -n "$REPO_URL" ]; then
        echo "📡 Repositoriyadan yangilanishlar yuklanmoqda: $REPO_URL ..."
        TMP_DIR=$(mktemp -d)
        if git clone --depth 1 "$REPO_URL" "$TMP_DIR" 2>/dev/null; then
            cp -r "$TMP_DIR/intelligence" .
            cp "$TMP_DIR/bot.py" .
            cp "$TMP_DIR/requirements.txt" . 2>/dev/null
            cp "$TMP_DIR/setup.sh" .
            cp "$TMP_DIR/update.sh" .
            cp "$TMP_DIR/test_intelligence.py" .
            if [ ! -f "profile.json" ]; then
                cp "$TMP_DIR/profile.json" .
            fi
            rm -rf "$TMP_DIR"
            echo "✅ GitHub'dan fayllar yangilandi!"
            UPDATED=1
        else
            rm -rf "$TMP_DIR"
        fi
    fi

    # 3. Agar jarvis_update.zip fayli mavjud bo'lsa:
    if [ "$UPDATED" -eq 0 ]; then
        ZIP_FOUND=""
        for z in "jarvis_update.zip" "../jarvis_update.zip" "$HOME/storage/downloads/jarvis_update.zip" "$HOME/downloads/jarvis_update.zip"; do
            if [ -f "$z" ]; then
                ZIP_FOUND="$z"
                break
            fi
        done

        if [ -n "$ZIP_FOUND" ]; then
            echo "📦 Topilgan '$ZIP_FOUND' faylidan yangilanmoqda..."
            unzip -o "$ZIP_FOUND" -x ".env" "*.session*" "history.json" "contacts.json" "profile.json" 2>/dev/null
            echo "✅ Zip faylidan yangilandi!"
        fi
    fi
fi

# Kutubxonalarni tekshirish va yangilash
echo ""
echo "📦 Kutubxonalar tekshirilmoqda..."
pip install --upgrade requests python-dotenv telethon rapidfuzz > /dev/null 2>&1

echo ""
echo "================================================="
echo "✅ Yangilash muvaffaqiyatli yakunlandi!"
echo "Botni ishga tushirish uchun: jarvis"
echo "================================================="
