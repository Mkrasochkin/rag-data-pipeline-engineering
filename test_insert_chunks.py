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
SUPABASE_KEY = os.getenv("SUPABASE_PUBLIC_KEY_LONG")

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def write_chunks_preview(
    *,
    chunks: list[dict],
    output_path: pathlib.Path,
    limit: int = 1000,
) -> None:
    """
    Сохраняет превью первых N чанков в формате BLOCK + текст,
    а также печатает metadata без текстовых полей.
    """
    selected_chunks = chunks[:limit]
    with output_path.open("w", encoding="utf-8") as f:
        for i, chunk in enumerate(selected_chunks):
            metadata = dict(chunk.get("metadata", {}))
            text = metadata.get("text_content", "") or ""
            metadata.pop("text", None)
            metadata.pop("text_content", None)

            f.write("=" * 80 + "\n")
            f.write(f"BLOCK {i}  ({len(text)} символов)\n")
            f.write("=" * 80 + "\n")
            f.write(f"{text}\n\n")
            f.write("METADATA\n")
            f.write("-" * 80 + "\n")
            f.write(f"{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n")

    print(f"Превью чанков сохранено: {output_path}")


def main() -> None:
    try:
        embedder = Embedder()
        # Получаем чанки из чистого файла
        chunker = SPDocumentChunker(embedder=embedder)
        _md = PROJECT_ROOT / "output" / "cleaned"
        # path = _md / "СП_48_13330_2019.md"
        path = _md / "СП_16_13330_2017.md"
        raw = path.read_text(encoding="utf-8")
        with_meta = chunker.add_metadata(
            blocks=chunker.split_plain_sp_into_blocks(raw),
            document_text=raw,
        )


        preview_path = PROJECT_ROOT / "chunks_preview_1000.txt"
        write_chunks_preview(chunks=with_meta, output_path=preview_path)

        # # Подключаемся к Supabase и заливаем чанки в таблицу chunks
        # supabase_helper = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
        # # Проверяем соединение с Supabase
        # if not supabase_helper.check_connection():
        #     print("Не удалось подключиться к Supabase")
        #     return
        # supabase_client = supabase_helper.get_supabase_client()

        # # Вставляем чанки в таблицу chunks
        # chunks_upsert = SupabaseChunksUpserter(supabase_client=supabase_client)
        # sub_rows = chunks_upsert.insert_chunks(chunks=with_meta)
        # qdrant_points = embed_vector_rows_to_qdrant_points(embedder, sub_rows)
        # print(f"Готово точек для Qdrant: {len(qdrant_points)}")

        # # Подключаемся к Qdrant
        # qdrant_helper = QdrantHelper(qdrant_host=QDRANT_HOST, qdrant_port=QDRANT_PORT, qdrant_api_key=QDRANT_API_KEY)
        # if not qdrant_helper.check_connection():
        #     print("Не удалось подключиться к Qdrant")
        #     return

        # qdrant_client = qdrant_helper.get_qdrant_client()

        # # Вставляем чанки в Qdrant
        # qdrant_insertor = QdrantInsertor(qdrant_client=qdrant_client)
        # qdrant_insertor.create_collection(
        #     collection_name="test_chunks",
        #     vector_size=embedder.get_embedding_dimension(),
        # )
        # qdrant_insertor.insert_chunks(chunks=qdrant_points, collection_name="test_chunks")
        # print("Чанки вставлены в Qdrant")


    except Exception as error:
        print("Ошибка во время подготовки/вставки чанков:", error)


if __name__ == "__main__":
    main()
