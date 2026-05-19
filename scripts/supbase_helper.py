from supabase import Client, ClientOptions, create_client


class SupabaseHelper:
    def __init__(
        self,
        *,
        supabase_url: str,
        supabase_key: str,
    ):
        self.client = create_client(
            supabase_url,
            supabase_key,
            options=ClientOptions(postgrest_client_timeout=120),
        )

    def get_supabase_client(self) -> Client:
        """
        Возвращает Supabase client.
        """
        return self.client

    def check_connection(self) -> bool:
        """
        Проверяет соединение с Supabase.
        """
        try:
            self.get_supabase_client().table("documents").select("*").execute()
            return True
        except Exception as e:
            print(f"Ошибка при проверке соединения с Supabase: {e}")
            return False
