import os

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv(override=True)


class SupabaseHelper:
    def __init__(
        self,
        *,
        supabase_url: str = os.getenv("SUPABASE_URL"),
        supabase_key: str = os.getenv("SUPABASE_PUBLIC_KEY_LONG")
    ):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

    def get_supabase_client(self) -> Client:
        return create_client(self.supabase_url, self.supabase_key)