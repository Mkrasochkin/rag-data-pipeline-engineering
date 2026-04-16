import os
import pathlib

from dotenv import load_dotenv
from supabase import Client, create_client
from scripts.supbase_helper import SupabaseHelper
import importlib

SupabaseChunksUpserter = importlib.import_module("scripts.09_upsert_chunks_supb").SupabaseChunksUpserter
SPDocumentChunker = importlib.import_module("scripts.07_chunking").SPDocumentChunker
Embedder = importlib.import_module("scripts.08_embedding").Embedder

PROJECT_ROOT = pathlib.Path(__file__).parent

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLIC_KEY_LONG")



def main() -> None:
    load_dotenv(override=True)
    print("Проверка подключения к Supabase через client API")

    try:
        # Получаем чанки из чистого файла
        chunker = SPDocumentChunker(embedder=Embedder())
        _md = PROJECT_ROOT / "output" / "cleaned"
        path = _md / "СП_48_13330_2019.md"
        raw = path.read_text(encoding="utf-8")
        with_meta = chunker.add_metadata(
            blocks=chunker.split_plain_sp_into_blocks(raw),
            document_text=raw,
        )

        print(len(with_meta))
        # Подключаемся к Supabase и заливаем чанки в таблицу chunks
        # supabase: Client = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY).get_supabase_client()
        # chunks_upsert = SupabaseChunksUpserter(supabase_client=supabase)
        # chunks_upsert.insert_chunks(chunks=with_meta)

    except Exception as error:
        print("Ошибка подключения через Supabase client:", error)


if __name__ == "__main__":
    main()
