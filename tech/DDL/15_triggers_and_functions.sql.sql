-- ============================================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ updated_at
-- ============================================================================

-- Функция, обновляющая поле updated_at при любом изменении строки.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Устанавливаем текущее время в поле updated_at.
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для таблицы workspaces.
CREATE TRIGGER update_workspaces_updated_at 
    BEFORE UPDATE ON workspaces 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Триггер для таблицы projects.
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Триггер для таблицы chat_sessions.
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Триггер для таблицы documents.
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ФУНКЦИЯ ДЛЯ УВЕЛИЧЕНИЯ СЧЕТЧИКА СООБЩЕНИЙ В СЕССИИ
-- ============================================================================

CREATE OR REPLACE FUNCTION increment_message_count(p_session_id UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    -- Увеличиваем счетчик сообщений и обновляем updated_at.
    UPDATE chat_sessions 
    SET message_count = message_count + 1,
        updated_at = NOW()
    WHERE id = p_session_id;
END;
$$;

-- ============================================================================
-- ФУНКЦИЯ ДЛЯ ИНКРЕМЕНТА СЧЕТЧИКА ЗАПРОСОВ WORKSPACE
-- ============================================================================

CREATE OR REPLACE FUNCTION increment_workspace_query_counter(p_workspace_id UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    -- Увеличиваем счетчик использованных запросов в текущем месяце.
    UPDATE workspaces 
    SET queries_used_this_month = queries_used_this_month + 1,
        updated_at = NOW()
    WHERE id = p_workspace_id;
END;
$$;

-- ============================================================================
-- ФУНКЦИЯ ДЛЯ СБРОСА СЧЕТЧИКОВ ЗАПРОСОВ ПО РАСПИСАНИЮ
-- ============================================================================

CREATE OR REPLACE FUNCTION reset_expired_query_counters()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    -- Сбрасываем счетчики для всех workspaces, у которых наступила дата сброса.
    UPDATE workspaces 
    SET queries_used_this_month = 0,
        -- Устанавливаем следующую дату сброса (первое число следующего месяца).
        quota_reset_at = DATE_TRUNC('month', NOW()) + INTERVAL '1 month',
        updated_at = NOW()
    WHERE quota_reset_at <= NOW() 
      AND queries_used_this_month > 0;
END;
$$;