-- ============================================================================
-- ТАБЛИЦА: chat_sessions
-- Назначение: Сессии общения с AI-ассистентом, сгруппированные по проектам
-- ============================================================================

CREATE TABLE chat_sessions (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Пользователь, ведущий диалог.
    -- ON DELETE CASCADE: при удалении пользователя удаляются его сессии.
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Связь с проектом (опционально).
    -- ON DELETE SET NULL: при удалении проекта сессия сохраняется, но теряет привязку.
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    
    -- Автоматически генерируемый заголовок сессии (первый вопрос пользователя).
    title TEXT,
    
    -- Контекстное окно диалога в формате JSONB.
    -- Структура: {"window_size": 5, "messages": [{role, content, timestamp}]}.
    -- Используется для многошагового диалога (Feature #2).
    context_window JSONB NOT NULL DEFAULT '{"window_size": 5, "messages": []}',
    
    -- Денормализованный счетчик сообщений для быстрого отображения в UI.
    message_count INT NOT NULL DEFAULT 0,
    
    -- Флаг активности сессии. FALSE = сессия завершена/архивирована.
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Время создания сессии.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время последней активности в сессии. Обновляется триггером.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка, что счетчик сообщений не может быть отрицательным.
    CONSTRAINT non_negative_messages CHECK (message_count >= 0)
);

-- Индекс для поиска всех сессий конкретного пользователя.
CREATE INDEX idx_sessions_user ON chat_sessions(user_id);

-- Индекс для поиска всех сессий в конкретном проекте.
CREATE INDEX idx_sessions_project ON chat_sessions(project_id);

-- Частичный индекс для быстрого получения только активных сессий.
CREATE INDEX idx_sessions_active ON chat_sessions(is_active) WHERE is_active = true;

-- Индекс для сортировки сессий по дате обновления (частый запрос в UI).
CREATE INDEX idx_sessions_updated ON chat_sessions(updated_at DESC);