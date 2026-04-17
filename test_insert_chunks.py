import importlib
import json
import os
import pathlib

from dotenv import load_dotenv
from scripts.supbase_helper import SupabaseHelper
from supabase import Client, create_client

SupabaseChunksUpserter = importlib.import_module("scripts.09_upsert_chunks_supb").SupabaseChunksUpserter
SPDocumentChunker = importlib.import_module("scripts.07_chunking").SPDocumentChunker
Embedder = importlib.import_module("scripts.08_embedding").Embedder

PROJECT_ROOT = pathlib.Path(__file__).parent

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLIC_KEY_LONG")


def write_chunks_preview(
    *,
    chunks: list[dict],
    output_path: pathlib.Path,
    limit: int = 100,
) -> None:
    """
    Сохраняет превью первых N чанков в формате BLOCK + текст,
    а также печатает metadata без текстовых полей.
    """
    selected_chunks = chunks[:limit]
    with output_path.open("w", encoding="utf-8") as f:
        for i, chunk in enumerate(selected_chunks):
            text = chunk.get("text", "") or ""
            metadata = dict(chunk.get("metadata", {}))
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

        preview_path = PROJECT_ROOT / "chunks_preview_100.txt"
        write_chunks_preview(chunks=with_meta, output_path=preview_path, limit=100)


        # # Теперь очистим таблицу chunks
        # supabase: Client = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY).get_supabase_client()
        # supabase.table("chunks").delete().execute()

        # # Подключаемся к Supabase и заливаем чанки в таблицу chunks
        # supabase: Client = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY).get_supabase_client()
        # chunks_upsert = SupabaseChunksUpserter(supabase_client=supabase)
        # chunks_upsert.insert_chunks(chunks=with_meta)

    except Exception as error:
        print("Ошибка во время подготовки/вставки чанков:", error)


if __name__ == "__main__":
    main()
