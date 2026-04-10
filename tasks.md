📋 Итоговый список задач команды (RAG + Metadata Pipeline)
👩‍💻 ЗАДАЧИ ДАША (Кратко)
Валидация и финализация DDL схемы Supabase.

Написать clean_markdown.py.

Написать filename_parser.py.

Написать section_extractor.py.

Создать скрипт инициализации публичного Workspace.

Подготовить JSON-дамп для передачи САШЕ.

👩‍💻 ЗАДАЧИ ДАША (Детально)
Задача 1.0. Валидация DDL схемы и подготовка окружения
Описание: ДАША отвечает за структуру метаданных в Supabase. Проверить файл DDL.sql на соответствие задачам RAG-пайплайна. Убедиться, что все нужные расширения и индексы присутствуют.

Ожидаемый результат:

Файл schema/final_schema.sql (отредактированный при необходимости).

Чек-лист проверки:

Размерность вектора: embedding VECTOR(384) — совпадает с моделью BAAI/bge-small-en-v1.5.

Наличие таблицы workspaces.

RLS политики для публичного доступа к documents (чтение visibility='public').

Задача 1.1. Написать clean_markdown.py
Описание: Очистка MD от мусора (колонтитулы, содержание, переносы слов).

Вход: raw_md/СП 113.13330.2023_Стоянки автомобилей.md
Выход: cleaned_md/СП 113.13330.2023_Стоянки автомобилей.md

Ожидаемый результат:

python
# Файл: preprocessing/clean_markdown.py
def clean_markdown(text: str) -> str:
    # 1. Удалить всё до заголовка "1. Область применения"
    # 2. Удалить всё после "Приложение А" или "Библиография"
    # 3. Склеить слова с переносами ("рампы-\nпандусы" -> "рампы-пандусы")
    # 4. Удалить колонтитулы (повторяющиеся строки с номерами страниц)
    return cleaned_text
Скрипт должен обрабатывать папку raw_md/ → cleaned_md/.

Задача 1.2. Написать filename_parser.py
Описание: Извлечение метаданных из имени файла.

Вход: СП 113.13330.2023_Стоянки автомобилей.md
Выход: dict с полями для таблицы documents.

Ожидаемый результат:

python
# Файл: preprocessing/filename_parser.py
import re

def parse_filename(filename: str) -> dict:
    # Пример: "СП 113.13330.2023_Стоянки автомобилей.md"
    # type = "СП"
    # designation = "113.13330"
    # year = 2023
    # official_title = "Стоянки автомобилей"
    return {
        "type": "СП",
        "designation": "113.13330",
        "year": 2023,
        "official_title": "Стоянки автомобилей"
    }
Задача 1.3. Написать section_extractor.py
Описание: Разбивка MD на секции по заголовкам #, ##, ### с построением hierarchy_path.

Вход: Очищенный Markdown текст.
Выход: list[dict].

Ожидаемый результат:

python
# Файл: preprocessing/section_extractor.py
def extract_sections(md_text: str) -> list[dict]:
    return [
        {
            "section_code": "5.26",
            "section_title": "Уклоны рамп",
            "level": 3,
            "hierarchy_path": "5. Объемно-планировочные решения/5.26 Уклоны рамп",
            "content": "Максимальный уклон рампы...\n\n| Тип | Уклон |\n..." 
            # ВАЖНО: Таблицы в markdown-формате оставляем как есть для ДИМЫ!
        }
    ]
Задача 1.4. Подготовить JSON-дамп для передачи САШЕ
Описание: ДАША не лезет в Supabase. Он готовит структурированные данные и передает их САШЕ в формате JSON.

Формат передачи (строго):

json
{
    "document": {
        "filename": "СП 113.13330.2023_Стоянки автомобилей.md",
        "metadata": {
            "type": "СП",
            "designation": "113.13330",
            "year": 2023,
            "official_title": "Стоянки автомобилей"
        },
        "sections": [
            {
                "section_code": "5.26",
                "section_title": "Уклоны рамп",
                "level": 3,
                "hierarchy_path": "5. Объемно-планировочные решения/5.26 Уклоны рамп",
                "content": "..."
            }
        ]
    }
}
Ожидаемый результат: Скрипт preprocessing/run.py, который для всех MD в папке создает JSON-файлы в processed_json/. ДАША передает САШЕ папку с JSON и говорит: "Вот готовые данные, загружай".

