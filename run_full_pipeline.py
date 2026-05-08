import os
import importlib
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from scripts.qdrant_helper import QdrantHelper
from scripts.supbase_helper import SupabaseHelper


# Скрипты, которые запускаются через ООП или импортом
SPDocumentChunker = importlib.import_module("scripts.04_chunking").SPDocumentChunker
Embedder = importlib.import_module("scripts.05_embedding").Embedder
SupabaseChunksUpserter = importlib.import_module("scripts.06_upsert_chunks_supb").SupabaseChunksUpserter
QdrantInsertor = importlib.import_module("scripts.07_insert_to_qdrant").QdrantInsertor

# Скрипты, которые запускаются в своем main()
pdf_to_markdown_path_02 = "scripts/01_pdf_to_markdown.py"
clean_markdown_path_03 = "scripts/02_clean_markdown.py"
supabase_writer_path_10 = "scripts/03_supabase_writer.py"

# Функция, которая вставляет векторы в Qdrant из скрипта 07_insert_to_qdrant.py
embed_vector_rows_to_qdrant_points = importlib.import_module("scripts.07_insert_to_qdrant").embed_vector_rows_to_qdrant_points


PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# Переменные из .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY_LONG")

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Коллекция в Qdrant
QDRANT_COLLECTION_NAME = "sp_chunks"


def main():
    print("-" * 100)
    print("Работает скрипт 01_pdf_to_markdown.py")
    subprocess.run([sys.executable, pdf_to_markdown_path_02], check=True)

    print("-" * 100)
    print("Работает скрипт 02_clean_markdown.py")
    subprocess.run([sys.executable, clean_markdown_path_03], check=True)
    print("-" * 100)

    print("-" * 100)
    print("Работает скрипт 03_supabase_writer.py")
    subprocess.run([sys.executable, supabase_writer_path_10], check=True)
    print("-" * 100)

    # Перед чанкованием нужно получить все файлы СП из папки output/cleaned/
    sp_files = list(Path("output/cleaned").glob("СП*.md"))
    # Путь к папке json
    _json = PROJECT_ROOT / "output" / "json"

    # Если файлы не найдены, то выводим ошибку и выходим из скрипта
    if not sp_files:
        print("Файлы СП не найдены в папке output/cleaned/")
        return

    # ------------------------------------------------------------
    # Подключаемся к Supabase и Qdrant и проверяем соединение
    # ------------------------------------------------------------
    supabase_helper = SupabaseHelper(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
    if not supabase_helper.check_connection():
        print("Не удалось подключиться к Supabase")
        return
    supabase_client = supabase_helper.get_supabase_client()

    qdrant_helper = QdrantHelper(qdrant_host=QDRANT_HOST, qdrant_port=QDRANT_PORT, qdrant_api_key=QDRANT_API_KEY)
    if not qdrant_helper.check_connection():
        print("Не удалось подключиться к Qdrant")
        return
    qdrant_client = qdrant_helper.get_qdrant_client()

    # ------------------------------------------------------------
    # Создаем коллекцию в Qdrant, если она не существует
    # ------------------------------------------------------------
    print("-" * 100)
    print(f"Проверяем коллекцию {QDRANT_COLLECTION_NAME}")
    if not qdrant_helper.check_collection(collection_name=QDRANT_COLLECTION_NAME):
        qdrant_helper.create_collection(collection_name=QDRANT_COLLECTION_NAME)
        print(f"Коллекция {QDRANT_COLLECTION_NAME} создана")
    else:
        print(f"Коллекция {QDRANT_COLLECTION_NAME} уже существует")
    print("-" * 100)

    # ------------------------------------------------------------

    # ------------------------------------------------------------
    # Создаем экземпляры всех классов, которые нужны для чанкования
    # ------------------------------------------------------------
    embedder = Embedder()
    chunker = SPDocumentChunker(embedder=embedder)
    chunks_upsert = SupabaseChunksUpserter(supabase_client=supabase_client)
    qdrant_insertor = QdrantInsertor(qdrant_client=qdrant_client)

    # ------------------------------------------------------------
    # Запускаем чанкование для всех файлов СП
    # ------------------------------------------------------------
    print("Запустили чанкование для всех файлов СП")
    print("-" * 100)

    # Цикл по всем файлам СП
    for sp_file in sp_files:
        # Чтобы не класть скрипт из-за одного файла добавил try. Для MVP, думаю, достаточно.
        try:
            print("-" * 100)
            print(f"Обработка файла: {sp_file}")
            path_md = sp_file
            path_json = _json / sp_file.with_suffix(".json").name
            text = path_md.read_text(encoding="utf-8")

            if not text:
                print(f"Файл {sp_file} пустой")
                continue

            if not path_json.exists():
                print(f"Файл {path_json} не найден")
                continue


            chunks = chunker.add_metadata(
                blocks=chunker.split_plain_sp_into_blocks(text),
                json_path=path_json
            )

            if not chunks:
                print(f"Внимание!!!! Не найдено чанков для файла {sp_file}")
                continue

            # Вставляем чанки в Supabase
            sub_rows = chunks_upsert.insert_chunks(chunks=chunks)
            print(f"Вставлено чанков в Supabase: {len(sub_rows)}")

            # Подготовка точек для Qdrant
            print(f"Подготавливаем чанки для Qdrant: {len(sub_rows)}")
            qdrant_points = embed_vector_rows_to_qdrant_points(embedder, sub_rows)
            print(f"Готово чанков для Qdrant: {len(qdrant_points)}")

            # Вставляем точки в Qdrant
            qdrant_insertor.insert_chunks(chunks=qdrant_points, collection_name=QDRANT_COLLECTION_NAME)
            print("-" * 100)

        except Exception as e:
            print(f"Ошибка при обработке файла {sp_file}: {e}")
            continue


if __name__ == "__main__":
    main()
