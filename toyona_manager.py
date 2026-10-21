import os
import sys
import json
import asyncio
import subprocess
import requests
from datetime import datetime

TOYONA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toyona")
toyona_process = None
cloudflared_process = None
active_tunnel_url = ""

DEFAULT_NEON_DB_URL = "postgresql://neondb_owner:npg_RNsvIktC3pF2@ep-curly-math-b5sqz5zy-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"

def get_toyona_db_url():
    raw = os.getenv("TOYONA_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_NEON_DB_URL
    if "channel_binding=" in raw:
        raw = raw.replace("channel_binding=require&", "").replace("&channel_binding=require", "").replace("?channel_binding=require", "")
    return raw.strip()


def get_toyona_webapp_url():
    global active_tunnel_url
    return active_tunnel_url or os.getenv("TOYONA_WEBAPP_URL", "").strip()

def is_node_available():
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

def is_cloudflared_available():
    try:
        res = subprocess.run(["cloudflared", "-v"], capture_output=True, text=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

def notify_admin_tunnel(url):
    admin_id = os.getenv("ADMIN_ID")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not admin_id or not bot_token:
        return
    direct_url = f"{url}?key=orifxon"
    text = (
        "💒 <b>To‘yona Mini App muvaffaqiyatli ishga tushdi!</b>\n\n"
        f"📱 <b>Telegram Mini App:</b> pastdagi tugmani bosing\n"
        f"🌐 <b>Har qanday telefon/brauzer uchun to‘g‘ridan-to‘g‘ri havola:</b>\n"
        f"<code>{direct_url}</code>\n\n"
        "<i>(Ushbu havolani istalgan telefonda Chrome yoki Safari orqali ochishingiz mumkin, Telegram shart emas!)</i>"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "🚀 Mini App’ni ochish (Telegramda)", "web_app": {"url": url}}],
            [{"text": "🌐 Brauzerda ochish (Har qanday telefon)", "url": direct_url}],
            [{"text": "📊 Hisobotni yuklab olish (CSV/Excel)", "callback_data": "toyona_get_report"}]
        ]
    }
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": admin_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": kb
            },
            timeout=10
        )
    except Exception as e:
        print(f"[TOYONA NOTIFY ERROR]: {e}")

    try:
        # Telegram pastki chap burchagidagi Menyu tugmasini ham yangilab qo'yish
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": "💒 To‘yona",
                    "web_app": {"url": url}
                }
            },
            timeout=10
        )
    except Exception:
        pass


async def start_cloudflared_tunnel(port):
    global cloudflared_process, active_tunnel_url
    if not is_cloudflared_available():
        print("[TOYONA] cloudflared o'rnatilmagan. Mini App faqat lokal tarmoqda ishlaydi.")
        return

    cmd = ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"]
    print(f"[TOYONA TUNNEL] Cloudflare tunnel ishga tushirilmoqda...")
    try:
        cloudflared_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def monitor_stream(stream):
            global active_tunnel_url
            import re
            pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode('utf-8', errors='ignore')
                m = pattern.search(line_str)
                if m:
                    url = m.group(0)
                    if url != active_tunnel_url:
                        active_tunnel_url = url
                        print(f"\n[TOYONA TUNNEL] 🎉 Mini App havolasi tayyor: {active_tunnel_url}\n")
                        notify_admin_tunnel(active_tunnel_url)

        asyncio.create_task(monitor_stream(cloudflared_process.stderr))
        asyncio.create_task(monitor_stream(cloudflared_process.stdout))
    except Exception as e:
        print(f"[TOYONA TUNNEL XATOLIK]: {e}")

is_server_running = True