Задача 1.5. Создание скрипта инициализации публичного Workspace
Описание: ДАША отвечает за метаданные. Публичный Workspace — часть метаданных. Нужно написать скрипт workspace_manager.py, который создает или возвращает ID публичного workspace.

Вход: Подключение к Supabase.
Выход: PUBLIC_WORKSPACE_ID (UUID), сохраненный в .env для использования САШЕЙ.

Ожидаемый результат:

python
# Файл: db/workspace_manager.py
def get_or_create_public_workspace() -> UUID:
    # 1. Проверить существование workspace с name = "Публичная база знаний"
    # 2. Если нет — создать с billing_tier = 'free'
    # 3. Вернуть UUID
    return workspace_id
🧑‍💻 ЗАДАЧИ ДИМА (Кратко)
Настроить Embedder (модель BAAI/bge-small-en-v1.5, 384 dims).

Разработать RegulationChunker (1 пункт = 1 чанк, таблицы отдельно).

Создать векторный индекс ivfflat на поле embedding.

Написать vector_uploader.py.

Провести локальный тест с ТГ-ботом.

🧑‍💻 ЗАДАЧИ ДИМА (Детально)
Задача 2.1. Настройка Embedder (BAAI/bge-small-en-v1.5)
Описание: ДИМА выбирает и настраивает модель эмбеддингов. Критично: использовать правильный префикс для запросов и нормализацию.

Вход: Тексты чанков / Поисковый запрос.
Выход: list[float] длиной 384.

Ожидаемый результат:

python
# Файл: vectorization/embedder.py
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Для чанков документов (без префикса, с нормализацией)
        return self.model.encode(texts, normalize_embeddings=True).tolist()
    
    def embed_query(self, query: str) -> list[float]:
        # Для поискового запроса (С ПРЕФИКСОМ для BGE)
        prefix = "Represent this sentence for searching relevant passages: "
        if not query.startswith(prefix):
            query = prefix + query
        return self.model.encode(query, normalize_embeddings=True).tolist()
Задача 2.2. Разработка RegulationChunker и Обработчик таблиц
Описание: Адаптировать чанкер под формат секций от ДАШИ. Строго следовать правилам из ТЗ.

Правила чанкования (из ТЗ):

1 чанк = 1 пункт документа (5.26, 5.26.1, 5.26.2).

Пункт включает весь текст до следующего пункта (не резать внутри пункта по параграфам, если нет таблицы).

Номер пункта сохраняется в метаданных (clause_number).

Таблица = отдельный чанк (если есть | --- |, выделить её в чанк с content_type = 'table', текст до и после — отдельные текстовые чанки).

Изображения и формулы — пока не обрабатываем.

Вход: section (dict от ДАШИ).
Выход: Список чанков с метаданными.

Ожидаемый результат:

python
# Файл: chunking/regulation_chunker.py
import re

def chunk_section(section: dict) -> list[dict]:
    """
    Разбивает секцию на чанки согласно правилам ТЗ.
    """
    chunks = []
    content = section["content"]
    section_code = section["section_code"]
    hierarchy_path = section["hierarchy_path"]
    
    # 1. Ищем markdown-таблицы
    table_pattern = r"(\|.*\|[\s\S]*?)(?=\n\n|\Z)"
    tables = list(re.finditer(table_pattern, content))
    
    if tables:
        last_end = 0
        for i, match in enumerate(tables):
            # Текст ДО таблицы
            text_before = content[last_end:match.start()].strip()
            if text_before:
                chunks.append(_create_chunk(text_before, "text", section_code, hierarchy_path))
            
            # Сама таблица
            table_text = match.group(0).strip()
            chunks.append(_create_chunk(table_text, "table", section_code, hierarchy_path))
            last_end = match.end()
        
        # Текст ПОСЛЕ последней таблицы
        text_after = content[last_end:].strip()
        if text_after:
            chunks.append(_create_chunk(text_after, "text", section_code, hierarchy_path))
    else:
        # Нет таблиц — весь пункт один чанк
        if content.strip():
            chunks.append(_create_chunk(content, "text", section_code, hierarchy_path))
    
    # 2. Проставляем chunk_index
    for idx, chunk in enumerate(chunks):
        chunk["chunk_index"] = idx
        chunk["start_point"] = chunk["content"][:100]
        chunk["end_point"] = chunk["content"][-100:]
    
    return chunks

