```text
Team_DE/
├── .env                                # Секреты (пароли, ключи)
├── .gitignore                          # Игнорируем .env и данные
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

# Предварительные требования

**ВМ:** Сервер с Linux (например, Ubuntu 20.04/22.04).

**Доступ:** SSH-доступ к ВМ. Ваш пользователь должен быть в группе docker (обычно настраивается администратором).

**Сервисы:** Аккаунт и проект в Supabase для облачной БД.

---

## Шаг 1: Подключение к ВМ и установка зависимостей ОС

Подключитесь к вашей ВМ по SSH и выполните начальную настройку.

```
# 1. Подключение
ssh ваш_пользователь@<IP_АДРЕС_ВМ>

# 2. Обновление пакетов
sudo apt update && sudo apt upgrade -y

# 3. Установка Python, pip, git и сетевых утилит
sudo apt install -y python3 python3-pip python3-venv git net-tools curl
```

---

## Шаг 2: Клонирование репозитория и настройка переменных окружения

```
# 1. Клонируйте ваш проект (замените URL на реальный)
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> svodpro
cd svodpro

# 2. Создайте виртуальное окружение Python и активируйте его
python3 -m venv venv
source venv/bin/activate

# 3. Установите Python-зависимости
pip install -r requirements.txt
```

Теперь создайте и заполните файл `.env` в корне проекта (`svodpro/.env`). Это самый важный шаг конфигурации.

```
nano .env
```

Скопируйте и заполните содержимое. Возьмите `SUPABASE_URL` и `SUPABASE_PRIVATE_KEY_LONG` из настроек вашего проекта в Supabase (Settings -> API -> Project URL и service_role key).

```
# .env
SUPABASE_URL=https://ваш-проект.supabase.co
SUPABASE_PRIVATE_KEY_LONG=eyJhbGciOiJI...ваш-длинный-ключ

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=
```



---

## Шаг 3: Настройка облачной базы данных (Supabase)

Выполните этот шаг один раз для инициализации схемы базы данных.

1. Войдите в Supabase Dashboard вашего проекта.
2. Перейдите в **SQL Editor**.
3. Откройте файл `sql/01_create_tables.sql` из вашего проекта локально и скопируйте его полное содержимое.
4. Вставьте скрипт в редактор Supabase и нажмите **Run**.
5. Дождитесь успешного выполнения. Вы увидите сообщение *"Success. No rows returned"*. Все таблицы, индексы и политики будут созданы.

---

## Шаг 4: Установка Docker и запуск Qdrant

Следуйте подпроцессу для установки Docker, если он еще не настроен на ВМ.

### 4.1. Установка Docker Engine

```
# Установите необходимые пакеты для добавления репозитория Docker
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Добавьте репозиторий в источники Apt
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Установите Docker Engine, CLI, containerd и плагин Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Добавьте вашего пользователя в группу docker, чтобы не использовать sudo
sudo usermod -aG docker $USER
```

> **Важно:** После добавления в группу `docker` нужно перезайти в сессию (выйти и зайти по SSH) или выполнить `newgrp docker`.

### 4.2. Запуск Qdrant

В проекте уже есть готовый `docker-compose.yml` файл. Запустите им контейнер.

```
# Находясь в корневой папке проекта, запустите Qdrant в фоне
docker compose up -d
```

**Проверка работы:**

```
# Проверка, что контейнер работает
docker ps

# Проверка HTTP API Qdrant
curl http://localhost:6333
```

В ответ вы должны получить JSON с версией Qdrant.

---

## Шаг 5: Подготовка данных и полный запуск пайплайна

Перед запуском убедитесь, что выполнены все предыдущие шаги: активировано виртуальное окружение, Qdrant запущен, Supabase настроен.

### 5.1. Размещение PDF-файлов

Поместите ваши PDF-файлы нормативных документов в папку `data/pdfs/`.

```
# Пример копирования файлов в нужную папку
cp /путь/к/вашим/*.pdf data/pdfs/
```

### 5.2. Запуск главного оркестратора

Теперь запустите `run_full_pipeline.py`. Он последовательно выполнит все шаги, от конвертации PDF до загрузки данных в Supabase и Qdrant.

```
python run_full_pipeline.py
```

**Что будет происходить по шагам (как задумано в скрипте):**

1. `pdf_to_markdown.py`: Конвертирует все PDF из `data/pdfs/` в формат Markdown и сохранит результат в `output/markdown/`.
2. `clean_markdown.py`: Очистит Markdown-файлы, извлечет метаданные, разобьет на секции и создаст JSON-файлы в `output/json/` и очищенные `.md` в `output/cleaned/`.
3. `supabase_writer.py`: Считает JSON-файлы и запишет метаданные документов и их разделов в облачную БД Supabase (таблицы `documents` и `document_sections`).

**Далее по основному коду `run_full_pipeline.py`:**

- Считает очищенные `.md` файлы.
- Выполнит "Chunking" (нарезку) и эмбеддинг текста прямо в памяти, используя классы `SPDocumentChunker` и `Embedder`.
- Запишет чанки в таблицу `chunks` в Supabase.
- Вставит векторные представления чанков в коллекцию `sp_chunks` в Qdrant.

### 5.3. Валидация (как проверить, что все работает)

**Supabase:** Зайдите в Supabase Dashboard -> Table Editor.

- Проверьте таблицы `documents`, `document_sections` и `chunks`. В них должны появиться записи.

**Qdrant:** Выполните API-запрос к коллекции.

```
curl http://localhost:6333/collections/sp_chunks
```

Если коллекция существует и количество векторов (`vectors_count`) больше 0, значит, загрузка прошла успешно.

---

## Заключение и полезные команды

Проект развернут и успешно отработал.

**Управление Qdrant:**

- Остановить: `docker compose stop`
- Запустить: `docker compose start`
- Посмотреть логи: `docker compose logs -f`

**Повторный запуск пайплайна:** Просто снова активируйте виртуальное окружение (`source venv/bin/activate`) и запускайте `python run_full_pipeline.py`. Скрипты upsert (обновляют или вставляют) безопасно обновят данные в Supabase и Qdrant для тех же документов.
```