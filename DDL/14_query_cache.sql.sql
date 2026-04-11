-- ============================================================================
-- ТАБЛИЦА: query_cache
-- Назначение: Кеширование ответов на частые запросы для экономии токенов
-- ============================================================================

CREATE TABLE query_cache (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Хеш нормализованного запроса (MD5 или SHA256).
    -- Используется для быстрого поиска в кеше.
    query_hash TEXT UNIQUE NOT NULL,
    
    -- Оригинальный запрос после нормализации.
    -- Нормализация: приведение к нижнему регистру, удаление пунктуации.
    normalized_query TEXT,
    
    -- Закешированный ответ (текст ответа AI).
    response_text TEXT,
    
    -- Цитаты из документов, использованные в ответе.
    citations JSONB DEFAULT '[]',
    
    -- Счетчик обращений к кешу (для аналитики популярности запросов).
    hits INT NOT NULL DEFAULT 1,
    
    -- Время последнего обращения к кешу.
    last_used TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время создания записи в кеше.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для быстрого поиска по хешу (основной сценарий использования кеша).
CREATE INDEX idx_cache_hash ON query_cache(query_hash);

-- Индекс для получения самых популярных запросов (по количеству hits).
CREATE INDEX idx_cache_hits ON query_cache(hits DESC);

-- Индекс для поиска устаревших записей (для очистки кеша).
CREATE INDEX idx_cache_last_used ON query_cache(last_used DESC);