def _create_chunk(content: str, c_type: str, clause: str, path: str) -> dict:
    return {
        "content": content,
        "content_type": c_type,
        "clause_number": clause,
        "section_path": path,
        "has_image": False,
        "image_url": None
    }
Задача 2.3. Создание векторного индекса в БД
Описание: ДИМА гарантирует быстрый поиск по векторам. Создает индекс ivfflat и предоставляет пример SQL-запроса для команды LLM (сами stored procedures создает команда LLM под свои нужды).

Ожидаемый результат:

sql
-- Выполнить в Supabase SQL Editor один раз
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine 
ON chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
Пример запроса для документации LLM-команды:

sql
-- Поиск похожих чанков
SELECT 
    c.id, c.content, c.clause_number, c.section_path, c.content_type,
    1 - (c.embedding <=> :query_vector) AS similarity
FROM chunks c
WHERE c.workspace_id = :workspace_id
    AND 1 - (c.embedding <=> :query_vector) > 0.5
ORDER BY c.embedding <=> :query_vector
LIMIT 5;
Задача 2.4. Написать vector_uploader.py
Описание: Вставка чанков с векторами в таблицу chunks.

Ожидаемый результат:

python
# Файл: vectorization/uploader.py
import uuid

def upload_chunks(chunks: list[dict]) -> int:
    """
    chunks: список словарей с полями:
    - doc_id, section_id, workspace_id
    - clause_number, section_path
    - content_type, content
    - embedding (list[float])
    - token_count
    """
    records = []
    for chunk in chunks:
        records.append({
            "id": str(uuid.uuid4()),
            "vector_db_id": str(uuid.uuid4()),  # или равно id
            "doc_id": chunk["doc_id"],
            "section_id": chunk["section_id"],
            "workspace_id": chunk["workspace_id"],
            "clause_number": chunk["clause_number"],
            "section_path": chunk["section_path"],
            "chunk_index": chunk["chunk_index"],
            "content_type": chunk["content_type"],
            "content": chunk["content"],
            "embedding": chunk["embedding"],
            "token_count": chunk["token_count"],
            "start_point": chunk.get("start_point"),
            "end_point": chunk.get("end_point")
        })
    
    result = supabase.table("chunks").insert(records).execute()
    return len(result.data)
Задача 2.5. Локальный тест с ботом
Описание: ДИМА проверяет качество поиска end-to-end в локальной среде (Docker Supabase + pgvector + ТГ-бот).

Сценарий тестирования:

Загрузить 2-3 документа через пайплайн (СП 113, СП 54).

Бот получает вопрос от пользователя.

Бот векторизует вопрос через embedder.embed_query().

Бот выполняет SQL-запрос (пример из 2.3).

Бот возвращает ответ с цитатой и пунктом.

Метрики для проверки:

Вопрос	Ожидаемый пункт	Ожидаемый документ
"Максимальный уклон рампы"	5.26	СП 113.13330.2023
"Ширина коридора в жилом доме"	5.3.2	СП 54.13330.2022
Цель: Добиться, чтобы правильный пункт был в топ-3 выдачи (recall@3 > 70%).

🧑‍🔧 ЗАДАЧИ САША (Кратко)
Написать SupabaseMetadataWriter.

Написать оркестратор full_pipeline.py.

Реализовать проверку на дубликаты документов.

Настроить логирование и статусы обработки.

Написать README.md.

🧑‍🔧 ЗАДАЧИ САША (Детально)
Задача 3.1. Написать SupabaseMetadataWriter
Описание: Класс для вставки в documents и document_sections.

Вход: JSON от ДАШИ.
Выход: doc_id и список section_id.

Ожидаемый результат:

python
# Файл: pipeline/supabase_writer.py
from supabase import Client
import uuid

