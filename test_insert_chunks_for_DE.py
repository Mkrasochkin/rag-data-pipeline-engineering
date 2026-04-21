import importlib
import json
import os
import pathlib

from dotenv import load_dotenv
from scripts import qdrant_helper
from scripts.supbase_helper import SupabaseHelper
from scripts.qdrant_helper import QdrantHelper
from supabase import Client

SupabaseChunksUpserter = importlib.import_module("scripts.09_upsert_chunks_supb").SupabaseChunksUpserter
SPDocumentChunker = importlib.import_module("scripts.07_chunking").SPDocumentChunker
Embedder = importlib.import_module("scripts.08_embedding").Embedder

QdrantInsertor = importlib.import_module("scripts.11_insert_to_qdrant").QdrantInsertor
embed_vector_rows_to_qdrant_points = importlib.import_module("scripts.11_insert_to_qdrant").embed_vector_rows_to_qdrant_points

PROJECT_ROOT = pathlib.Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPBASE_PUBLIC_KEY_LONG = os.getenv("SUPABASE_PUBLIC_KEY_LONG")

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")




def main() -> None:
    try:
        embedder = Embedder()
        # Читаем чанки из Supabase
        supabase_helper = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPBASE_PUBLIC_KEY_LONG)
        if not supabase_helper.check_connection():
            print("Не удалось подключиться к Supabase")
            return
        supabase_client = supabase_helper.get_supabase_client()
        chunks_upsert = SupabaseChunksUpserter(supabase_client=supabase_client)

        # Тестовая привязка к документу
        chunks = chunks_upsert.read_chunks(doc_id="33cafd34-aaf2-42ce-b14c-3c497bb32efb")
        print(f"Чанки прочитаны из Supabase: {len(chunks)}")

        qdrant_points = embed_vector_rows_to_qdrant_points(embedder, chunks)
        print(f"Чанки векторизованы: {len(qdrant_points)}")

        # Подключаемся к Qdrant
        qdrant_helper = QdrantHelper(qdrant_host=QDRANT_HOST, qdrant_port=QDRANT_PORT, qdrant_api_key=QDRANT_API_KEY)
        if not qdrant_helper.check_connection():
            print("Не удалось подключиться к Qdrant")
            return

        qdrant_client = qdrant_helper.get_qdrant_client()

        # Вставляем чанки в Qdrant
        qdrant_insertor = QdrantInsertor(qdrant_client=qdrant_client)
        qdrant_insertor.create_collection(
            collection_name="test_chunks",
            vector_size=embedder.get_embedding_dimension(),
        )
        qdrant_insertor.insert_chunks(chunks=qdrant_points, collection_name="test_chunks")
        print("Чанки вставлены в Qdrant")


    except Exception as error:
        print("Ошибка во время подготовки/вставки чанков:", error)


if __name__ == "__main__":
    main()
