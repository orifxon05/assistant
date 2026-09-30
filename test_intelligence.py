import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
except (ValueError, TypeError):
    API_ID = 0

if API_ID > 2147483647 or API_ID <= 0:
    print(f"\n❌ XATOLIK: .env ichidagi TELEGRAM_API_ID noto'g'ri: {API_ID}")
    print("TELEGRAM_API_ID faqat https://my.telegram.org saytidan olinadigan 7-8 xonali son bo'lishi kerak!")
    sys.exit(1)

API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")
if not SESSION_NAME:
    SESSION_NAME = "orifxon_session" if os.path.exists("orifxon_session.session") else "jarvis_session"

from intelligence.config import load_user_profile
from intelligence.sources import find_intelligence_folder, ensure_intelligence_folder
from intelligence.monitor import run_intelligence_check

async def test_main():
    print("=" * 60)
    print("  JARVIS INTELLIGENCE - DRY-RUN TESTI (XAVFSIZ TEKSHIRUV)")
    print("=" * 60)

    # 1. Profile test
    prof = load_user_profile()
    print(f"\n[1] Profil tekshirildi:")
    print(f"  • Ism: {prof.get('name')}")
    print(f"  • Yo'nalish: {prof.get('primary_field')}")
    print(f"  • Maqsad: {', '.join(prof.get('goals', []))}")
    print(f"  • Joylashuv: {prof.get('primary_location')}")

    # 2. Telethon init
    print("\n[2] Telethon akkauntiga ulanish...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"  • Muvaffaqiyatli ulandi: {me.first_name} (@{me.username})")

    # 3. Folder test
    print("\n[3] '📂 Intelligence' papkasini tekshirish...")
    folder, title = await find_intelligence_folder(client)
    if not folder:
        print("  • Papka topilmadi, yangi '📂 Intelligence' papkasi ochilmoqda...")
        folder, title = await ensure_intelligence_folder(client)
    print(f"  • Papka mavjud: '{title}'")

    # 4. Dry-run pipeline
    print("\n[4] Kanallarni monitoring qilish (Dry-Run rejimida, Telegramga yuborilmaydi)...")
    count, found = await run_intelligence_check(client, send_bot_message_func=None, admin_id=None, dry_run=True)

    print("\n" + "=" * 60)
    print(f"  TEST YAKUNLANDI:")
    print(f"  • Tahlil qilingan postlar soni: {count} ta")
    print(f"  • Yuqori moslikdagi postlar soni: {len(found)} ta")
    print("=" * 60)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_main())
