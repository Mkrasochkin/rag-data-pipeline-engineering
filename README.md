```text
Team_DE/
├── .env                                # Секреты (пароли, ключи)
├── .gitignore                          # Игнорируем .env и данные
├── docker-compose.yml                  # Запуск Qdrant
├── requirements.txt                    # Python зависимости
├── README.md                           # Инструкция
├── run_full_pipeline.py                # Оркестратор полного пайплайна
│
├── sql/                                # SQL скрипты для Supabase
│   └── 01_create_tables.sql            # DDL файл (создание схемы, таблиц, триггеры, функции, политики)
│
├── scripts/                            # DE скрипты
│   ├── 01_pdf_to_markdown.py           # Конвертация PDF → Markdown
│   ├── 02_clean_markdown.py            # Очистка документа от мусора, извлечение метаданных для Supabase documents и document_sections в json, разбивка на секции по пунктам, создание JSON-файлов для всех документов
│   ├── 03_chunking.py                  # Чанкование секций, извлечение метаданных для Supabase chunks
│   ├── 04_embedding.py                 # Эмбеддинг чанков
│   ├── 05_upload_to_qdrant.py          # Загрузка метаданных в Supabase и векторов в Qdrant
│   ├── 06_supabase_writer.py           # Вставка метаданных из json в documents и document_sections
│   ├── 07_insert_to_qdrant.py          # Вставка векторов в Qdrant
│   ├── qdrant_helper                   # Подключение к векторной БД
│   └── supbase_helper                  # Подключение к Supabase
│
├── data/                               # Входные данные
│   └── pdfs/                           # Папка с PDF документами
│       ├── SP 1.13130.2020.pdf
│       └── ...
│
├── output/                             # Промежуточные выходные данные
│   ├── markdown/                       # Конвертированные Markdown файлы
│   │   └── SP 1.13130.2020.md
│   ├── cleaned/                        # Очищенные Markdown файлы
│   │   └── СП_1.13130.2020.md
│   └── json/                           # JSON структуры метаданных
│       └── СП_1.13130.2020.json
│
└── qdrant_data/                        # Данные Qdrant (авто)
```