async def run_node_supervisor(env, port):
    global toyona_process, is_server_running
    server_js = os.path.join(TOYONA_DIR, "server.js")
    while is_server_running:
        try:
            print(f"[TOYONA] Node.js server ishga tushirilmoqda (port {port})...")
            toyona_process = await asyncio.create_subprocess_exec(
                "node", server_js,
                cwd=TOYONA_DIR,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            print(f"[TOYONA] Node.js server ishga tushdi (PID: {toyona_process.pid})")

            async def monitor_node_output(stream, is_err=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    txt = line.decode('utf-8', errors='ignore').rstrip()
                    if txt:
                        prefix = "[TOYONA ERR]" if is_err else "[TOYONA]"
                        print(f"{prefix} {txt}")

            asyncio.create_task(monitor_node_output(toyona_process.stdout, False))
            asyncio.create_task(monitor_node_output(toyona_process.stderr, True))

            await toyona_process.wait()
            if not is_server_running:
                break
            print(f"[TOYONA] Node server to'xtadi. 2 soniyada qayta ishga tushirilmoqda...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[TOYONA SUPERVISOR XATO]: {e}")
            await asyncio.sleep(3)

async def start_toyona_server():
    global is_server_running
    server_js = os.path.join(TOYONA_DIR, "server.js")
    if not os.path.exists(server_js):
        return

    if not is_node_available():
        print("[TOYONA] Node.js topilmadi. Termuxda 'pkg install nodejs-lts' o'rnating.")
        return

    try:
        # Check node_modules
        node_modules = os.path.join(TOYONA_DIR, "node_modules")
        if not os.path.exists(node_modules):
            print("[TOYONA] 'node_modules' topilmadi. Kutubxonalar o'rnatilmoqda (npm install)...")
            npm_proc = await asyncio.create_subprocess_exec("npm", "install", "--omit=dev", cwd=TOYONA_DIR)
            await npm_proc.wait()
            print("[TOYONA] Kutubxonalar muvaffaqiyatli o'rnatildi.")

        env = os.environ.copy()
        env["TOYONA_DATABASE_URL"] = get_toyona_db_url()
        env["TELEGRAM_BOT_TOKEN"] = os.getenv("TELEGRAM_BOT_TOKEN", "")

        port = os.getenv("TOYONA_PORT", "3000")
        env["TOYONA_PORT"] = port
        is_server_running = True
        print(f"[TOYONA] Baza sozlandi: {env['TOYONA_DATABASE_URL'][:30]}...")

        asyncio.create_task(run_node_supervisor(env, port))
        asyncio.create_task(start_cloudflared_tunnel(port))

    except Exception as e:
        print(f"[TOYONA XATOLIK]: Serverni yoqishda xatolik: {e}")

async def stop_toyona_server():
    global toyona_process, cloudflared_process, is_server_running
    is_server_running = False
    if cloudflared_process:
        try:
            cloudflared_process.terminate()
            await cloudflared_process.wait()
            print("[TOYONA] Cloudflared tunnel to'xtatildi.")
        except Exception:
            pass
    if toyona_process:
        try:
            toyona_process.terminate()
            await toyona_process.wait()
            print("[TOYONA] Node.js server to'xtatildi.")
        except Exception:
            pass



def export_toyona_data():
    conn_str = get_toyona_db_url()
    
    # 1. Try psycopg2 direct connection
    if conn_str:
        try:
            import psycopg2
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor()

            cur.execute("SELECT * FROM friends ORDER BY name")
            friends = []
            for r in cur.fetchall():
                friends.append({"id": str(r[0]), "telegram_id": r[1], "name": r[2], "created_at": str(r[3])})

            cur.execute("SELECT * FROM weddings ORDER BY wedding_date DESC NULLS LAST")
            weddings = []
            for r in cur.fetchall():
                weddings.append({
                    "id": str(r[0]), "telegram_id": r[1], "friend_id": str(r[2]) if r[2] else None,
                    "name": r[3], "wedding_date": str(r[4]) if r[4] else None,
                    "meat_price": float(r[5]), "min_kg": float(r[6]),
                    "note": r[7] or "", "archived": r[8]
                })

            cur.execute("SELECT * FROM gifts")
            gifts = []
            for r in cur.fetchall():
                gifts.append({
                    "id": str(r[0]), "telegram_id": r[1], "wedding_id": str(r[2]),
                    "friend_id": str(r[3]), "amount": int(r[4]), "meat_price": float(r[5]),
                    "note": r[6] or ""
                })

            conn.close()

            data = {
                "backup_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "database_provider": "Neon PostgreSQL",
                "stats": {
                    "total_friends": len(friends),
                    "total_weddings": len(weddings),
                    "total_gifts": len(gifts)
                },
                "friends": friends,
                "weddings": weddings,
                "gifts": gifts
            }
            return data, None
        except ImportError:
            pass
        except Exception as e:
            print(f"[TOYONA PSYCOPG2 BACKUP ERROR]: {e}")

    # 2. Fallback to local server endpoint
    port = os.getenv("TOYONA_PORT", "3000")
    admin_id = os.getenv("ADMIN_ID", "123456789")
    try:
        res = requests.get(
            f"http://127.0.0.1:{port}/api/backup",
            headers={"DEV-AUTH": "true", "DEV-TELEGRAM-ID": admin_id},
            timeout=8
        )
        if res.ok:
            payload = res.json()
            data = {
                "backup_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "database_provider": "Neon PostgreSQL (via API)",
                "stats": {
                    "total_friends": len(payload.get("friends", [])),
                    "total_weddings": len(payload.get("weddings", [])),
                    "total_gifts": len(payload.get("gifts", []))
                },
                "friends": payload.get("friends", []),
                "weddings": payload.get("weddings", []),
                "gifts": payload.get("gifts", [])
            }
            return data, None
    except Exception as e:
        print(f"[TOYONA API BACKUP ERROR]: {e}")

    return None, "Baza ma'lumotlarini yuklab bo'lmadi. TOYONA_DATABASE_URL to'g'riligini tekshiring."

def send_file_to_telegram(chat_id, file_path, caption="", bot_token=None):
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, files=files, data=data, timeout=30)
            return res.ok
    except Exception as e:
        print(f"[TOYONA SEND FILE ERROR]: {e}")
        return False


def generate_and_send_toyona_report(chat_id):
    data, err = export_toyona_data()
    if err or not data:
        return False, err or "Ma'lumot topilmadi"

    friends_map = {f["id"]: f["name"] for f in data.get("friends", [])}
    weddings_map = {w["id"]: w for w in data.get("weddings", [])}
    gifts = data.get("gifts", [])

    total_amount = sum(g.get("amount", 0) for g in gifts)
    total_kg = sum(g.get("amount", 0) / (g.get("meat_price", 0) or 150000) for g in gifts)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"toyona_hisoboti_{ts}.csv"

    def escape_csv(val):
        s = str(val if val is not None else "")
        return '"' + s.replace('"', '""') + '"'

    rows = [
        ["To‘y", "Sana", "To‘y paytidagi kg narxi (so‘m)", "Oshna", "Summa (so‘m)", "Yozuvdagi kg narxi (so‘m)", "Izoh"]
    ]

    for g in gifts:
        w = weddings_map.get(g.get("wedding_id"), {})
        w_name = w.get("name", "Noma'lum to'y")
        w_date = (w.get("wedding_date") or "")[:10]
        w_price = w.get("meat_price", "")
        f_name = friends_map.get(g.get("friend_id"), "Noma'lum oshna")
        rows.append([w_name, w_date, w_price, f_name, g.get("amount", 0), g.get("meat_price", ""), g.get("note", "")])

    with open(csv_file, "w", encoding="utf-8-sig") as f:
        for r in rows:
            f.write(";".join(escape_csv(x) for x in r) + "\n")

    money_fmt = f"{int(total_amount):,}".replace(",", " ") + " so‘m"
    kg_fmt = f"{total_kg:.1f} kg"

    caption = (
        "📊 <b>To‘yona Hisoboti (Excel / CSV)</b>\n\n"
        f"💰 <b>Jami yig‘ilgan to‘yona:</b> {money_fmt}\n"
        f"🥩 <b>Jami go‘sht ekvivalenti:</b> {kg_fmt}\n"
        f"🎉 <b>To‘ylar soni:</b> {len(weddings_map)} ta | 👥 <b>Oshnalar:</b> {len(friends_map)} ta\n"
        f"📝 <b>Yozuvlar:</b> {len(gifts)} ta\n\n"
        "📁 <i>To‘liq jadval fayli ilova qilindi. Excel yoki telefon brauzerida ochishingiz mumkin.</i>"
    )

    ok = send_file_to_telegram(chat_id, csv_file, caption=caption)
    try:
        if os.path.exists(csv_file):
            os.remove(csv_file)
    except Exception:
        pass

    return ok, None

