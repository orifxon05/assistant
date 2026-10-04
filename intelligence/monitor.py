import asyncio
import time
from datetime import datetime
from .sources import get_intelligence_folder_peers, ensure_intelligence_folder
from .state import get_channel_last_id, update_channel_state, is_message_seen, mark_message_seen
from .preferences import load_preferences, get_check_interval, is_intelligence_enabled
from .analyzer import analyze_post_with_ai
from .formatter import format_intelligence_message
from .digest import record_daily_item, get_today_digest

LAST_DIGEST_DATE = None

async def run_intelligence_check(telethon_client, send_bot_message_func=None, admin_id=None, dry_run=False):
    """
    Barcha '📂 Intelligence' papkasidagi kanallarni bir martalik to'liq tekshirish va tahlil qilish.
    """
    peers, folder_title = await get_intelligence_folder_peers(telethon_client)
    if not peers:
        print("[MONITOR] '📂 Intelligence' papkasida hali hech qanday kanal topilmadi.")
        return 0, []

    prefs = load_preferences()
    sources_prefs = prefs.get("sources", {})
    processed_count = 0
    relevant_found = []

    print(f"[MONITOR] '{folder_title}' papkasida {len(peers)} ta kanal/guruh tekshirilmoqda...")

    for entity in peers:
        try:
            uname = getattr(entity, 'username', None)
            ident = f"@{uname}" if uname else str(entity.id)
            title = getattr(entity, 'title', None) or getattr(entity, 'first_name', ident)

            # Check if muted in user preferences
            src_pref = sources_prefs.get(ident.lower(), {})
            if src_pref.get("muted", False):
                continue

            last_id = get_channel_last_id(entity.id)
            messages_to_process = []

            # If it's the very first time checking this channel, only look at the last 3 messages
            limit = 15 if last_id > 0 else 3

            async for msg in telethon_client.iter_messages(entity, limit=limit, min_id=last_id):
                if msg.text and len(msg.text.strip()) > 30:
                    messages_to_process.append(msg)

            if not messages_to_process:
                continue

            # Process oldest to newest
            messages_to_process.reverse()

            for msg in messages_to_process:
                # Update channel state progressively
                update_channel_state(entity.id, msg.id, title)

                # Deduplication check
                if is_message_seen(msg.text, msg.id, entity.id):
                    continue

                mark_message_seen(msg.text, msg.id, entity.id)
                processed_count += 1

                # Analyze via Groq AI
                channel_intent = src_pref.get("intent", "all")
                analysis = analyze_post_with_ai(msg.text, channel_title=title, channel_intent=channel_intent)
                await asyncio.sleep(5)

                score = analysis.get("relevance_score", 0)
                level = analysis.get("level", "IGNORE")

                # Post link
                post_link = ""
                if uname:
                    post_link = f"https://t.me/{uname}/{msg.id}"

                if score >= 60:
                    record_daily_item(
                        title=analysis.get("title", "Imkoniyat"),
                        company=analysis.get("company", ""),
                        link=post_link,
                        category=",".join(analysis.get("categories", [])),
                        score=score,
                        level=level
                    )

                # Send only 🔥 and 🟢 (score >= 80)
                if score >= 80:
                    relevant_found.append((title, analysis))
                    msg_text, keyboard = format_intelligence_message(analysis, source_title=title, post_link=post_link)

                    if dry_run or not send_bot_message_func or not admin_id:
                        print(f"\n[DRY RUN TOPILDI: {score} BALL] -> {title}:\n{msg_text}\n")
                    else:
                        try:
                            send_bot_message_func(admin_id, msg_text, keyboard, parse_mode="HTML")
                            await asyncio.sleep(2)  # Delay between notifications
                        except Exception as e:
                            print(f"[MONITOR] Telegramga xabar yuborishda xatolik: {e}")

        except Exception as e:
            print(f"[MONITOR] Kanalni tekshirishda xatolik ({getattr(entity, 'id', 'peer')}): {e}")

    return processed_count, relevant_found

async def intelligence_monitor_loop(telethon_client, send_bot_message_func, admin_id):
    """
    Fondagi uzluksiz monitoring sikli (har 30 daqiqada uyg'onadi).
    """
    global LAST_DIGEST_DATE
    print("[INTELLIGENCE] Fon monitoringi ishga tushdi.")

    # 1. Ensure folder exists
    try:
        await ensure_intelligence_folder(telethon_client)
    except Exception as e:
        print("[MONITOR] Folder tekshirishda xatolik:", e)

    # Initial short delay on bot boot
    await asyncio.sleep(15)

    while True:
        try:
            if is_intelligence_enabled():
                prefs = load_preferences()
                dry_run = prefs.get("dry_run", False)
                count, found = await run_intelligence_check(
                    telethon_client,
                    send_bot_message_func=send_bot_message_func,
                    admin_id=admin_id,
                    dry_run=dry_run
                )
                if count > 0:
                    print(f"[INTELLIGENCE] {count} ta post tahlil qilindi, {len(found)} ta mos keluvchi topildi.")

                # Check daily digest (e.g. at 21:00)
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                digest_enabled = prefs.get("daily_digest_enabled", True)
                digest_target_hour = int(prefs.get("daily_digest_time", "21:00").split(":")[0])

                if digest_enabled and now.hour == digest_target_hour and LAST_DIGEST_DATE != today_str:
                    LAST_DIGEST_DATE = today_str
                    digest_text = get_today_digest()
                    if send_bot_message_func and admin_id:
                        try:
                            send_bot_message_func(admin_id, digest_text, parse_mode="HTML")
                        except Exception as e:
                            print("[MONITOR] Kunlik xulosa yuborishda xatolik:", e)

            # Sleep for configured interval
            interval_mins = get_check_interval()
            await asyncio.sleep(interval_mins * 60)

        except asyncio.CancelledError:
            print("[INTELLIGENCE] Monitoring to'xtatildi.")
            break
        except Exception as e:
            print("[INTELLIGENCE XATOLIK]:", e)
            await asyncio.sleep(60)
