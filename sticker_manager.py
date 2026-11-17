import os
import io
import json
import time
import requests
from PIL import Image, ImageDraw, ImageOps, ImageFilter

STICKERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stickers")
DATA_FILE = os.path.join(STICKERS_DIR, "stickers_data.json")

def ensure_sticker_dirs():
    if not os.path.exists(STICKERS_DIR):
        os.makedirs(STICKERS_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        default_data = {
            "pack_name": "",
            "pack_title": "Orifxon Stikerlari",
            "pack_url": "",
            "stickers": [],
            "sound_stickers": []
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def load_sticker_data():
    ensure_sticker_dirs()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "pack_name": "",
            "pack_title": "Orifxon Stikerlari",
            "pack_url": "",
            "stickers": [],
            "sound_stickers": []
        }

def save_sticker_data(data):
    if not os.path.exists(STICKERS_DIR):
        os.makedirs(STICKERS_DIR, exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[STICKER DATA SAVE ERROR]: {e}")

# ─────────────────────────────────────────────────────────────
# 1. TASVIRNI STIKERGA AYLANTIRISH (STATIC STICKER)
# ─────────────────────────────────────────────────────────────
def convert_to_sticker(image_bytes, style="circle"):
    """
    Rasmni Telegram stiker talabiga (512x512, shaffof fon, oq hoshiya) moslashtiradi.
    style:
      - 'circle': Dumaloq qirqilgan, oq hoshiyali professional avatar stiker.
      - 'rounded': Yumaloq burchakli to'rtburchak stiker.
      - 'standard': Rasm proporsiyasini to'liq saqlagan holda 512x512 ga sig'dirish.
    Qaytaradi: (webp_bytes, png_bytes)
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    size = 512

    if style == "circle":
        # Markazdan kvadrat qirqish
        min_side = min(img.width, img.height)
        left = (img.width - min_side) // 2
        top = (img.height - min_side) // 2
        cropped = img.crop((left, top, left + min_side, top + min_side))
        
        # 480x480 ga kichraytirish (atrofiga oq hoshiya sig'ishi uchun)
        inner_size = 480
        cropped = cropped.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
        
        # Dumaloq maska
        mask = Image.new("L", (inner_size, inner_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, inner_size, inner_size), fill=255)
        
        # 512x512 kanvas yaratish
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(canvas)
        
        # Qalin oq hoshiya (border)
        cdraw.ellipse((6, 6, size - 6, size - 6), fill=(255, 255, 255, 255))
        # Nozik soya / kontur effekti
        cdraw.ellipse((8, 8, size - 8, size - 8), outline=(220, 220, 220, 255), width=2)
        
        # Rasmni markazga joylash
        offset = ((size - inner_size) // 2, (size - inner_size) // 2)
        canvas.paste(cropped, offset, mask)
        final_img = canvas

    elif style == "rounded":
        # Proporsiya bo'yicha sig'dirish (chekka hoshiya uchun 480 gacha)
        img.thumbnail((470, 470), Image.Resampling.LANCZOS)
        w, h = img.size
        radius = 32
        
        # Dumaloq burchak maskasi
        mask = Image.new("L", (w, h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
        
        # Oq hoshiyali kanvas
        bw, bh = w + 20, h + 20
        bcanvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(bcanvas)
        bdraw.rounded_rectangle((0, 0, bw, bh), radius=radius + 6, fill=(255, 255, 255, 255))
        bcanvas.paste(img, (10, 10), mask)
        
        # 512x512 markaziga joylash
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(bcanvas, ((size - bw) // 2, ((size - bh) // 2)))
        final_img = canvas

    else:
        # Standard fit: Asl nisbatni saqlab 512x512 gacha kattalashtirish/kichraytirish
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(img, ((size - img.width) // 2, ((size - img.height) // 2)))
        final_img = canvas

    # WEBP va PNG baytlarini chiqarish
    webp_io = io.BytesIO()
    final_img.save(webp_io, format="WEBP", quality=95)
    webp_bytes = webp_io.getvalue()

    png_io = io.BytesIO()
    final_img.save(png_io, format="PNG")
    png_bytes = png_io.getvalue()

    return webp_bytes, png_bytes

# ─────────────────────────────────────────────────────────────
# 2. RASMDAN ANIMATSION GIF STIKER YASASH
# ─────────────────────────────────────────────────────────────
def convert_to_gif(image_bytes, anim_type="pulse"):
    """
    Oddiy rasmdan animatsion GIF stiker yasaydi.
    anim_type:
      - 'pulse': Yaqinlashib-uzoqlovchi pulsatsiya (kattalashib-kichrayish)
      - 'shake': Kulgili silkinish / tebranish effekti
      - 'spin': 360 gradus yumshoq aylanish
      - 'heartbeat': Yurak urishi effekti
    """
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    size = 512
    # Animatsiya hoshiyadan chiqib ketmasligi uchun 420x420 ga sig'diramiz
    base.thumbnail((420, 420), Image.Resampling.LANCZOS)

    frames = []

    if anim_type == "pulse":
        steps = [1.0, 1.03, 1.07, 1.12, 1.18, 1.22, 1.18, 1.12, 1.07, 1.03]
        for s in steps:
            nw, nh = int(base.width * s), int(base.height * s)
            resized = base.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2))
            frames.append(canvas)

    elif anim_type == "shake":
        angles = [0, -4, -8, -5, 0, 5, 8, 4, 0]
        for a in angles:
            rot = base.rotate(a, resample=Image.Resampling.BICUBIC, expand=False)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(rot, ((size - rot.width) // 2, (size - rot.height) // 2))
            frames.append(canvas)

    elif anim_type == "spin":
        for i in range(12):
            deg = i * 30
            rot = base.rotate(-deg, resample=Image.Resampling.BICUBIC, expand=False)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(rot, ((size - rot.width) // 2, (size - rot.height) // 2))
            frames.append(canvas)

    elif anim_type == "heartbeat":
        # Tez 2 marta urish va tinch turish
        steps = [1.0, 1.15, 1.05, 1.22, 1.0, 1.0, 1.0, 1.0]
        for s in steps:
            nw, nh = int(base.width * s), int(base.height * s)
            resized = base.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2))
            frames.append(canvas)

    out = io.BytesIO()
    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=110,
        loop=0,
        disposal=2
    )
    return out.getvalue()

# ─────────────────────────────────────────────────────────────
# 3. TELEGRAM BOT API ORQALI YUBORISH VA YUKLAB OLISH
# ─────────────────────────────────────────────────────────────
def api_send_sticker(chat_id, sticker_input, reply_markup=None, bot_token=None):
    """
    Telegramga to'g'ridan-to'g'ri .WEBP stiker yuborish.
    sticker_input: fayl baytlari (bytes) yoki mavjud file_id (str)
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendSticker"
    try:
        data = {"chat_id": chat_id}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup

        if isinstance(sticker_input, (bytes, bytearray)):
            files = {"sticker": ("sticker.webp", sticker_input, "image/webp")}
            r = requests.post(url, data=data, files=files, timeout=20)
        else:
            data["sticker"] = str(sticker_input)
            r = requests.post(url, data=data, timeout=20)

        res = r.json()
        if res.get("ok"):
            file_id = res["result"].get("sticker", {}).get("file_id")
            return True, file_id, res["result"]
        return False, None, res.get("description", "Xatolik")
    except Exception as e:
        return False, None, str(e)

def api_send_animation(chat_id, animation_bytes_or_id, caption="", reply_markup=None, bot_token=None):
    """
    Telegramga animatsion GIF stiker yuborish.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendAnimation"
    try:
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup

        if isinstance(animation_bytes_or_id, (bytes, bytearray)):
            files = {"animation": ("sticker.gif", animation_bytes_or_id, "image/gif")}
            r = requests.post(url, data=data, files=files, timeout=30)
        else:
            data["animation"] = str(animation_bytes_or_id)
            r = requests.post(url, data=data, timeout=30)

        res = r.json()
        if res.get("ok"):
            file_id = res["result"].get("animation", {}).get("file_id")
            return True, file_id, res["result"]
        return False, None, res.get("description", "Xatolik")
    except Exception as e:
        return False, None, str(e)

def api_send_voice(chat_id, voice_file_id_or_bytes, caption="", reply_markup=None, bot_token=None):
    """
    Telegramga ovozli xabar (Voice) yuborish.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendVoice"
    try:
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup

        if isinstance(voice_file_id_or_bytes, (bytes, bytearray)):
            files = {"voice": ("voice.ogg", voice_file_id_or_bytes, "audio/ogg")}
            r = requests.post(url, data=data, files=files, timeout=30)
        else:
            data["voice"] = str(voice_file_id_or_bytes)
            r = requests.post(url, data=data, timeout=30)

        res = r.json()
        if res.get("ok"):
            file_id = res["result"].get("voice", {}).get("file_id")
            return True, file_id, res["result"]
        return False, None, res.get("description", "Xatolik")
    except Exception as e:
        return False, None, str(e)

def api_download_file(file_id, bot_token=None):
    """
    Telegram serveridan faylni file_id orqali yuklab olish.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    try:
        info_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        r = requests.get(info_url, timeout=15)
        res = r.json()
        if not res.get("ok"):
            return None, res.get("description", "Fayl topilmadi")
        
        file_path = res["result"]["file_path"]
        down_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        down_r = requests.get(down_url, timeout=40)
        if down_r.status_code == 200:
            return down_r.content, None
        return None, f"Yuklab olishda xatolik: HTTP {down_r.status_code}"
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────────────────
# 4. TELEGRAM STICKER PACK (TO'PLAM) YARATISH VA BOSHQARISH
# ─────────────────────────────────────────────────────────────
def get_or_create_pack_name(user_id, bot_username=None):
    """
    Stiker to'plami nomini generatsiya qilish.
    Telegram qoidasiga ko'ra: <name>_by_<bot_username>
    """
    clean_bot = (bot_username or "Orifxon_assistantbot").replace("@", "")
    data = load_sticker_data()
    if data.get("pack_name"):
        return data["pack_name"]
    # Unikal nom: u{user_id}_stickers_by_{bot}
    name = f"u{user_id}_stickers_by_{clean_bot}"
    data["pack_name"] = name
    data["pack_url"] = f"https://t.me/addstickers/{name}"
    save_sticker_data(data)
    return name

def api_add_sticker_to_pack(user_id, png_or_webp_bytes, emoji="✨", bot_token=None, bot_username="Orifxon_assistantbot"):
    """
    Stikerni Telegram stiker to'plamiga qo'shadi.
    Agar to'plam hali yaratilmagan bo'lsa, avval createNewStickerSet chaqiradi.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    pack_name = get_or_create_pack_name(user_id, bot_username)
    data = load_sticker_data()
    pack_title = data.get("pack_title", "Orifxon Stikerlari")

    # 1. To'plam mavjudligini tekshirish
    check_url = f"https://api.telegram.org/bot{token}/getStickerSet"
    pack_exists = False
    try:
        chk_r = requests.get(check_url, params={"name": pack_name}, timeout=15).json()
        if chk_r.get("ok"):
            pack_exists = True
    except Exception:
        pass

    # 2. Yangi yaratish yoki qo'shish
    if not pack_exists:
        # createNewStickerSet
        url = f"https://api.telegram.org/bot{token}/createNewStickerSet"
        # Modern Bot API: stickers parameter
        stickers_payload = json.dumps([{
            "sticker": "attach://stk_file",
            "emoji_list": [emoji],
            "format": "static"
        }])
        data_fields = {
            "user_id": user_id,
            "name": pack_name,
            "title": pack_title,
            "stickers": stickers_payload
        }
        files = {"stk_file": ("sticker.png", png_or_webp_bytes, "image/png")}

        try:
            r = requests.post(url, data=data_fields, files=files, timeout=30).json()
            if r.get("ok"):
                data["pack_url"] = f"https://t.me/addstickers/{pack_name}"
                save_sticker_data(data)
                return True, data["pack_url"], None

            # Fallback legacy: png_sticker
            legacy_data = {
                "user_id": user_id,
                "name": pack_name,
                "title": pack_title,
                "emojis": emoji
            }
            legacy_files = {"png_sticker": ("sticker.png", png_or_webp_bytes, "image/png")}
            lr = requests.post(url, data=legacy_data, files=legacy_files, timeout=30).json()
            if lr.get("ok"):
                data["pack_url"] = f"https://t.me/addstickers/{pack_name}"
                save_sticker_data(data)
                return True, data["pack_url"], None

            return False, None, r.get("description") or lr.get("description", "Yaratib bo'lmadi")
        except Exception as e:
            return False, None, str(e)

    else:
        # addStickerToSet
        url = f"https://api.telegram.org/bot{token}/addStickerToSet"
        # Modern Bot API: sticker parameter
        sticker_payload = json.dumps({
            "sticker": "attach://stk_file",
            "emoji_list": [emoji],
            "format": "static"
        })
        data_fields = {
            "user_id": user_id,
            "name": pack_name,
            "sticker": sticker_payload
        }
        files = {"stk_file": ("sticker.png", png_or_webp_bytes, "image/png")}

        try:
            r = requests.post(url, data=data_fields, files=files, timeout=30).json()
            if r.get("ok"):
                return True, data.get("pack_url", f"https://t.me/addstickers/{pack_name}"), None

            # Fallback legacy: png_sticker
            legacy_data = {
                "user_id": user_id,
                "name": pack_name,
                "emojis": emoji
            }
            legacy_files = {"png_sticker": ("sticker.png", png_or_webp_bytes, "image/png")}
            lr = requests.post(url, data=legacy_data, files=legacy_files, timeout=30).json()
            if lr.get("ok"):
                return True, data.get("pack_url", f"https://t.me/addstickers/{pack_name}"), None

            return False, None, r.get("description") or lr.get("description", "Qo'shib bo'lmadi")
        except Exception as e:
            return False, None, str(e)

# ─────────────────────────────────────────────────────────────
# 5. OVOZLI STIKERLAR (SOUND STICKERS) BOSHQARUVI
# ─────────────────────────────────────────────────────────────
def save_sound_sticker_pair(sticker_file_id, voice_file_id, title="Ovozli stiker", emoji="🎙️", duration=0):
    """
    Stiker va ovozli xabarni yagona juftlik qilib saqlaydi.
    """
    data = load_sticker_data()
    pair_id = f"snd_{int(time.time())}"
    pair = {
        "id": pair_id,
        "title": title,
        "emoji": emoji,
        "sticker_file_id": sticker_file_id,
        "voice_file_id": voice_file_id,
        "duration": duration,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    data["sound_stickers"].append(pair)
    save_sticker_data(data)
    return pair

def delete_sound_sticker(pair_id):
    data = load_sticker_data()
    data["sound_stickers"] = [s for s in data["sound_stickers"] if s["id"] != pair_id]
    save_sticker_data(data)

def send_sound_sticker_pair(chat_id, pair_id, bot_token=None):
    """
    Ovozli stikerni jo'natadi: oldin stiker, keyin unga biriktirilgan ovozli xabar ketma-ket.
    """
    data = load_sticker_data()
    pair = next((s for s in data["sound_stickers"] if s["id"] == pair_id), None)
    if not pair:
        return False, "Ovozli stiker topilmadi."

    # 1. Stikerni yuborish
    ok_stk, _, err1 = api_send_sticker(chat_id, pair["sticker_file_id"], bot_token=bot_token)
    # 2. Ovozni yuborish
    caption = f"{pair['emoji']} <b>{pair['title']}</b>"
    ok_vce, _, err2 = api_send_voice(chat_id, pair["voice_file_id"], caption=caption, bot_token=bot_token)
    return (ok_stk or ok_vce), None

# ─────────────────────────────────────────────────────────────
# 6. KLAVIATURALAR (UI KEYBOARDS)
# ─────────────────────────────────────────────────────────────
def get_sticker_main_menu_keyboard():
    data = load_sticker_data()
    stk_count = len(data.get("stickers", []))
    snd_count = len(data.get("sound_stickers", []))
    pack_name = data.get("pack_name", "")

    return {
        "inline_keyboard": [
            [
                {"text": "➕ Yangi stiker yaratish", "callback_data": "stk_create_static"},
                {"text": "🎞️ GIF stiker yasash", "callback_data": "stk_create_gif"}
            ],
            [
                {"text": f"🎙️ Ovozli stikerlar ({snd_count})", "callback_data": "stk_sound_menu"}
            ],
            [
                {"text": f"📦 Mening to‘plamim ({stk_count})", "callback_data": "stk_my_pack"}
            ],
            [
                {"text": "ℹ️ Qo‘llanma", "callback_data": "stk_help"},
                {"text": "⬅️ Bosh menyu", "callback_data": "open_menu"}
            ]
        ]
    }

def get_sticker_style_keyboard(temp_key):
    return {
        "inline_keyboard": [
            [{"text": "⚪ Dumaloq stiker (Oq hoshiyali)", "callback_data": f"stk_apply_circle_{temp_key}"}],
            [{"text": "📐 Asl ko‘rinish (To‘liq rasm)", "callback_data": f"stk_apply_standard_{temp_key}"}],
            [{"text": "🔲 Yumaloq burchakli stiker", "callback_data": f"stk_apply_rounded_{temp_key}"}],
            [{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]
        ]
    }

def get_gif_style_keyboard(temp_key):
    return {
        "inline_keyboard": [
            [{"text": "💓 Pulsatsiya (Kattalashib-kichrayish)", "callback_data": f"stk_gif_pulse_{temp_key}"}],
            [{"text": "⚡ Silkinish (Wiggle / Kulgili)", "callback_data": f"stk_gif_shake_{temp_key}"}],
            [{"text": "🔄 Aylanish (360° Spin)", "callback_data": f"stk_gif_spin_{temp_key}"}],
            [{"text": "❤️ Yurak urishi (Heartbeat)", "callback_data": f"stk_gif_heart_{temp_key}"}],
            [{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]
        ]
    }

def get_sticker_after_action_keyboard(stk_index):
    return {
        "inline_keyboard": [
            [
                {"text": "➕ To‘plamga qo‘shish (Pack)", "callback_data": f"stk_pack_add_{stk_index}"},
                {"text": "🎙️ Ovoz biriktirish", "callback_data": f"stk_attach_voice_{stk_index}"}
            ],
            [
                {"text": "🎞️ GIF stiker qilish", "callback_data": f"stk_make_gif_{stk_index}"}
            ],
            [
                {"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}
            ]
        ]
    }

def get_sound_stickers_keyboard():
    data = load_sticker_data()
    sound_list = data.get("sound_stickers", [])
    buttons = []

    # Har bir ovozli stiker uchun tugma
    for s in sound_list[:8]:
        title = s.get("title") or "Ovozli stiker"
        emoji = s.get("emoji") or "🎙️"
        buttons.append([
            {"text": f"{emoji} {title} (Yuborish)", "callback_data": f"stk_play_{s['id']}"},
            {"text": "🗑️", "callback_data": f"stk_del_sound_{s['id']}"}
        ])

    buttons.append([{"text": "➕ Yangi ovozli stiker yaratish", "callback_data": "stk_create_static"}])
    buttons.append([{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}])

    return {"inline_keyboard": buttons}

# ─────────────────────────────────────────────────────────────
# 7. ASOSIY MENYU VA CALLBACK HANDLERLAR
# ─────────────────────────────────────────────────────────────
TEMP_STICKER_STORAGE = {}

def send_sticker_main_menu(chat_id, send_message_fn):
    data = load_sticker_data()
    stk_count = len(data.get("stickers", []))
    snd_count = len(data.get("sound_stickers", []))
    pack_title = data.get("pack_title", "Orifxon Stikerlari")
    pack_url = data.get("pack_url")

    pack_info = f"<a href='{pack_url}'>{pack_title}</a>" if pack_url else f"<b>{pack_title}</b> (Hali yaratilmagan)"

    text = (
        "🎨 <b>Stiker Ustaxonasi (Sticker Studio)</b>\n\n"
        "O‘zingizning rasmlaringizdan shaxsiy Telegram stiker to‘plamini yarating, "
        "harakatlanuvchi GIF stikerlar yasang va stikerlarga ovozli xabar (Sound sticker) biriktiring!\n\n"
        f"📦 <b>To‘plam:</b> {pack_info}\n"
        f"🖼️ <b>Stikerlar:</b> {stk_count} ta\n"
        f"🎙️ <b>Ovozli stikerlar:</b> {snd_count} ta\n\n"
        "<i>Quyidagi menyudan kerakli amalni tanlang:</i>"
    )
    send_message_fn(chat_id, text, get_sticker_main_menu_keyboard(), parse_mode="HTML")

async def handle_sticker_callback(chat_id, data, callback_query, send_message_fn, pending_actions, bot_username="Orifxon_assistantbot", bot_token=None):
    if data == "stk_menu":
        send_sticker_main_menu(chat_id, send_message_fn)
        return

    if data == "stk_create_static":
        pending_actions[chat_id] = {"type": "stk_awaiting_photo", "mode": "static"}
        kb = {"inline_keyboard": [[{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]]}
        send_message_fn(
            chat_id,
            "📸 <b>Stiker uchun rasm yuboring:</b>\n\n"
            "Menga stiker qilmoqchi bo‘lgan rasmingizni yuboring (Oddiy rasm yoki Fayl ko‘rinishida).\n"
            "Bot uni avtomatik 512x512 stiker ko‘rinishiga keltiradi.",
            kb,
            parse_mode="HTML"
        )
        return

    if data == "stk_create_gif":
        pending_actions[chat_id] = {"type": "stk_awaiting_photo", "mode": "gif"}
        kb = {"inline_keyboard": [[{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]]}
        send_message_fn(
            chat_id,
            "🎞️ <b>GIF stiker uchun rasm yuboring:</b>\n\n"
            "Menga rasm yuboring, bot unga animatsiya (pulsatsiya, silkinish, aylanish) qo‘shib jonli GIF stiker yasab beradi.",
            kb,
            parse_mode="HTML"
        )
        return

    if data == "stk_my_pack":
        stk_data = load_sticker_data()
        stk_count = len(stk_data.get("stickers", []))
        pack_url = stk_data.get("pack_url")
        pack_title = stk_data.get("pack_title", "Orifxon Stikerlari")

        if pack_url:
            text = (
                f"📦 <b>Sizning Shaxsiy Stiker To‘plamingiz</b>\n\n"
                f"📌 <b>Nomi:</b> {pack_title}\n"
                f"🖼️ <b>Stikerlar soni:</b> {stk_count} ta\n"
                f"🔗 <b>Telegram havolasi:</b>\n<code>{pack_url}</code>\n\n"
                f"<i>Ushbu havolani bosib, to‘plamni o‘z Telegramingizga qo‘shib olishingiz va do‘stlaringizga ulashishingiz mumkin!</i>"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "🔗 To‘plamni ochish (Telegramda)", "url": pack_url}],
                    [{"text": "➕ Yangi stiker qo‘shish", "callback_data": "stk_create_static"}],
                    [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
                ]
            }
        else:
            text = (
                "📦 <b>Sizning Shaxsiy Stiker To‘plamingiz</b>\n\n"
                f"Sarlavha: <b>{pack_title}</b>\n\n"
                "Hali to‘plamga hech qanday stiker qo‘shilmagan.\n"
                "Birinchi rasmingizni stiker qilib, <b>➕ To‘plamga qo‘shish</b> tugmasini bossangiz, "
                "Telegramda sizning shaxsiy sticker pack'ingiz avtomatik yaratiladi va maxsus havola beriladi!"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "➕ Birinchi stikerni yaratish", "callback_data": "stk_create_static"}],
                    [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
                ]
            }
        send_message_fn(chat_id, text, kb, parse_mode="HTML")
        return

    if data == "stk_sound_menu":
        stk_data = load_sticker_data()
        sound_list = stk_data.get("sound_stickers", [])
        if not sound_list:
            text = (
                "🎙️ <b>Ovozli Stikerlar (Sound Stickers)</b>\n\n"
                "Sizda hali ovozli stikerlar mavjud emas.\n\n"
                "💡 <b>Bu qanday ishlaydi?</b>\n"
                "1. Avval rasmdan stiker yarating.\n"
                "2. <b>🎙️ Ovoz biriktirish</b> tugmasini bosing va ovozli xabar (Voice) yuboring.\n"
                "3. Bot stiker va ovozni juftlik qilib saqlaydi.\n"
                "4. Shunda bir tugmani bosish orqali ham stiker, ham ovozli xabar ketma-ket yuboriladi!"
            )
        else:
            text = (
                f"🎙️ <b>Mening Ovozli Stikerlarim ({len(sound_list)} ta)</b>\n\n"
                f"Quyidagi ro‘yxatdan birini tanlang — bot darhol stikerni va unga ulangan ovozli xabarni yuboradi:"
            )
        send_message_fn(chat_id, text, get_sound_stickers_keyboard(), parse_mode="HTML")
        return

    if data.startswith("stk_play_"):
        pair_id = data.replace("stk_play_", "")
        ok, err = send_sound_sticker_pair(chat_id, pair_id, bot_token=bot_token)
        if not ok:
            send_message_fn(chat_id, f"❌ Ovozli stikerni yuborishda xatolik: {err}")
        return

    if data.startswith("stk_del_sound_"):
        pair_id = data.replace("stk_del_sound_", "")
        delete_sound_sticker(pair_id)
        send_message_fn(chat_id, "🗑️ Ovozli stiker o‘chirildi.")
        stk_data = load_sticker_data()
        sound_list = stk_data.get("sound_stickers", [])
        send_message_fn(chat_id, f"🎙️ <b>Ovozli stikerlar ro‘yxati ({len(sound_list)} ta):</b>", get_sound_stickers_keyboard(), parse_mode="HTML")
        return

    if data.startswith("stk_apply_"):
        # Masalan: stk_apply_circle_123456
        parts = data.split("_")
        style = parts[2]
        temp_key = parts[3]
        photo_bytes = TEMP_STICKER_STORAGE.get(temp_key)

        if not photo_bytes:
            send_message_fn(chat_id, "⚠️ Rasm muddati tugagan. Iltimos, rasmni qaytadan yuboring.", get_sticker_main_menu_keyboard())
            return

        send_message_fn(chat_id, "⏳ Stiker tayyorlanmoqda...")
        webp_bytes, png_bytes = convert_to_sticker(photo_bytes, style=style)

        # Stiker sifatida jo'natish
        ok, file_id, res = api_send_sticker(chat_id, webp_bytes, bot_token=bot_token)

        stk_data = load_sticker_data()
        stk_id = f"stk_{int(time.time())}"
        
        # Faylni diskda saqlash
        local_filename = f"{stk_id}.png"
        local_path = os.path.join(STICKERS_DIR, local_filename)
        with open(local_path, "wb") as f:
            f.write(png_bytes)

        stk_entry = {
            "id": stk_id,
            "file_id": file_id or "",
            "local_path": local_path,
            "format": "static",
            "style": style,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        stk_data["stickers"].append(stk_entry)
        save_sticker_data(stk_data)

        # Temp Storage'da saqlab turish
        TEMP_STICKER_STORAGE[stk_id] = png_bytes

        caption_text = (
            "✅ <b>Stiker tayyor!</b>\n\n"
            "Endi ushbu stiker bilan nima qilmoqchisiz?\n"
            "• <b>➕ To‘plamga qo‘shish:</b> Telegram shaxsiy sticker pack'ingizga kiritadi\n"
            "• <b>🎙️ Ovoz biriktirish:</b> Ovozli xabar qo‘shib, Sound Sticker qiladi\n"
            "• <b>🎞️ GIF qilish:</b> Rasmni harakatlantirib, animatsion GIF stiker yasaydi"
        )
        send_message_fn(chat_id, caption_text, get_sticker_after_action_keyboard(stk_id), parse_mode="HTML")
        return

    if data.startswith("stk_gif_"):
        # Masalan: stk_gif_pulse_123456
        parts = data.split("_")
        anim_type = parts[2]
        temp_key = parts[3]
        photo_bytes = TEMP_STICKER_STORAGE.get(temp_key)

        if not photo_bytes:
            send_message_fn(chat_id, "⚠️ Rasm muddati tugagan. Iltimos, rasmni qaytadan yuboring.", get_sticker_main_menu_keyboard())
            return

        send_message_fn(chat_id, "⏳ Animatsion GIF stiker tayyorlanmoqda...")
        gif_bytes = convert_to_gif(photo_bytes, anim_type=anim_type)

        gif_id = f"gif_{int(time.time())}"
        local_filename = f"{gif_id}.gif"
        local_path = os.path.join(STICKERS_DIR, local_filename)
        with open(local_path, "wb") as f:
            f.write(gif_bytes)

        caption = "🎞️ <b>Animatsion GIF stiker tayyor!</b>\n\nUshbu GIF avtomatik aylanadi va uni saqlab olishingiz mumkin."
        kb = {
            "inline_keyboard": [
                [{"text": "➕ Yana stiker yaratish", "callback_data": "stk_create_static"}],
                [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
            ]
        }
        api_send_animation(chat_id, gif_bytes, caption=caption, reply_markup=kb, bot_token=bot_token)
        return

    if data.startswith("stk_pack_add_"):
        stk_id = data.replace("stk_pack_add_", "")
        stk_data = load_sticker_data()
        stk_entry = next((s for s in stk_data.get("stickers", []) if s["id"] == stk_id), None)
        
        png_bytes = TEMP_STICKER_STORAGE.get(stk_id)
        if not png_bytes and stk_entry and os.path.exists(stk_entry.get("local_path", "")):
            with open(stk_entry["local_path"], "rb") as f:
                png_bytes = f.read()

        if not png_bytes:
            send_message_fn(chat_id, "⚠️ Stiker fayli topilmadi. Qaytadan stiker yarating.", get_sticker_main_menu_keyboard())
            return

        send_message_fn(chat_id, "⏳ Telegram stiker to‘plamiga qo‘shilmoqda...")
        ok, pack_url, err = api_add_sticker_to_pack(
            user_id=chat_id,
            png_or_webp_bytes=png_bytes,
            emoji="✨",
            bot_token=bot_token,
            bot_username=bot_username
        )

        if ok:
            text = (
                "🎉 <b>Stiker to‘plamingizga muvaffaqiyatli qo‘shildi!</b>\n\n"
                f"🔗 <b>Sizning to‘plamingiz havolasi:</b>\n<code>{pack_url}</code>\n\n"
                "Havolani bosib, stikerlaringizni Telegram klaviaturangizga qo‘shib oling!"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "🔗 To‘plamni ochish (Add Stickers)", "url": pack_url}],
                    [{"text": "➕ Yana stiker qo‘shish", "callback_data": "stk_create_static"}],
                    [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
                ]
            }
            send_message_fn(chat_id, text, kb, parse_mode="HTML")
        else:
            text = (
                f"ℹ️ <b>To‘plam holati:</b>\n\n"
                f"Telegram javobi: <code>{err}</code>\n\n"
                "💡 <i>Eslatma: Stikeringiz botda va chatda tayyor saqlanib qoldi. Uni do‘stlaringizga yuborishingiz yoki ovoz biriktirishingiz mumkin!</i>"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "🎙️ Ovoz biriktirish", "callback_data": f"stk_attach_voice_{stk_id}"}],
                    [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
                ]
            }
            send_message_fn(chat_id, text, kb, parse_mode="HTML")
        return

    if data.startswith("stk_attach_voice_"):
        stk_id = data.replace("stk_attach_voice_", "")
        stk_data = load_sticker_data()
        stk_entry = next((s for s in stk_data.get("stickers", []) if s["id"] == stk_id), None)
        
        file_id = stk_entry["file_id"] if stk_entry else stk_id
        pending_actions[chat_id] = {
            "type": "stk_awaiting_voice",
            "stk_id": stk_id,
            "stk_file_id": file_id
        }
        kb = {"inline_keyboard": [[{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]]}
        send_message_fn(
            chat_id,
            "🎙️ <b>Ovozli xabar yozing:</b>\n\n"
            "Endi ushbu stiker uchun ovozli xabar (Voice note) yuboring.\n"
            "<i>(Telegram mikrofoni tugmasini bosib gapiring yoki audio fayl jo‘nating)</i>",
            kb,
            parse_mode="HTML"
        )
        return

    if data.startswith("stk_make_gif_"):
        stk_id = data.replace("stk_make_gif_", "")
        stk_data = load_sticker_data()
        stk_entry = next((s for s in stk_data.get("stickers", []) if s["id"] == stk_id), None)
        if stk_entry and os.path.exists(stk_entry.get("local_path", "")):
            with open(stk_entry["local_path"], "rb") as f:
                TEMP_STICKER_STORAGE[stk_id] = f.read()
            send_message_fn(chat_id, "🎞️ <b>GIF animatsiya turini tanlang:</b>", get_gif_style_keyboard(stk_id), parse_mode="HTML")
        else:
            send_message_fn(chat_id, "⚠️ Rasm topilmadi. Qaytadan rasm yuboring.", get_sticker_main_menu_keyboard())
        return

    if data == "stk_help":
        help_text = (
            "📖 <b>Stiker Ustaxonasi Qo‘llanmasi</b>\n\n"
            "1️⃣ <b>Statik stikerlar:</b>\n"
            "O‘z rasmingizni yuborasiz -> Bot uni oq hoshiyali dumaloq yoki to‘liq formatdagi 512x512 stikerga aylantirib beradi.\n\n"
            "2️⃣ <b>GIF stikerlar:</b>\n"
            "Rasmingizga pulsatsiya, silkinish yoki aylanish effekti berilib, Telegramda aylanib turuvchi GIF stiker yasaladi.\n\n"
            "3️⃣ <b>Ovozli stikerlar (Sound Stickers):</b>\n"
            "Stiker yaratgach, unga o‘z ovozingizni (Voice) qo‘shasiz. Keyinchalik birgina tugma bilan stiker va uning ovozi do‘stlaringizga birgalikda yuboriladi!\n\n"
            "4️⃣ <b>Shaxsiy Sticker Pack:</b>\n"
            "Stikerni to‘plamga qo‘shganingizda, Telegramda shaxsiy to‘plam havolasi hosil bo‘ladi (masalan <code>t.me/addstickers/...</code>). Uni xohlagan odam Telegramiga o‘rnatib oladi!"
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]]}
        send_message_fn(chat_id, help_text, kb, parse_mode="HTML")
        return

    if data == "stk_cancel":
        if chat_id in pending_actions:
            del pending_actions[chat_id]
        send_message_fn(chat_id, "Bekor qilindi.", get_sticker_main_menu_keyboard())
        return
