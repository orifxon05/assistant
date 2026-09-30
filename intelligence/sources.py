from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import DialogFilter, TextWithEntities
from .config import DEFAULT_FOLDER_NAMES
from .preferences import load_preferences, update_source_preference

async def find_intelligence_folder(telethon_client):
    """
    Telegramdagi '📂 Intelligence' yoki '📂 Addek' nomli chat papkasini qidiradi.
    Topilsa DialogFilter obyektini qaytaradi.
    """
    try:
        res = await telethon_client(GetDialogFiltersRequest())
        filters = getattr(res, 'filters', res)
        for f in filters:
            if isinstance(f, DialogFilter):
                t = getattr(f, 'title', '')
                title_str = t.text if hasattr(t, 'text') else str(t)
                for candidate in DEFAULT_FOLDER_NAMES:
                    if candidate.lower() in title_str.lower():
                        return f, title_str
        return None, None
    except Exception as e:
        print("[SOURCES] Papkani qidirishda xatolik:", e)
        return None, None

async def ensure_intelligence_folder(telethon_client, folder_name="Intelligence"):
    """
    Agar papka mavjud bo'lmasa, uni avtomatik yaratadi.
    Telegram folder title limiti max 12 ta belgi bo'lishi shart!
    """
    folder, title = await find_intelligence_folder(telethon_client)
    if folder:
        return folder, title

    try:
        res = await telethon_client(GetDialogFiltersRequest())
        filters = getattr(res, 'filters', res)
        existing_ids = [getattr(f, 'id', 0) for f in filters if hasattr(f, 'id')]
        new_id = (max(existing_ids) + 1) if existing_ids else 2
        if new_id < 2:
            new_id = 2

        clean_name = folder_name.replace("📂", "").strip()[:12]
        if not clean_name:
            clean_name = "Intelligence"

        title_obj = TextWithEntities(text=clean_name, entities=[])
        me = await telethon_client.get_input_entity("me")
        new_filter = DialogFilter(
            id=new_id,
            title=title_obj,
            pinned_peers=[],
            include_peers=[me],
            exclude_peers=[],
            emoticon="📂"
        )
        await telethon_client(UpdateDialogFilterRequest(id=new_id, filter=new_filter))
        print(f"[SOURCES] Yangi '{clean_name}' papkasi yaratildi (ID: {new_id}).")
        return new_filter, clean_name
    except Exception as e:
        print("[SOURCES] Papka yaratishda xatolik:", e)
        return None, None

async def get_intelligence_folder_peers(telethon_client):
    """
    Papkadagi barcha chat/kanal entity'larini ro'yxat sifatida qaytaradi.
    """
    folder, title = await find_intelligence_folder(telethon_client)
    if not folder:
        return [], None

    peers = []
    include_peers = getattr(folder, 'include_peers', [])
    for input_peer in include_peers:
        try:
            entity = await telethon_client.get_entity(input_peer)
            peers.append(entity)
        except Exception as e:
            print(f"[SOURCES] Peer entity olishda xatolik ({input_peer}):", e)
    return peers, title

async def analyze_new_source_channel(telethon_client, entity):
    """
    Yangi qo'shilgan kanalning oxirgi 8 ta postini o'rganib, uning qisqa mavzusini aniqlaydi.
    """
    title = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Kanal')
    uname = getattr(entity, 'username', None)
    identifier = f"@{uname}" if uname else str(entity.id)

    texts = []
    try:
        async for msg in telethon_client.iter_messages(entity, limit=8):
            if msg.text:
                texts.append(msg.text[:100])
    except Exception as e:
        print(f"[SOURCES] Yangi kanal xabarlarini o'qishda xatolik ({identifier}):", e)

    sample_content = " | ".join(texts)
    return {
        "title": title,
        "identifier": identifier,
        "sample": sample_content[:300]
    }
