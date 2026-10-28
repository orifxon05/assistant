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


DEFAULT_VERCEL_WEBAPP_URL = "https://assistant-nu-nine.vercel.app"

def get_toyona_webapp_url():
    global active_tunnel_url
    custom_url = os.getenv("TOYONA_WEBAPP_URL", "").strip() or DEFAULT_VERCEL_WEBAPP_URL
    return custom_url or active_tunnel_url

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
    custom_url = os.getenv("TOYONA_WEBAPP_URL", "").strip() or DEFAULT_VERCEL_WEBAPP_URL
    if custom_url:
        print(f"[TOYONA] Doimiy Vercel havolasi aniqlandi: {custom_url}. Cloudflare tunnel kerak emas.")
        active_tunnel_url = custom_url
        notify_admin_tunnel(custom_url)
        return

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

            cur.execute("SELECT current_price FROM settings LIMIT 1")
            s_row = cur.fetchone()
            current_price = float(s_row[0]) if (s_row and s_row[0]) else 150000.0

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
                "settings": {"current_price": current_price},
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
            curr_price = 150000.0
            if isinstance(payload.get("settings"), dict):
                curr_price = float(payload.get("settings", {}).get("current_price", 150000))
            data = {
                "backup_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "database_provider": "Neon PostgreSQL (via API)",
                "settings": {"current_price": curr_price},
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

    friends_map = {f["id"]: f.get("name", "Noma'lum") for f in data.get("friends", [])}
    weddings_map = {w["id"]: w for w in data.get("weddings", [])}
    gifts = data.get("gifts", [])

    current_price = float(data.get("settings", {}).get("current_price", 150000.0))

    def money_fmt(n):
        return f"{int(round(float(n or 0))):,}".replace(",", " ") + " so‘m"

    def kg_fmt(n):
        return f"{float(n or 0):.1f} kg"

    total_sum = 0
    total_kg = 0.0
    total_today_val = 0

    rows_data = []
    for idx, g in enumerate(gifts):
        w = weddings_map.get(g.get("wedding_id"), {})
        w_name = (w.get("name") + " to‘yi") if w.get("name") else "-"
        w_date = (w.get("wedding_date") or "")[:10]
        f_name = friends_map.get(g.get("friend_id"), "Noma'lum oshna")

        amount = int(g.get("amount") or 0)
        gift_price = float(g.get("meat_price") or w.get("meat_price") or current_price)
        kg = (amount / gift_price) if gift_price > 0 else 0.0
        today_val = int(round(kg * current_price))

        total_sum += amount
        total_kg += kg
        total_today_val += today_val

        rows_data.append({
            "num": idx + 1,
            "friend": f_name,
            "wedding": w_name,
            "date": w_date or "-",
            "amount_fmt": money_fmt(amount),
            "kg_fmt": kg_fmt(kg),
            "today_val_fmt": money_fmt(today_val),
            "note": g.get("note") or "-"
        })

    # Summary by weddings
    wedding_stats = {}
    for wid, w in weddings_map.items():
        wedding_stats[wid] = {
            "name": (w.get("name") + " to‘yi") if w.get("name") else "-",
            "date": (w.get("wedding_date") or "")[:10] or "-",
            "count": 0,
            "sum": 0,
            "kg": 0.0
        }
    for g in gifts:
        wid = g.get("wedding_id")
        if wid in wedding_stats:
            amt = int(g.get("amount") or 0)
            gp = float(g.get("meat_price") or weddings_map.get(wid, {}).get("meat_price") or current_price)
            k = (amt / gp) if gp > 0 else 0.0
            wedding_stats[wid]["count"] += 1
            wedding_stats[wid]["sum"] += amt
            wedding_stats[wid]["kg"] += k

    wedding_list = sorted(wedding_stats.values(), key=lambda x: x["sum"], reverse=True)

    today_str = datetime.now().strftime("%d.%m.%Y")
    gift_rows_html = "".join([
        f"""<tr>
          <td style="text-align:center;">{r['num']}</td>
          <td><b>{r['friend']}</b></td>
          <td>{r['wedding']}</td>
          <td style="text-align:center;">{r['date']}</td>
          <td style="text-align:right;">{r['amount_fmt']}</td>
          <td style="text-align:right;">{r['kg_fmt']}</td>
          <td style="text-align:right;">{r['today_val_fmt']}</td>
          <td>{r['note']}</td>
        </tr>""" for r in rows_data
    ]) if rows_data else '<tr><td colspan="8" style="text-align:center;color:#888;padding:15px;">To‘yona yozuvlari kiritilmagan</td></tr>'

    wedding_rows_html = "".join([
        f"""<tr>
          <td style="text-align:center;">{idx + 1}</td>
          <td><b>{w['name']}</b></td>
          <td style="text-align:center;">{w['date']}</td>
          <td style="text-align:center;">{w['count']} kishi</td>
          <td style="text-align:right;">{money_fmt(w['sum'])}</td>
          <td style="text-align:right;">{kg_fmt(w['kg'])}</td>
        </tr>""" for idx, w in enumerate(wedding_list)
    ]) if wedding_list else '<tr><td colspan="6" style="text-align:center;color:#888;padding:15px;">To‘ylar mavjud emas</td></tr>'

    excel_html = f"""\ufeff<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<!--[if gte mso 9]>
<xml>
 <x:ExcelWorkbook>
  <x:ExcelWorksheets>
   <x:ExcelWorksheet>
    <x:Name>Toyona hisoboti</x:Name>
    <x:WorksheetOptions>
     <x:DisplayGridlines/>
    </x:WorksheetOptions>
   </x:ExcelWorksheet>
  </x:ExcelWorksheets>
 </x:ExcelWorkbook>
</xml>
<![endif]-->
<style>
  body {{ font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e2924; }}
  table {{ border-collapse: collapse; margin-bottom: 22px; width: 100%; }}
  th {{ background-color: #0d785b; color: #ffffff; font-weight: bold; border: 1px solid #084c39; padding: 8px 10px; font-size: 11pt; }}
  td {{ border: 1px solid #d3ded8; padding: 7px 10px; font-size: 10.5pt; }}
  .head-sec {{ background-color: #164e3f; color: #ffffff; font-size: 12pt; font-weight: bold; padding: 7px 10px; }}
  .total-row {{ background-color: #e5f4ed; font-weight: bold; color: #084c39; }}
  .summary-lbl {{ background-color: #f6faf8; font-weight: 600; width: 280px; }}
  .summary-val {{ font-weight: bold; color: #0d785b; }}
</style>
</head>
<body>
  <h2 style="color:#0d785b;margin:0 0 4px;font-size:16pt;">💒 TO‘YONA HISOBOTI</h2>
  <p style="margin:0 0 16px;color:#556;font-size:10pt;">Tayyorlangan sana: <b>{today_str}</b> | Bugungi 1 kg go‘sht narxi: <b>{money_fmt(current_price)}</b></p>

  <table>
    <tr><th colspan="2" class="head-sec">📊 1. UMUMIY KO‘RSATKICHLAR</th></tr>
    <tr><td class="summary-lbl">Jami yig‘ilgan to‘yona summasi:</td><td class="summary-val">{money_fmt(total_sum)}</td></tr>
    <tr><td class="summary-lbl">Jami go‘sht ekvivalenti:</td><td class="summary-val">{kg_fmt(total_kg)}</td></tr>
    <tr><td class="summary-lbl">Bugungi narxdagi umumiy qiymati:</td><td class="summary-val">{money_fmt(total_today_val)}</td></tr>
    <tr><td class="summary-lbl">Jami to‘ylar soni:</td><td>{len(weddings_map)} ta</td></tr>
    <tr><td class="summary-lbl">Jami oshnalar soni:</td><td>{len(friends_map)} ta</td></tr>
    <tr><td class="summary-lbl">Kiritilgan to‘yona yozuvlari:</td><td>{len(gifts)} ta</td></tr>
  </table>

  <table>
    <tr><th colspan="8" class="head-sec">📋 2. BARCHA TO‘YONALARNING BATAFSIL RO‘YXATI</th></tr>
    <tr>
      <th style="width:45px;text-align:center;">№</th>
      <th style="text-align:left;">Oshna (Do‘st ismi)</th>
      <th style="text-align:left;">Qaysi to‘y</th>
      <th style="text-align:center;">To‘y sanasi</th>
      <th style="text-align:right;">Berilgan to‘yona</th>
      <th style="text-align:right;">Go‘sht miqdori</th>
      <th style="text-align:right;">Bugungi qiymati</th>
      <th style="text-align:left;">Izoh</th>
    </tr>
    {giftRowsHtml}
    <tr class="total-row">
      <td colspan="4" style="text-align:right;">JAMI:</td>
      <td style="text-align:right;">{money_fmt(total_sum)}</td>
      <td style="text-align:right;">{kg_fmt(total_kg)}</td>
      <td style="text-align:right;">{money_fmt(total_today_val)}</td>
      <td></td>
    </tr>
  </table>

  <table>
    <tr><th colspan="6" class="head-sec">🎉 3. TO‘YLAR BO‘YICHA JAMLANMA</th></tr>
    <tr>
      <th style="width:45px;text-align:center;">№</th>
      <th style="text-align:left;">To‘y nomi</th>
      <th style="text-align:center;">Sanasi</th>
      <th style="text-align:center;">To‘yona berganlar</th>
      <th style="text-align:right;">Jami summa</th>
      <th style="text-align:right;">Jami go‘sht ekv.</th>
    </tr>
    {weddingRowsHtml}
  </table>
</body>
</html>"""

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    xls_file = f"toyona_hisoboti_{ts}.xls"

    with open(xls_file, "w", encoding="utf-8") as f:
        f.write(excel_html)

    caption = (
        "📊 <b>To‘yona Hisoboti (Excel)</b>\n\n"
        f"💰 <b>Jami to‘yona:</b> {money_fmt(total_sum)}\n"
        f"🥩 <b>Go‘sht ekvivalenti:</b> {kg_fmt(total_kg)}\n"
        f"💵 <b>Bugungi qiymati:</b> {money_fmt(total_today_val)}\n"
        f"🎉 <b>To‘ylar:</b> {len(weddings_map)} ta | 👥 <b>Oshnalar:</b> {len(friends_map)} ta\n"
        f"📝 <b>Kiritilgan yozuvlar:</b> {len(gifts)} ta\n"
        f"🍖 <b>Bugungi 1 kg narxi:</b> {money_fmt(current_price)}\n\n"
        "📁 <i>Quyidagi Excel faylini ochsangiz, barcha to‘yona va oshnalar toza, tushunarli jadvalda ko‘rinadi!</i>"
    )

    ok = send_file_to_telegram(chat_id, xls_file, caption=caption)
    try:
        if os.path.exists(xls_file):
            os.remove(xls_file)
    except Exception:
        pass

    return ok, None

