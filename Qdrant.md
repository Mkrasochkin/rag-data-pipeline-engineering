## 4. Выбор векторной базы данных

**Выбор:** Qdrant (Open-Source, Self-Hosted или Cloud)

### Обоснование выбора:

- **Высокая производительность и фильтрация:** Qdrant написан на Rust и показывает отличные результаты по скорости поиска (Latency). Критически важная фича для ТЗ — это возможность накладывать `payload filters` (фильтры по метаданным). В нашем случае это:
  - `workspace_id` (B2B изоляция)
  - `doc_id` (поиск в конкретном документе)
  - `version_status = 'active'` (поиск только по актуальным версиям)
  - `valid_from` / `valid_to` (учет даты проекта)
  
  Qdrant делает это на порядок эффективнее, чем `pgvector` при больших объемах данных (особенно при комбинации пре-фильтрации и пост-фильтрации).

- **Размерность модели:** Модель `ai-forever/ru-en-RoSBERTa` выдает эмбеддинги размерности `1024`. Qdrant отлично работает с векторами 1024 (и выше, в отличие от некоторых специализированных БД, заточенных под 768 или 384).

- **DevOps и инфраструктура:** Есть готовая интеграция с LangChain/LangGraph (стека из п.10 ответов). Легко поднимается в Docker (п.10 ответов: *"Докер будем собирать?"*).

- **Архитектурное соответствие ТЗ:** В ТЗ (п. 7.4) сказано про отдельное хранение векторов. В ответах на вопросы просят *"решения завязанные на Postgres (Supabase)"*. Qdrant идеально дополняет Supabase/Postgres, беря на себя тяжелую векторную математику, оставляя SQL базе метаданные и реляционные связи.

### Альтернатива (почему нет):

- **`pgvector`:** Не выбран, так как ТЗ явно требует отдельную векторную БД. Кроме того, при объеме >1M векторов и активной фильтрации по метаданным производительность `pgvector` на AWS RDS может деградировать, требуя тюнинга `maintenance_work_mem`.
- **ChromaDB:** Хорош для прототипов, но хуже справляется с production-нагрузкой и сложной фильтрацией по сравнению с Qdrant.

---

## 5. Объяснение: Как хранить и загружать вектора в векторную базу

**Стратегия синхронизации и хранения:** `Transactional Outbox Pattern` + `UUID Mapping`

Мы не можем хранить вектор в той же транзакции PostgreSQL, что и метаданные, так как Qdrant — это отдельная система (распределенная транзакция усложнит архитектуру). Предлагается следующий пайплайн:

### Шаг 1: Создание записи в PostgreSQL (ETL / Ingestion Service)
```python
import uuid

chunk_uuid = uuid.uuid4()
qdrant_point_uuid = uuid.uuid4()  # Генерируем ID заранее

# Вставляем в PostgreSQL
cursor.execute("""
    INSERT INTO chunks (id, qdrant_point_id, doc_id, workspace_id, text_content, clause_number, ...) 
    VALUES (%s, %s, %s, %s, %s, %s, ...)
""", (chunk_uuid, qdrant_point_uuid, ...))
```

### Шаг 2: Векторизация (Embedding Service)
Используем модель `ai-forever/ru-en-RoSBERTa`.
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('ai-forever/ru-en-RoSBERTa')
# Важно: модель выдает вектор размерности 1024
embedding = model.encode(chunk_text).tolist() 
```

### Шаг 3: Загрузка в Qdrant
Используем `qdrant_point_uuid` в качестве `id` точки. Это критически важно для связи между системами.
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

client = QdrantClient(host="localhost", port=6333)

client.upsert(
    collection_name="svodpro_chunks",
    points=[
        PointStruct(
            id=str(qdrant_point_uuid),  # Связка с Postgres!
            vector=embedding,
            payload={
                # Денормализуем метаданные для фильтрации в Qdrant
                "chunk_id": str(chunk_uuid),
                "doc_id": str(doc_id),
                "workspace_id": str(workspace_id),
                "clause_number": clause_number,
                "version_status": "active",
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
                # Сам текст хранить в payload необязательно (он в PG), 
                # но можно для быстрого дебага или если нужно вернуть текст без запроса в PG
            }
        )
    ]
)
```

