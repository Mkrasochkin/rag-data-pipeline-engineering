-- ============================================================================
-- ТАБЛИЦА: messages
-- Назначение: Отдельные сообщения в рамках чат-сессии
-- ============================================================================

CREATE TABLE messages (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Связь с сессией.
    -- ON DELETE CASCADE: при удалении сессии удаляются все её сообщения.
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    
    -- Роль отправителя: 'system' (системные), 'user' (пользователь), 'assistant' (AI).
    role TEXT NOT NULL,
    
    -- Текст сообщения.
    content TEXT NOT NULL,
    
    -- Цитаты из документов в формате JSONB.
    -- Структура: [{doc_id, designation, clause_number, content, similarity_score}].
    citations JSONB NOT NULL DEFAULT '[]',
    
    -- Метаданные сообщения: latency_ms, model_used, tokens_used и т.д.
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Количество токенов в сообщении (для аналитики использования и расчета стоимости).
    token_count INT,
    
    -- Ссылка на предыдущее сообщение для построения цепочки диалога.
    -- ON DELETE SET NULL: при удалении сообщения цепочка не рвется.
    in_response_to UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    -- Время создания сообщения.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка допустимых значений роли.
    CONSTRAINT valid_role CHECK (role IN ('system', 'user', 'assistant'))
);

-- Индекс для быстрого получения всех сообщений конкретной сессии.
CREATE INDEX idx_messages_session ON messages(session_id);

-- Индекс для сортировки сообщений по времени создания.
CREATE INDEX idx_messages_created ON messages(created_at);

-- Индекс для поиска ответов на конкретное сообщение.
CREATE INDEX idx_messages_in_response_to ON messages(in_response_to);