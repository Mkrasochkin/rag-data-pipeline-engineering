-- ============================================================================
-- ROW LEVEL SECURITY (RLS) ПОЛИТИКИ
-- Назначение: Изоляция приватных данных на уровне БД
-- Доступ:
--   - postgres / supabase_admin / DE команда: полные права (DDL + DML)
--   - authenticated (команда DS): CRUD в указанных таблицах + SELECT в остальных
--   - anon: полный запрет доступа
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
-- ОТКЛЮЧЕНИЕ ДОСТУПА ДЛЯ РОЛИ anon КО ВСЕМ ТАБЛИЦАМ
-- ============================================================================

-- Отзываем все права у роли anon на все таблицы
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon', r.tablename);
    END LOOP;
END $$;

-- Отзываем USAGE на схему public для anon
REVOKE USAGE ON SCHEMA public FROM anon;

-- ============================================================================
-- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (для будущих B2B сценариев)
-- ============================================================================

-- Функция: получение ID текущего пользователя из сессии
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
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

-- Функция: проверка доступа пользователя к workspace
CREATE OR REPLACE FUNCTION user_has_workspace_access(p_workspace_id UUID, p_user_id UUID DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
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

-- Функция: получение списка workspaces пользователя
CREATE OR REPLACE FUNCTION get_user_workspaces(p_user_id UUID DEFAULT NULL)
RETURNS UUID[]
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
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
-- ПОЛИТИКИ ДЛЯ ТАБЛИЦ С ПОЛНЫМ CRUD (ТОЛЬКО ДЛЯ authenticated)
-- chat_sessions, messages, query_cache
-- ============================================================================

-- ----------------------------------------------------------------------------
-- chat_sessions: полный доступ для DS команды
-- ----------------------------------------------------------------------------
CREATE POLICY chat_sessions_ds_policy ON chat_sessions
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- messages: полный доступ для DS команды
-- ----------------------------------------------------------------------------
CREATE POLICY messages_ds_policy ON messages
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- query_cache: полный доступ для DS команды
-- ----------------------------------------------------------------------------
CREATE POLICY query_cache_ds_policy ON query_cache
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- ПОЛИТИКИ ДЛЯ ТАБЛИЦ ТОЛЬКО ДЛЯ ЧТЕНИЯ (ТОЛЬКО ДЛЯ authenticated)
-- chunks, document_references, document_sections, document_uploads, documents,
-- glossary_terms, projects, subscription_plans, user_workspaces, users, workspaces
-- ============================================================================

-- ----------------------------------------------------------------------------
-- documents: публичные видны всем DS, приватные - только своим workspace
-- ----------------------------------------------------------------------------
CREATE POLICY documents_select_policy ON documents
    FOR SELECT
    TO authenticated
    USING (
        visibility = 'public' 
        OR (
            visibility = 'private' 
            AND workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

-- ----------------------------------------------------------------------------
-- chunks: наследует видимость от documents
-- ----------------------------------------------------------------------------
CREATE POLICY chunks_select_policy ON chunks
    FOR SELECT
    TO authenticated
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
-- document_sections: доступ через родительский документ
-- ----------------------------------------------------------------------------
CREATE POLICY document_sections_select_policy ON document_sections
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = document_sections.doc_id 
              AND (d.visibility = 'public' 
                   OR (d.visibility = 'private' AND user_has_workspace_access(d.workspace_id)))
        )
    );

-- ----------------------------------------------------------------------------
-- document_uploads: только загрузки из доступных workspace
-- ----------------------------------------------------------------------------
CREATE POLICY document_uploads_select_policy ON document_uploads
    FOR SELECT
    TO authenticated
    USING (user_has_workspace_access(workspace_id));

-- ----------------------------------------------------------------------------
-- document_references: все DS видят все ссылки
-- ----------------------------------------------------------------------------
CREATE POLICY document_references_select_policy ON document_references
    FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- glossary_terms: справочник терминов виден всем DS
-- ----------------------------------------------------------------------------
CREATE POLICY glossary_terms_select_policy ON glossary_terms
    FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- projects: только свои или из доступного workspace
-- ----------------------------------------------------------------------------
CREATE POLICY projects_select_policy ON projects
    FOR SELECT
    TO authenticated
    USING (
        created_by = get_current_user_id()
        OR (
            workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

-- ----------------------------------------------------------------------------
-- subscription_plans: справочник тарифов виден всем DS
-- ----------------------------------------------------------------------------
CREATE POLICY subscription_plans_select_policy ON subscription_plans
    FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- user_workspaces: только свои связи
-- ----------------------------------------------------------------------------
CREATE POLICY user_workspaces_select_policy ON user_workspaces
    FOR SELECT
    TO authenticated
    USING (user_id = get_current_user_id());

-- ----------------------------------------------------------------------------
-- users: публичная информация о пользователях видна всем DS
-- ----------------------------------------------------------------------------
CREATE POLICY users_select_policy ON users
    FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- workspaces: только те, куда пользователь имеет доступ
-- ----------------------------------------------------------------------------
CREATE POLICY workspaces_select_policy ON workspaces
    FOR SELECT
    TO authenticated
    USING (user_has_workspace_access(id));

-- ============================================================================
-- ВЫДАЧА ПРАВ ДЛЯ РОЛИ authenticated
-- ============================================================================

-- Даем USAGE на схему public
GRANT USAGE ON SCHEMA public TO authenticated;

-- Таблицы с полным CRUD
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON messages TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON query_cache TO authenticated;

-- Таблицы только для чтения
GRANT SELECT ON chunks TO authenticated;
GRANT SELECT ON document_references TO authenticated;
GRANT SELECT ON document_sections TO authenticated;
GRANT SELECT ON document_uploads TO authenticated;
GRANT SELECT ON documents TO authenticated;
GRANT SELECT ON glossary_terms TO authenticated;
GRANT SELECT ON projects TO authenticated;
GRANT SELECT ON subscription_plans TO authenticated;
GRANT SELECT ON user_workspaces TO authenticated;
GRANT SELECT ON users TO authenticated;
GRANT SELECT ON workspaces TO authenticated;

-- ============================================================================
-- ЗАПРЕТ DDL (структурных изменений) для authenticated
-- ============================================================================

REVOKE CREATE ON SCHEMA public FROM authenticated;
REVOKE TEMP ON DATABASE postgres FROM authenticated;

-- ============================================================================
-- СВОДКА ПРАВ ДОСТУПА
-- ============================================================================
-- 
-- ┌─────────────────────────┬────────────┬──────────────────┬─────────────┐
-- │ Роль                    │ BYPASSRLS  │ chat_sessions    │ documents   │
-- │                         │            │ messages         │ chunks      │
-- │                         │            │ query_cache      │ projects    │
-- ├─────────────────────────┼────────────┼──────────────────┼─────────────┤
-- │ postgres (DE)           │    ✅ Да   │ ✅ ПОЛНЫЙ ДОСТУП │ ✅ ПОЛНЫЙ   │
-- │ supabase_admin          │    ✅ Да   │ ✅ ПОЛНЫЙ ДОСТУП │ ✅ ПОЛНЫЙ   │
-- ├─────────────────────────┼────────────┼──────────────────┼─────────────┤
-- │ authenticated (DS)      │    ❌ Нет  │ ✅ CRUD (через RLS)│ ✅ SELECT  │
-- ├─────────────────────────┼────────────┼──────────────────┼─────────────┤
-- │ anon                    │    ❌ Нет  │ ❌ НЕТ ДОСТУПА   │ ❌ НЕТ      │
-- └─────────────────────────┴────────────┴──────────────────┴─────────────┘
-- 
-- ============================================================================
-- ПРИМЕЧАНИЕ ДЛЯ DE КОМАНДЫ
-- ============================================================================
-- 
-- 1. DE должны подключаться к БД используя роль postgres
-- 
-- 2. При добавлении новых таблиц НЕ ЗАБЫВАТЬ:
--    - ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
--    - REVOKE ALL ON new_table FROM anon;
--    - GRANT нужные права TO authenticated;
--    - Создать политику для authenticated;
-- 
-- ============================================================================
-- ПРИМЕЧАНИЕ ДЛЯ DS КОМАНДЫ
-- ============================================================================
-- 
-- 1. DS должны входить через Supabase Dashboard ИЛИ через код:
--    - const { data } = await supabase.auth.signInWithPassword({...})
-- 
-- 2. Доступные таблицы для CRUD:
--    ✅ chat_sessions
--    ✅ messages  
--    ✅ query_cache
-- 
-- 3. Доступные таблицы только для чтения:
--    ✅ все остальные таблицы схемы public
-- 
-- 4. Запрещено:
--    ❌ CREATE, ALTER, DROP, TRUNCATE
--    ❌ INSERT/UPDATE/DELETE в таблицы только для чтения
-- 
-- ============================================================================