class SupabaseMetadataWriter:
    def __init__(self, client: Client, public_workspace_id: str):
        self.client = client
        self.public_workspace_id = public_workspace_id

    def upsert_document(self, doc_meta: dict) -> uuid.UUID:
        # 1. Проверить SELECT ... WHERE designation = ... AND year = ...
        existing = self.client.table("documents")\
            .select("id")\
            .eq("designation", doc_meta["designation"])\
            .eq("year", doc_meta["year"])\
            .eq("visibility", "public")\
            .execute()
        
        if existing.data:
            return uuid.UUID(existing.data[0]["id"])
        
        # 2. Если нет — INSERT
        new_doc = self.client.table("documents").insert({
            "workspace_id": self.public_workspace_id,
            "type": doc_meta["type"],
            "designation": doc_meta["designation"],
            "year": doc_meta["year"],
            "official_title": doc_meta["official_title"],
            "visibility": "public",
            "version_status": "active",
            "processing_metadata": {"status": "pending"}
        }).execute()
        return uuid.UUID(new_doc.data[0]["id"])

    def create_sections(self, doc_id: uuid.UUID, sections: list) -> list[uuid.UUID]:
        # Вставка в document_sections
        records = []
        for sec in sections:
            records.append({
                "doc_id": str(doc_id),
                "section_code": sec["section_code"],
                "section_title": sec["section_title"],
                "hierarchy_path": sec["hierarchy_path"],
                "level": sec["level"]
            })
        result = self.client.table("document_sections").insert(records).execute()
        return [uuid.UUID(r["id"]) for r in result.data]

    def update_status(self, doc_id: uuid.UUID, status: str, error: str = None, chunks_count: int = 0):
        # Обновление processing_metadata
        metadata = {"status": status, "chunks_count": chunks_count}
        if error:
            metadata["error"] = error
        self.client.table("documents").update({"processing_metadata": metadata})\
            .eq("id", str(doc_id)).execute()
Задача 3.2. Написать оркестратор full_pipeline.py
Описание: Скрипт, который склеивает работу ДАШИ (JSON), ДИМЫ (Чанкер/Эмбеддер) и САШИ (Writer).

Алгоритм:

Читает JSON от ДАШИ.

Вызывает SupabaseMetadataWriter → получает doc_id и section_ids.

Обновляет статус документа на parsing_done.

Для каждой секции вызывает chunker.chunk_section().

Для всех чанков вызывает embedder.embed_documents().

Вызывает uploader.upload_chunks().

Обновляет статус документа на completed.

Ожидаемый результат:

python
# Файл: pipeline/full_pipeline.py
import json
import uuid
from chunking.regulation_chunker import chunk_section
from vectorization.embedder import Embedder
from vectorization.uploader import upload_chunks
from pipeline.supabase_writer import SupabaseMetadataWriter

def process_json(json_path: str, writer: SupabaseMetadataWriter, embedder: Embedder):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. Метаданные
    doc_id = writer.upsert_document(data["document"]["metadata"])
    writer.update_status(doc_id, "parsing_done")
    section_ids = writer.create_sections(doc_id, data["document"]["sections"])
    
    # 2. Чанкинг
    all_chunks = []
    for section, section_id in zip(data["document"]["sections"], section_ids):
        chunks = chunk_section(section)
        for chunk in chunks:
            chunk.update({
                "doc_id": doc_id,
                "section_id": section_id,
                "workspace_id": writer.public_workspace_id
            })
            all_chunks.append(chunk)
    
    # 3. Векторизация
    texts = [c["content"] for c in all_chunks]
    embeddings = embedder.embed_documents(texts)
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb
        chunk["token_count"] = len(chunk["content"].split())
    
    # 4. Загрузка
    uploaded_count = upload_chunks(all_chunks)
    
    # 5. Финал
    writer.update_status(doc_id, "completed", chunks_count=uploaded_count)
    print(f"✅ Документ {data['document']['metadata']['designation']} загружен. Чанков: {uploaded_count}")
Задача 3.3. Настроить логирование
Описание: Логировать каждый шаг в консоль и в documents.processing_metadata.

Структура processing_metadata:

json
{
    "status": "completed",
    "error": null,
    "chunks_count": 156,
    "sections_count": 42,
    "pipeline_version": "1.0.0",
    "started_at": "2024-01-01T00:00:00Z",
    "completed_at": "2024-01-01T00:05:00Z"
}
Задача 3.4. Написать README.md
Описание: Инструкция по запуску пайплайна для всей команды.

Содержание:

Установка: pip install -r requirements.txt.

Подготовка БД: Запустить schema/final_schema.sql и workspace_manager.py.

Запуск пайплайна: python pipeline/full_pipeline.py --input processed_json/.

Проверка результата: SQL-запросы для проверки загруженных чанков.

Контакты: ДАША (формат JSON), ДИМА (эмбеддинг и чанкер), САША (оркестратор).