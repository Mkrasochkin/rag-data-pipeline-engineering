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