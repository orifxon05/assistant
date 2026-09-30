"""
Jarvis Intelligence Module
~~~~~~~~~~~~~~~~~~~~~~~~~~
Telegram jildlarini ("📂 Intelligence" / "📂 Addek") avtomatik kuzatuvchi,
postlarni AI tahlil qiluvchi va foydalanuvchi profiliga moslarini
filtrlash va yuborish tizimi.
"""

from .config import load_user_profile, save_user_profile
from .state import load_intelligence_state, save_intelligence_state, is_message_seen, mark_message_seen
from .preferences import load_preferences, save_preferences, update_source_preference
from .analyzer import analyze_post_with_ai
from .formatter import format_intelligence_message, format_digest_message
from .sources import get_intelligence_folder_peers, analyze_new_source_channel
from .monitor import intelligence_monitor_loop, run_intelligence_check
from .onboarding import handle_onboarding_callback, start_onboarding_quiz

__all__ = [
    "load_user_profile",
    "save_user_profile",
    "load_intelligence_state",
    "save_intelligence_state",
    "is_message_seen",
    "mark_message_seen",
    "load_preferences",
    "save_preferences",
    "update_source_preference",
    "analyze_post_with_ai",
    "format_intelligence_message",
    "format_digest_message",
    "get_intelligence_folder_peers",
    "analyze_new_source_channel",
    "intelligence_monitor_loop",
    "run_intelligence_check",
    "handle_onboarding_callback",
    "start_onboarding_quiz",
]
