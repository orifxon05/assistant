import os
import sys
import json
import asyncio
import subprocess
import requests
from datetime import datetime

TOYONA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toyona")
toyona_process = None

def get_toyona_db_url():
    raw = os.getenv("TOYONA_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if "channel_binding=" in raw:
        raw = raw.replace("channel_binding=require&", "").replace("&channel_binding=require", "").replace("?channel_binding=require", "")
    return raw.strip()

def get_toyona_webapp_url():
    return os.getenv("TOYONA_WEBAPP_URL", "").strip()

def is_node_available():
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

async def start_toyona_server():
    global toyona_process
    server_js = os.path.join(TOYONA_DIR, "server.js")
    if not os.path.exists(server_js):
        return

    if not is_node_available():
        print("[TOYONA] Node.js topilmadi. Termuxda 'pkg install nodejs-lts' o'rnating.")
        return

    try:
        env = os.environ.copy()
        if not env.get("TOYONA_DATABASE_URL"):
            env["TOYONA_DATABASE_URL"] = get_toyona_db_url()
        if not env.get("TELEGRAM_BOT_TOKEN"):
            env["TELEGRAM_BOT_TOKEN"] = os.getenv("TELEGRAM_BOT_TOKEN", "")

        port = os.getenv("TOYONA_PORT", "3000")
        env["TOYONA_PORT"] = port

        print(f"[TOYONA] Server ishga tushirilmoqda (port {port})...")
        toyona_process = await asyncio.create_subprocess_exec(
            "node", server_js,
            cwd=TOYONA_DIR,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print(f"[TOYONA] Node.js server ishga tushdi (PID: {toyona_process.pid})")
    except Exception as e:
        print(f"[TOYONA XATOLIK]: Serverni yoqishda xatolik: {e}")

async def stop_toyona_server():
    global toyona_process
    if toyona_process:
        try:
            toyona_process.terminate()
            await toyona_process.wait()
            print("[TOYONA] Server to'xtatildi.")
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