### Шаг 4: Retrieval (Поиск)
1. Пользователь задает вопрос `query`.
2. Определяем `workspace_id` пользователя.
3. Векторизуем `query` той же моделью.
4. Делаем запрос в Qdrant с фильтром:
```python
client.search(
    collection_name="svodpro_chunks",
    query_vector=query_vector,
    query_filter=Filter(
        must=[
            FieldCondition(key="workspace_id", match=MatchValue(value=str(workspace_id))),
            FieldCondition(key="version_status", match=MatchValue(value="active"))
            # Добавляем фильтр по дате проекта, если есть project_metadata
        ]
    ),
    limit=10
)
```
5. Qdrant возвращает список `[point_id_1, point_id_2, ...]` и `score`.
6. Делаем запрос в PostgreSQL: `SELECT * FROM chunks WHERE qdrant_point_id IN (...)`.
7. Получаем полные тексты, номера пунктов, пути к картинкам и возвращаем пользователю.

### Почему такой подход хорош:

- **Консистентность:** Удаление документа в PG влечет удаление векторов в Qdrant по списку `qdrant_point_id`. Это гарантирует, что "сиротских" эмбеддингов не останется.
- **Гибридный поиск:** Вы легко можете сделать запрос в PG: `WHERE text_content ILIKE '%пандус%'` и объединить результаты с результатами из Qdrant (векторный поиск) для повышения `Recall@5` и покрытия кейсов с точными вхождениями.
```

#Что справшивает Андрей

RAG-сервис физически еще не поднят (занимаемся пайплайном загрузки данных), но контракт можно зафиксировать прямо сейчас.

Мы будем использовать связку FastAPI (Python) + Qdrant (векторная БД) + PostgreSQL (метаданные).
Бот будет стучаться не в Qdrant напрямую, а в нашу тонкую прослойку rag-service, которая будет делать следующее:

- Принимать текст.
- Превращать его в эмбеддинг (модель ai-forever/ru-en-RoSBERTa).
- Ходить в Qdrant и Postgres.
- Возвращать вам готовые, очищенные данные с нормативкой.

## Предлагаемый контракт (можно использовать для Mock-заглушки):

### 1. Endpoint (URL)
```
POST http://rag-service:8000/api/v1/search
```

### 2. Формат запроса (Request)
Отправляете обычный текст запроса и контекст пользователя (чтобы мы правильно отфильтровали приватные документы компании).

```json
{
  "query": "Какой уклон пандуса для МГН?",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440001",
  "project_metadata": {
    "building_type": "жилое",
    "project_year": 2025
  },
  "top_k": 5
}
```

### 3. Формат ответа (Response)
Возвращаем список чанков. Вся необходимая для цитирования информация уже будет внутри.

```json
{
  "results": [
    {
      "chunk_id": "uuid-чанка",
      "score": 0.89,
      "content": "Максимальный уклон пандуса на путях эвакуации не должен превышать 1:20 (5%).",
      "metadata": {
        "document_name": "СП 59.13330.2020",
        "clause_number": "5.1.12",
        "document_type": "СП",
        "is_active": true,
        "valid_from": "2021-07-01"
      }
    },
    {
      "chunk_id": "...",
      "score": 0.85,
      "content": "...",
      "metadata": { ... }
    }
  ]
}
```

### 4. Параметр top_k
- По умолчанию: `5`.
- Это соответствует метрике Recall@5 из ТЗ.

### 5. Для Mock-заглушки (пока нет реального Qdrant)
Чтобы вы могли писать код бота уже сейчас, можете на своей стороне захардкодить следующий ответ от нашего API на любой запрос про "пандус" или "уклон":

```json
{
  "results": [
    {
      "chunk_id": "mock-chunk-001",
      "score": 0.99,
      "content": "Уклон пандуса при перепаде высот более 3 метров следует принимать не более 5%.",
      "metadata": {
        "document_name": "СП 113.13330.2023 (МОК)",
        "clause_number": "5.26",
        "document_type": "Свод правил"
      }
    }
  ]
}
```

> Как только поднимем реальный сервис, просто переключим `base_url` в конфиге бота.
```


