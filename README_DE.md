```text
svodpro/
├── .env                              # Секреты (пароли, ключи)
├── .gitignore                        # Игнорируем .env и данные
├── docker-compose.yml                # Запуск Qdrant
├── requirements.txt                  # Python зависимости
│
├── sql/                              # SQL скрипты для Supabase
│   └── 01_create_tables.sql          # DDL файл (full_DDL_with_comments.sql)
│
├── scripts/                          # DE скрипты
│   ├── 01_init_qdrant.py             # Создание коллекции в Qdrant
│   ├── 02_pdf_to_markdown.py         # Конвертация PDF → Markdown
│   ├── 03_clean_markdown.py          # Очистка документа от мусора
│   ├── 04_extract_metadata.py        # Извлечение метаданных для Supabase documents
│   ├── 05_section_extractor.py       # Разбивка на секции по заголовкам #, ##, ###
│   ├── 06_create_json_structure.py   # Создание JSON-файлов для всех документов
│   ├── 07_chunking.py                # Чанкование секций
│   ├── 08_embedding.py               # Эмбеддинг чанков
│   ├── 09_upload_to_qdrant.py        # Загрузка векторов в Qdrant
│   ├── 10_supabase_writer.py         # SupabaseMetadataWriter (вставка в documents и document_sections)
│   ├── 11_check_status.py            # Проверка статуса
│   └── full_pipeline.py              # Оркестратор полного пайплайна
│
├── core/                             # Общие модули и утилиты
│   ├── __init__.py
│   ├── config.py                     # Конфигурация (загрузка из .env)
│   ├── supabase_client.py            # Клиент для Supabase
│   ├── qdrant_client.py              # Клиент для Qdrant
│   └── utils.py                      # Вспомогательные функции
│
├── data/                             # Входные данные
│   └── pdfs/                         # Папка с PDF документами
│       ├── SP_113_2023.pdf
│       └── ...
│
├── output/                           # Промежуточные выходные данные
│   ├── markdown/                     # Конвертированные Markdown файлы
│   │   └── СП_113.13330.2023_Стоянки_автомобилей.md
│   ├── cleaned/                      # Очищенные Markdown файлы
│   │   └── СП_113.13330.2023_Стоянки_автомобилей_clean.md
│   └── json/                         # JSON структуры документов
│       └── СП_113.13330.2023_Стоянки_автомобилей.json
│
├── qdrant_data/                      # Данные Qdrant (авто)
│
└── README_DE.md                      # Инструкция
```
Первый запуск
# 1. Клонировать репозиторий
git clone ...
cd svodpro

# 2. Настроить .env
cp .env.example .env
nano .env  # Вставить пароль от Supabase

# 3. Запустить Qdrant
docker compose up -d

# 4. Установить зависимости
pip install -r requirements.txt

# 5. Применить схему БД в Supabase
# Зайти в Supabase → SQL Editor → Выполнить sql/01_create_tables.sql

# 6. Создать коллекцию в Qdrant
python scripts/01_init_qdrant.py

# 7. Положить PDF в папку data/pdfs/

# 8. Парсинг и чанкование → Supabase
python scripts/02_parse_and_chunk.py

# 9. Векторизация и загрузка в Qdrant
python scripts/03_embed_and_upload.py

# 10. Проверить статус
python scripts/04_check_status.py




Добавление новых документов
bash
# 1. Положить новые PDF в data/pdfs/
# 2. Запустить парсинг
python scripts/02_parse_and_chunk.py
# 3. Запустить векторизацию
python scripts/03_embed_and_upload.py




После выполнения всех шагов, передать DS:

bash
# Подключение к Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=svod_chunks

# Подключение к Supabase (для получения метаданных)
SUPABASE_DB_HOST=db.xxxx.supabase.co
SUPABASE_DB_PASSWORD=...

# Пример поиска (Python)
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Поиск с фильтром по workspace_id (RLS)
results = client.search(
    collection_name="svod_chunks",
    query_vector=user_query_vector,  # получен из RoSBERTa
    query_filter={
        "must": [
            {"key": "workspace_id", "match": {"value": workspace_id}}
        ]
    },
    limit=5
)