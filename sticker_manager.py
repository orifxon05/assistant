import os
import io
import json
import time
import requests
import cv2
import numpy as np
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
            "sound_stickers": [],
            "selected_emojis": {}
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
            data = json.load(f)
            if "selected_emojis" not in data:
                data["selected_emojis"] = {}
            return data
    except Exception:
        return {
            "pack_name": "",
            "pack_title": "Orifxon Stikerlari",
            "pack_url": "",
            "stickers": [],
            "sound_stickers": [],
            "selected_emojis": {}
        }

def save_sticker_data(data):
    if not os.path.exists(STICKERS_DIR):
        os.makedirs(STICKERS_DIR, exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[STICKER DATA SAVE ERROR]: {e}")

def get_temp_photo_path(chat_id):
    ensure_sticker_dirs()
    return os.path.join(STICKERS_DIR, f"temp_{chat_id}.png")

def get_current_sticker_path(chat_id):
    ensure_sticker_dirs()
    return os.path.join(STICKERS_DIR, f"current_{chat_id}.png")

# ─────────────────────────────────────────────────────────────
# 1. TASVIRNI TAHRIRLASH VA STIKERGA AYLANTIRISH
# ─────────────────────────────────────────────────────────────

def add_white_contour_to_cutout(cutout_rgba, contour_width=12):
    """
    Shaffof ob'yekt atrofida Telegram stikerlari kabi chiroyli oq kontur hosil qiladi.
    """
    max_size = 512 - (contour_width * 2 + 10)
    cutout_rgba.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    cw, ch = cutout_rgba.size

    alpha = cutout_rgba.split()[-1]
    # Kontur uchun alpha maskani kengaytirish
    dilated_mask = alpha.filter(ImageFilter.MaxFilter(contour_width * 2 + 1))

    # Oq kontur qatlami
    white_fill = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
    contour_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    contour_layer.paste(white_fill, (0, 0), dilated_mask)

    # Kontur ustiga asl ob'yektni tushirish
    stk = Image.alpha_composite(contour_layer, cutout_rgba)

    # 512x512 kvadrat kanvasga markazlashtirib joylash
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.paste(stk, ((512 - cw) // 2, (512 - ch) // 2))

    return canvas

def make_auto_cutout_with_contour(img_bytes, contour_width=12):
    """
    Rasmdan ob'yektni avtomatik qirqib oladi (fondan ajratadi) va
    oq kontur (sticker outline) qo'shib 512x512 stiker yasaydi.
    """
    img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    cv_img = np.array(img_pil)
    h, w = cv_img.shape[:2]

    # GrabCut yordamida markaziy ob'yektni ajratish
    margin_x = max(8, int(w * 0.05))
    margin_y = max(8, int(h * 0.05))
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

    mask = np.zeros((h, w), np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(cv_img, mask, rect, bgdModel, fgdModel, 3, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype("uint8")
        mask_pil = Image.fromarray(mask2).filter(ImageFilter.GaussianBlur(1))
    except Exception as e:
        print("[GRABCUT FALLBACK]:", e)
        mask_pil = Image.new("L", (w, h), 255)

    cutout = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cutout.paste(img_pil.convert("RGBA"), (0, 0), mask_pil)

    canvas = add_white_contour_to_cutout(cutout, contour_width=contour_width)

    webp_io = io.BytesIO()
    canvas.save(webp_io, format="WEBP", quality=95)
    png_io = io.BytesIO()
    canvas.save(png_io, format="PNG")
    return webp_io.getvalue(), png_io.getvalue()

def convert_to_sticker(image_bytes, style="cutout"):
    """
    style:
      - 'cutout': Obyektni qirqib olish + Oq stiker konturi (Telegram uslubi).
      - 'circle': Dumaloq qirqilgan, oq hoshiyali avatar stiker.
      - 'standard': Asl nisbatni saqlagan holda toza stiker.
      - 'rounded': Yumaloq burchakli stiker.
    """
    if style == "cutout":
        return make_auto_cutout_with_contour(image_bytes, contour_width=12)

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    size = 512

    if style == "circle":
        min_side = min(img.width, img.height)
        left = (img.width - min_side) // 2
        top = (img.height - min_side) // 2
        cropped = img.crop((left, top, left + min_side, top + min_side))

        inner_size = 470
        cropped = cropped.resize((inner_size, inner_size), Image.Resampling.LANCZOS)

        mask = Image.new("L", (inner_size, inner_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, inner_size, inner_size), fill=255)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(canvas)
        # Oq stiker hoshiyasi
        cdraw.ellipse((6, 6, size - 6, size - 6), fill=(255, 255, 255, 255))
        cdraw.ellipse((8, 8, size - 8, size - 8), outline=(220, 220, 220, 255), width=2)

        offset = ((size - inner_size) // 2, (size - inner_size) // 2)
        canvas.paste(cropped, offset, mask)
        final_img = canvas

    elif style == "rounded":
        img.thumbnail((470, 470), Image.Resampling.LANCZOS)
        w, h = img.size
        radius = 32

        mask = Image.new("L", (w, h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)

        bw, bh = w + 20, h + 20
        bcanvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(bcanvas)
        bdraw.rounded_rectangle((0, 0, bw, bh), radius=radius + 6, fill=(255, 255, 255, 255))
        bcanvas.paste(img, (10, 10), mask)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(bcanvas, ((size - bw) // 2, ((size - bh) // 2)))
        final_img = canvas

    else:
        # Standard fit
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(img, ((size - img.width) // 2, ((size - img.height) // 2)))
        final_img = canvas

    webp_io = io.BytesIO()
    final_img.save(webp_io, format="WEBP", quality=95)
    png_io = io.BytesIO()
    final_img.save(png_io, format="PNG")
    return webp_io.getvalue(), png_io.getvalue()

def convert_to_gif(image_bytes, anim_type="pulse"):
    """
    Oddiy rasmdan animatsion GIF stiker yasaydi.
    """
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    size = 512
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
# 2. TELEGRAM BOT API
# ─────────────────────────────────────────────────────────────

def api_send_sticker(chat_id, sticker_input, reply_markup=None, bot_token=None):
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

def get_or_create_pack_name(user_id, bot_username=None):
    clean_bot = (bot_username or "Orifxon_assistantbot").replace("@", "")
    data = load_sticker_data()
    if data.get("pack_name"):
        return data["pack_name"]
    name = f"u{user_id}_stickers_by_{clean_bot}"
    data["pack_name"] = name
    data["pack_url"] = f"https://t.me/addstickers/{name}"
    save_sticker_data(data)
    return name

def api_add_sticker_to_pack(user_id, png_or_webp_bytes, emoji="✨", bot_token=None, bot_username="Orifxon_assistantbot"):
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    pack_name = get_or_create_pack_name(user_id, bot_username)
    data = load_sticker_data()
    pack_title = data.get("pack_title", "Orifxon Stikerlari")

    check_url = f"https://api.telegram.org/bot{token}/getStickerSet"
    pack_exists = False
    try:
        chk_r = requests.get(check_url, params={"name": pack_name}, timeout=15).json()
        if chk_r.get("ok"):
            pack_exists = True
    except Exception:
        pass

    if not pack_exists:
        url = f"https://api.telegram.org/bot{token}/createNewStickerSet"
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
        url = f"https://api.telegram.org/bot{token}/addStickerToSet"
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
# 3. OVOZLI STIKERLAR (SOUND STICKERS)
# ─────────────────────────────────────────────────────────────

def save_sound_sticker_pair(sticker_file_id, voice_file_id, title="Ovozli stiker", emoji="🎙️", duration=0):
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
    data = load_sticker_data()
    pair = next((s for s in data["sound_stickers"] if s["id"] == pair_id), None)
    if not pair:
        return False, "Ovozli stiker topilmadi."

    ok_stk, _, _ = api_send_sticker(chat_id, pair["sticker_file_id"], bot_token=bot_token)
    caption = f"{pair['emoji']} <b>{pair['title']}</b>"
    ok_vce, _, _ = api_send_voice(chat_id, pair["voice_file_id"], caption=caption, bot_token=bot_token)
    return (ok_stk or ok_vce), None

# ─────────────────────────────────────────────────────────────
# 4. KLAVIATURALAR (UI KEYBOARDS)
# ─────────────────────────────────────────────────────────────

AVAILABLE_EMOJIS = ["🎩", "❤️", "👍", "👎", "🔥", "🥰", "👏", "😂"]

def get_sticker_main_menu_keyboard():
    data = load_sticker_data()
    stk_count = len(data.get("stickers", []))
    snd_count = len(data.get("sound_stickers", []))

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

def get_sticker_style_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✨ Obyektni qirqish + Kontur (Telegram stili)", "callback_data": "stk_apply_cutout"}],
            [{"text": "⚪ Dumaloq stiker (Oq hoshiyali)", "callback_data": "stk_apply_circle"}],
            [{"text": "📐 Asl ko‘rinish (To‘liq rasm)", "callback_data": "stk_apply_standard"}],
            [{"text": "🔲 Yumaloq burchakli", "callback_data": "stk_apply_rounded"}],
            [{"text": "🎞️ GIF stiker qilish", "callback_data": "stk_apply_gif_pulse"}],
            [{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]
        ]
    }

def get_gif_style_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "💓 Pulsatsiya (Kattalashib-kichrayish)", "callback_data": "stk_gif_pulse"}],
            [{"text": "⚡ Silkinish (Wiggle / Kulgili)", "callback_data": "stk_gif_shake"}],
            [{"text": "🔄 Aylanish (360° Spin)", "callback_data": "stk_gif_spin"}],
            [{"text": "❤️ Yurak urishi (Heartbeat)", "callback_data": "stk_gif_heart"}],
            [{"text": "❌ Bekor qilish", "callback_data": "stk_cancel"}]
        ]
    }

def get_emoji_selector_keyboard(chat_id):
    """
    Foydalanuvchining 3-rasmidagidek:
    Stikeringizga mos keladigan emojilarni tanlang:
    🎩 ❤️ 👍 👎 🔥 🥰 👏 😂
    [➕ Stikerlar to'plamiga qo'shish]
    """
    data = load_sticker_data()
    selected = data.get("selected_emojis", {}).get(str(chat_id), "✨")

    emoji_row = []
    for em in AVAILABLE_EMOJIS:
        label = f"✅{em}" if em == selected else em
        emoji_row.append({"text": label, "callback_data": f"stk_pick_emoji_{em}"})

    # 4 ta dan 2 qatorga bo'lish
    r1 = emoji_row[:4]
    r2 = emoji_row[4:]

    return {
        "inline_keyboard": [
            r1,
            r2,
            [{"text": f"➕ Stikerlar to‘plamiga qo‘shish ({selected})", "callback_data": "stk_do_add_to_pack"}],
            [
                {"text": "🎙️ Ovoz biriktirish", "callback_data": "stk_attach_voice"},
                {"text": "🎞️ GIF qilish", "callback_data": "stk_make_gif"}
            ],
            [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
        ]
    }

def get_sound_stickers_keyboard():
    data = load_sticker_data()
    sound_list = data.get("sound_stickers", [])
    buttons = []

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
# 5. ASOSIY MENYU VA CALLBACK HANDLERLAR
# ─────────────────────────────────────────────────────────────

def send_sticker_main_menu(chat_id, send_message_fn):
    data = load_sticker_data()
    stk_count = len(data.get("stickers", []))
    snd_count = len(data.get("sound_stickers", []))
    pack_title = data.get("pack_title", "Orifxon Stikerlari")
    pack_url = data.get("pack_url")

    pack_info = f"<a href='{pack_url}'>{pack_title}</a>" if pack_url else f"<b>{pack_title}</b> (Hali yaratilmagan)"

    text = (
        "🎨 <b>Stiker Ustaxonasi (Sticker Studio)</b>\n\n"
        "Rasmlaringizdan professional Telegram stikerlari, fonni qirqib olish va oq kontur berish, "
        "animatsion GIF stikerlar va ovozli xabarlar (Sound stickers) yarating!\n\n"
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
            "Menga stiker qilmoqchi bo‘lgan rasmingizni yuboring.\n"
            "Bot ob'yektni qirqib olish (fonni tozalash), oq kontur qo‘shish yoki dumaloq stiker qilish imkoniyatini taqdim etadi.",
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
                "Hali to‘plamga stiker qo‘shilmagan.\n"
                "Birinchi rasmingizni stiker qilib, <b>➕ Stikerlar to‘plamiga qo‘shish</b> tugmasini bossangiz, "
                "Telegramda shaxsiy to‘plam havolasi hosil bo‘ladi!"
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
                "1. Rasmdan stiker yarating.\n"
                "2. <b>🎙️ Ovoz biriktirish</b> tugmasini bosib, ovozli xabar (Voice) jo‘nating.\n"
                "3. Bot stiker va ovozni juftlik qilib saqlaydi va bir bosishda ikkalasini birga jo‘natadi!"
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

    # ─────────────────────────────────────────────────────────
    # STIKER YASASH AMALLARI (Cutout, Circle, Standard, Rounded)
    # ─────────────────────────────────────────────────────────
    if data.startswith("stk_apply_"):
        style = data.replace("stk_apply_", "")
        temp_path = get_temp_photo_path(chat_id)

        if not os.path.exists(temp_path):
            send_message_fn(chat_id, "⚠️ Rasm topilmadi. Iltimos, rasmni qaytadan yuboring.", get_sticker_main_menu_keyboard())
            return

        with open(temp_path, "rb") as f:
            photo_bytes = f.read()

        send_message_fn(chat_id, "⏳ <b>Stiker tahrirlanmoqda...</b>\n<i>(Obyekt ajratilmoqda va kontur qo‘shilmoqda)</i>", parse_mode="HTML")

        try:
            webp_bytes, png_bytes = convert_to_sticker(photo_bytes, style=style)
        except Exception as e:
            send_message_fn(chat_id, f"❌ Stiker yasashda xatolik yuz berdi: {e}")
            return

        # Natijani diskda joriy stiker sifatida saqlash
        current_path = get_current_sticker_path(chat_id)
        with open(current_path, "wb") as f:
            f.write(png_bytes)

        # Telegramga stiker sifatida yuborish
        ok, file_id, _ = api_send_sticker(chat_id, webp_bytes, bot_token=bot_token)

        stk_data = load_sticker_data()
        stk_id = f"stk_{int(time.time())}"
        stk_entry = {
            "id": stk_id,
            "file_id": file_id or "",
            "local_path": current_path,
            "format": "static",
            "style": style,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        stk_data["stickers"].append(stk_entry)
        save_sticker_data(stk_data)

        # Emojilar va to'plamga qo'shish menyusini ko'rsatish
        caption_text = (
            "✅ <b>Stikeringiz tayyor!</b>\n\n"
            "Stikeringizga mos keladigan emojini tanlang va <b>➕ Stikerlar to‘plamiga qo‘shish</b> tugmasini bosing:"
        )
        send_message_fn(chat_id, caption_text, get_emoji_selector_keyboard(chat_id), parse_mode="HTML")
        return

    # EMOJI TANLASH
    if data.startswith("stk_pick_emoji_"):
        emoji = data.replace("stk_pick_emoji_", "")
        stk_data = load_sticker_data()
        stk_data["selected_emojis"][str(chat_id)] = emoji
        save_sticker_data(stk_data)
        send_message_fn(chat_id, f"Emoji tanlandi: {emoji}", get_emoji_selector_keyboard(chat_id))
        return

    # TO'PLAMGA QO'SHISH
    if data == "stk_do_add_to_pack":
        current_path = get_current_sticker_path(chat_id)
        if not os.path.exists(current_path):
            send_message_fn(chat_id, "⚠️ Avval rasm yuborib stiker yasang.", get_sticker_main_menu_keyboard())
            return

        with open(current_path, "rb") as f:
            png_bytes = f.read()

        stk_data = load_sticker_data()
        selected_emoji = stk_data.get("selected_emojis", {}).get(str(chat_id), "✨")

        send_message_fn(chat_id, "⏳ <b>Telegram stiker to‘plamiga qo‘shilmoqda...</b>", parse_mode="HTML")
        ok, pack_url, err = api_add_sticker_to_pack(
            user_id=chat_id,
            png_or_webp_bytes=png_bytes,
            emoji=selected_emoji,
            bot_token=bot_token,
            bot_username=bot_username
        )

        if ok:
            text = (
                f"🎉 <b>Stiker {selected_emoji} to‘plamingizga muvaffaqiyatli qo‘shildi!</b>\n\n"
                f"🔗 <b>To‘plam havolasi:</b>\n<code>{pack_url}</code>\n\n"
                "Ushbu havolani bosib, stikerlaringizni to‘g‘ridan-to‘g‘ri Telegram klaviaturangizga qo‘shib oling!"
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
                "💡 <i>Eslatma: Stikeringiz botda tayyor saqlanib qoldi. Uni do‘stlaringizga yuborishingiz yoki ovoz biriktirishingiz mumkin!</i>"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "🎙️ Ovoz biriktirish", "callback_data": "stk_attach_voice"}],
                    [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
                ]
            }
            send_message_fn(chat_id, text, kb, parse_mode="HTML")
        return

    # GIF STIKER
    if data.startswith("stk_gif_"):
        anim_type = data.replace("stk_gif_", "")
        temp_path = get_temp_photo_path(chat_id)

        if not os.path.exists(temp_path):
            send_message_fn(chat_id, "⚠️ Rasm topilmadi. Qaytadan rasm yuboring.", get_sticker_main_menu_keyboard())
            return

        with open(temp_path, "rb") as f:
            photo_bytes = f.read()

        send_message_fn(chat_id, "⏳ <b>Animatsion GIF stiker tayyorlanmoqda...</b>", parse_mode="HTML")
        try:
            gif_bytes = convert_to_gif(photo_bytes, anim_type=anim_type)
        except Exception as e:
            send_message_fn(chat_id, f"❌ GIF yasashda xatolik: {e}")
            return

        caption = "🎞️ <b>Animatsion GIF stiker tayyor!</b>\n\nUshbu GIF Telegramda avtomatik o‘ynaydi va aylanadi."
        kb = {
            "inline_keyboard": [
                [{"text": "➕ Yana stiker yaratish", "callback_data": "stk_create_static"}],
                [{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]
            ]
        }
        api_send_animation(chat_id, gif_bytes, caption=caption, reply_markup=kb, bot_token=bot_token)
        return

    if data == "stk_make_gif":
        send_message_fn(chat_id, "🎞️ <b>GIF animatsiya turini tanlang:</b>", get_gif_style_keyboard(), parse_mode="HTML")
        return

    if data == "stk_attach_voice":
        stk_data = load_sticker_data()
        stickers = stk_data.get("stickers", [])
        last_stk = stickers[-1] if stickers else {}
        file_id = last_stk.get("file_id", "")

        pending_actions[chat_id] = {
            "type": "stk_awaiting_voice",
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

    if data == "stk_help":
        help_text = (
            "📖 <b>Stiker Ustaxonasi Qo‘llanmasi</b>\n\n"
            "1️⃣ <b>Obyektni qirqish va oq kontur (Telegram stili):</b>\n"
            "Rasm yuborasiz -> <b>✨ Obyektni qirqish + Kontur</b> tugmasini bosasiz. Bot rasm orqa fonini olib tashlab, shaxsiy stiker konturini chizib beradi!\n\n"
            "2️⃣ <b>Emoji tanlash va To‘plamga qo‘shish:</b>\n"
            "Stikeringizga mos keladigan emojini tanlaysiz (masalan 🔥, 😎, 👍) va <b>➕ Stikerlar to‘plamiga qo‘shish</b> tugmasini bosasiz. Telegramda shaxsiy to‘plamingizga qo‘shiladi.\n\n"
            "3️⃣ <b>Ovozli stikerlar (Sound Stickers):</b>\n"
            "Stikerga <b>🎙️ Ovoz biriktirish</b> orqali ovozli xabar qo‘shasiz. Keyin bir bosishda ham stiker, ham ovoz birga jo‘natiladi!\n\n"
            "4️⃣ <b>GIF stikerlar:</b>\n"
            "Rasmingizga pulsatsiya yoki aylanish harakati qo‘shiladi."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Stiker menyusi", "callback_data": "stk_menu"}]]}
        send_message_fn(chat_id, help_text, kb, parse_mode="HTML")
        return

    if data == "stk_cancel":
        if chat_id in pending_actions:
            del pending_actions[chat_id]
        send_message_fn(chat_id, "Bekor qilindi.", get_sticker_main_menu_keyboard())
        return
