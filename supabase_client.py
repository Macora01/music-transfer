# supabase_client.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_service_client() -> Client:
    """
    Devuelve un cliente con permisos de servicio para operaciones de backend
    (usar solo en el servidor, nunca en frontend).
    """
    if not SUPABASE_SERVICE_ROLE_KEY:
        return supabase
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
