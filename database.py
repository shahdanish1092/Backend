import os
from dotenv import load_dotenv

load_dotenv()

_supabase = None

def get_supabase():
    """Return a Supabase client. Import is deferred so tests don't fail when package isn't installed."""
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    return _supabase

def get_db_connection():
    """Return a psycopg2 connection. Import is deferred to avoid import-time failures."""
    import psycopg2
    return psycopg2.connect(os.getenv("DATABASE_URL"))
