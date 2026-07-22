from supabase import create_client

from app.config import settings

_supabase = None


def get_supabase():
    global _supabase
    if _supabase is None and settings.SUPABASE_URL and settings.SUPABASE_KEY:
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase
