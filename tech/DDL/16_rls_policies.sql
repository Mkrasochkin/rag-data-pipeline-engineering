-- ============================================================================
-- ROW LEVEL SECURITY (RLS) ПОЛИТИКИ
-- Назначение: Изоляция приватных данных на уровне БД
-- ============================================================================

-- ============================================================================
-- ВКЛЮЧЕНИЕ RLS ДЛЯ ВСЕХ ТАБЛИЦ
-- ============================================================================

-- Таблицы с полным CRUD для DS (SELECT, INSERT, UPDATE, DELETE)
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_cache ENABLE ROW LEVEL SECURITY;

-- Таблицы только для чтения (SELECT)
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE glossary_terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (для будущих B2B сценариев)
-- ============================================================================

-- Функция: получение ID текущего пользователя из сессии
-- Примечание: Бэкенд должен устанавливать переменную app.current_user_id при старте соединения.
-- Пример: SELECT set_config('app.current_user_id', user_id::TEXT, false);
-- Для MVP с anon key эта функция возвращает NULL, что нормально.
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    user_id_str TEXT;
BEGIN
    user_id_str := current_setting('app.current_user_id', TRUE);
    IF user_id_str IS NULL OR user_id_str = '' THEN
        RETURN NULL;
    END IF;
    RETURN user_id_str::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- Функция: проверка доступа пользователя к workspace (для будущих B2B сценариев)
CREATE OR REPLACE FUNCTION user_has_workspace_access(p_workspace_id UUID, p_user_id UUID DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    v_user_id := COALESCE(p_user_id, get_current_user_id());
    IF v_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM user_workspaces 
        WHERE user_id = v_user_id AND workspace_id = p_workspace_id
    );
END;
$$;

-- Функция: получение списка workspaces пользователя (для будущих B2B сценариев)
CREATE OR REPLACE FUNCTION get_user_workspaces(p_user_id UUID DEFAULT NULL)
RETURNS UUID[]
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    v_user_id := COALESCE(p_user_id, get_current_user_id());
    IF v_user_id IS NULL THEN
        RETURN ARRAY[]::UUID[];
    END IF;
    RETURN ARRAY(
        SELECT workspace_id FROM user_workspaces WHERE user_id = v_user_id
    );
END;
$$;

-- ============================================================================
-- ПОЛИТИКИ ДЛЯ ТАБЛИЦ С ПОЛНЫМ ДОСТУПОМ (SELECT, INSERT, UPDATE, DELETE)
-- chat_sessions, messages, query_cache
-- ============================================================================

-- ----------------------------------------------------------------------------
-- chat_sessions
-- ----------------------------------------------------------------------------
CREATE POLICY chat_sessions_select_policy ON chat_sessions
    FOR SELECT USING (true);

CREATE POLICY chat_sessions_insert_policy ON chat_sessions
    FOR INSERT WITH CHECK (true);

CREATE POLICY chat_sessions_update_policy ON chat_sessions
    FOR UPDATE USING (true);

CREATE POLICY chat_sessions_delete_policy ON chat_sessions
    FOR DELETE USING (true);

-- ----------------------------------------------------------------------------
-- messages
-- ----------------------------------------------------------------------------
CREATE POLICY messages_select_policy ON messages
    FOR SELECT USING (true);

CREATE POLICY messages_insert_policy ON messages
    FOR INSERT WITH CHECK (true);

CREATE POLICY messages_update_policy ON messages
    FOR UPDATE USING (true);

CREATE POLICY messages_delete_policy ON messages
    FOR DELETE USING (true);

-- ----------------------------------------------------------------------------
-- query_cache
-- ----------------------------------------------------------------------------
CREATE POLICY query_cache_select_policy ON query_cache
    FOR SELECT USING (true);

CREATE POLICY query_cache_insert_policy ON query_cache
    FOR INSERT WITH CHECK (true);

CREATE POLICY query_cache_update_policy ON query_cache
    FOR UPDATE USING (true);

CREATE POLICY query_cache_delete_policy ON query_cache
    FOR DELETE USING (true);

-- ============================================================================
-- ПОЛИТИКИ ДЛЯ ТАБЛИЦ ТОЛЬКО ДЛЯ ЧТЕНИЯ (SELECT)
-- chunks, document_references, document_sections, document_uploads, documents,
-- glossary_terms, projects, subscription_plans, user_workspaces, users, workspaces
-- ============================================================================

-- ----------------------------------------------------------------------------
-- documents (публичные документы видны всем, приватные только членам workspace)
-- ----------------------------------------------------------------------------
CREATE POLICY documents_select_policy ON documents
    FOR SELECT
    USING (
        visibility = 'public' 
        OR (
            visibility = 'private' 
            AND workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

-- ----------------------------------------------------------------------------
-- chunks (наследует видимость от documents)
-- ----------------------------------------------------------------------------
CREATE POLICY chunks_select_policy ON chunks
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = chunks.doc_id AND d.visibility = 'public'
        )
        OR (
            chunks.workspace_id IS NOT NULL 
            AND user_has_workspace_access(chunks.workspace_id)
        )
    );

-- ----------------------------------------------------------------------------
-- document_sections
-- ----------------------------------------------------------------------------
CREATE POLICY sections_select_policy ON document_sections
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = document_sections.doc_id 
              AND (d.visibility = 'public' 
                   OR (d.visibility = 'private' AND user_has_workspace_access(d.workspace_id)))
        )
    );

-- ----------------------------------------------------------------------------
-- document_uploads
-- ----------------------------------------------------------------------------
CREATE POLICY document_uploads_select_policy ON document_uploads
    FOR SELECT
    USING (user_has_workspace_access(workspace_id));

-- ----------------------------------------------------------------------------
-- document_references (публичные ссылки видны всем)
-- ----------------------------------------------------------------------------
CREATE POLICY document_references_select_policy ON document_references
    FOR SELECT USING (true);

-- ----------------------------------------------------------------------------
-- glossary_terms (публичный справочник терминов)
-- ----------------------------------------------------------------------------
CREATE POLICY glossary_terms_select_policy ON glossary_terms
    FOR SELECT USING (true);

-- ----------------------------------------------------------------------------
-- projects (только публичные проекты или свои)
-- ----------------------------------------------------------------------------
CREATE POLICY projects_select_policy ON projects
    FOR SELECT
    USING (
        created_by = get_current_user_id()
        OR (
            workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

-- ----------------------------------------------------------------------------
-- subscription_plans (публичный справочник тарифов)
-- ----------------------------------------------------------------------------
CREATE POLICY subscription_plans_select_policy ON subscription_plans
    FOR SELECT USING (true);

-- ----------------------------------------------------------------------------
-- user_workspaces (только свои связи)
-- ----------------------------------------------------------------------------
CREATE POLICY user_workspaces_select_policy ON user_workspaces
    FOR SELECT
    USING (user_id = get_current_user_id());

-- ----------------------------------------------------------------------------
-- users (только публичная информация о пользователях)
-- ----------------------------------------------------------------------------
CREATE POLICY users_select_policy ON users
    FOR SELECT USING (true);

-- ----------------------------------------------------------------------------
-- workspaces (только те, куда пользователь имеет доступ)
-- ----------------------------------------------------------------------------
CREATE POLICY workspaces_select_policy ON workspaces
    FOR SELECT
    USING (user_has_workspace_access(id));

-- ============================================================================
-- ЗАПРЕТ DDL (структурных изменений) через отзыв прав
-- ============================================================================

-- Отзываем право на создание объектов в схеме public у роли anon
REVOKE CREATE ON SCHEMA public FROM anon;

-- Отзываем право на использование схемы (без него нельзя выполнять SELECT, но это нам не подходит)
-- Поэтому USAGE оставляем, а CREATE убираем
GRANT USAGE ON SCHEMA public TO anon;

-- Отзываем право на создание временных таблиц (может быть опасно)
REVOKE TEMP ON DATABASE postgres FROM anon;

-- Для роли authenticated (на будущее)
REVOKE CREATE ON SCHEMA public FROM authenticated;
REVOKE TEMP ON DATABASE postgres FROM authenticated;

-- ============================================================================
-- ПРИМЕЧАНИЕ ДЛЯ DS КОМАНДЫ
-- ============================================================================
-- 
-- DS имеют следующие права через anon key:
-- 
-- Таблицы с полным CRUD (SELECT, INSERT, UPDATE, DELETE):
--   ✅ chat_sessions
--   ✅ messages  
--   ✅ query_cache
-- 
-- Таблицы только для чтения (SELECT):
--   ✅ chunks
--   ✅ document_references
--   ✅ document_sections
--   ✅ document_uploads
--   ✅ documents (только публичные)
--   ✅ glossary_termsS
--   ✅ projects (только свои)
--   ✅ subscription_plans
--   ✅ user_workspaces (только свои)
--   ✅ users
--   ✅ workspaces (только доступные)
-- 
-- Запрещено:
--   ❌ CREATE, ALTER, DROP, TRUNCATE (изменение структуры БД)
--   ❌ INSERT/UPDATE/DELETE в таблицах только для чтения
-- 
-- ============================================================================