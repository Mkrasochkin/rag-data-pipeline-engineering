-- ============================================================================
-- ROW LEVEL SECURITY (RLS) ПОЛИТИКИ
-- Назначение: Изоляция приватных данных на уровне БД
-- ============================================================================

-- Включаем RLS для таблиц, содержащих приватные данные workspace.
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- Вспомогательная функция: получение ID текущего пользователя из сессии
-- Примечание: Бэкенд должен устанавливать переменную app.current_user_id при старте соединения.
-- Пример: SELECT set_config('app.current_user_id', user_id::TEXT, false);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    user_id_str TEXT;
BEGIN
    -- Пытаемся прочитать переменную сессии app.current_user_id.
    user_id_str := current_setting('app.current_user_id', TRUE);
    
    -- Если переменная не установлена или пустая, возвращаем NULL.
    IF user_id_str IS NULL OR user_id_str = '' THEN
        RETURN NULL;
    END IF;
    
    -- Преобразуем строку в UUID и возвращаем.
    RETURN user_id_str::UUID;
EXCEPTION
    -- При любой ошибке (например, неверный формат) возвращаем NULL.
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- ----------------------------------------------------------------------------
-- Вспомогательная функция: проверка доступа пользователя к workspace
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION user_has_workspace_access(p_workspace_id UUID, p_user_id UUID DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER  -- Выполняется с правами владельца функции (обход RLS)
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Определяем ID пользователя: переданный параметр или текущий из сессии.
    v_user_id := COALESCE(p_user_id, get_current_user_id());
    
    -- Если пользователь не определен, доступ запрещен.
    IF v_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Проверяем наличие связи пользователя с workspace в таблице user_workspaces.
    RETURN EXISTS (
        SELECT 1 FROM user_workspaces 
        WHERE user_id = v_user_id AND workspace_id = p_workspace_id
    );
END;
$$;

-- ----------------------------------------------------------------------------
-- Вспомогательная функция: получение списка workspaces пользователя
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_workspaces(p_user_id UUID DEFAULT NULL)
RETURNS UUID[]
LANGUAGE plpgsql
SECURITY DEFINER  -- Выполняется с правами владельца функции
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Определяем ID пользователя.
    v_user_id := COALESCE(p_user_id, get_current_user_id());
    
    -- Если пользователь не определен, возвращаем пустой массив.
    IF v_user_id IS NULL THEN
        RETURN ARRAY[]::UUID[];
    END IF;
    
    -- Возвращаем массив ID всех workspaces, к которым имеет доступ пользователь.
    RETURN ARRAY(
        SELECT workspace_id FROM user_workspaces WHERE user_id = v_user_id
    );
END;
$$;

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ documents
-- ============================================================================

-- Политика для SELECT:
-- 1. Видны все публичные документы (visibility = 'public')
-- 2. Видны приватные документы только для пользователей из того же workspace
CREATE POLICY documents_select_policy ON documents
    FOR SELECT
    USING (
        -- Публичные документы доступны всем.
        visibility = 'public' 
        OR (
            -- Приватные документы доступны только членам workspace.
            visibility = 'private' 
            AND workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

-- Политика для INSERT: только пользователи workspace могут добавлять документы.
CREATE POLICY documents_insert_policy ON documents
    FOR INSERT
    WITH CHECK (
        -- Публичные документы добавляются системой (workspace_id = NULL).
        workspace_id IS NULL
        -- Приватные документы может добавлять только член workspace.
        OR user_has_workspace_access(workspace_id)
    );

-- Политика для UPDATE: только пользователи workspace с ролью admin/owner.
CREATE POLICY documents_update_policy ON documents
    FOR UPDATE
    USING (
        workspace_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM user_workspaces 
            WHERE user_id = get_current_user_id() 
                AND workspace_id = documents.workspace_id 
                AND role IN ('owner', 'admin')
        )
    );

-- Политика для DELETE: только владелец workspace.
CREATE POLICY documents_delete_policy ON documents
    FOR DELETE
    USING (
        workspace_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM user_workspaces 
            WHERE user_id = get_current_user_id() 
                AND workspace_id = documents.workspace_id 
                AND role = 'owner'
        )
    );

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ chunks
-- Наследуют правила видимости от documents через doc_id
-- ============================================================================

CREATE POLICY chunks_select_policy ON chunks
    FOR SELECT
    USING (
        -- Публичные документы видны всем.
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = chunks.doc_id AND d.visibility = 'public'
        )
        OR
        -- Приватные документы видны только членам workspace.
        (
            chunks.workspace_id IS NOT NULL 
            AND user_has_workspace_access(chunks.workspace_id)
        )
    );

CREATE POLICY chunks_insert_policy ON chunks
    FOR INSERT
    WITH CHECK (
        -- Чанки публичных документов добавляются системой.
        chunks.workspace_id IS NULL 
        -- Чанки приватных документов добавляются только членами workspace.
        OR user_has_workspace_access(chunks.workspace_id)
    );

CREATE POLICY chunks_update_policy ON chunks
    FOR UPDATE
    USING (
        chunks.workspace_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM user_workspaces 
            WHERE user_id = get_current_user_id() 
                AND workspace_id = chunks.workspace_id 
                AND role IN ('owner', 'admin')
        )
    );

CREATE POLICY chunks_delete_policy ON chunks
    FOR DELETE
    USING (
        chunks.workspace_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM user_workspaces 
            WHERE user_id = get_current_user_id() 
                AND workspace_id = chunks.workspace_id 
                AND role = 'owner'
        )
    );

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ document_sections
-- ============================================================================

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

CREATE POLICY sections_insert_policy ON document_sections
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = document_sections.doc_id 
              AND (d.workspace_id IS NULL OR user_has_workspace_access(d.workspace_id))
        )
    );

CREATE POLICY sections_update_policy ON document_sections
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = document_sections.doc_id 
              AND d.workspace_id IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM user_workspaces 
                  WHERE user_id = get_current_user_id() 
                    AND workspace_id = d.workspace_id 
                    AND role IN ('owner', 'admin')
              )
        )
    );

CREATE POLICY sections_delete_policy ON document_sections
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM documents d 
            WHERE d.id = document_sections.doc_id 
              AND d.workspace_id IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM user_workspaces 
                  WHERE user_id = get_current_user_id() 
                    AND workspace_id = d.workspace_id 
                    AND role = 'owner'
              )
        )
    );

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ chat_sessions
-- Пользователь видит только свои сессии
-- ============================================================================

CREATE POLICY chat_sessions_select_policy ON chat_sessions
    FOR SELECT
    USING (user_id = get_current_user_id());

CREATE POLICY chat_sessions_insert_policy ON chat_sessions
    FOR INSERT
    WITH CHECK (user_id = get_current_user_id());

CREATE POLICY chat_sessions_update_policy ON chat_sessions
    FOR UPDATE
    USING (user_id = get_current_user_id());

CREATE POLICY chat_sessions_delete_policy ON chat_sessions
    FOR DELETE
    USING (user_id = get_current_user_id());

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ messages
-- Доступ через связь с chat_sessions (пользователь видит только свои сообщения)
-- ============================================================================

CREATE POLICY messages_select_policy ON messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions cs 
            WHERE cs.id = messages.session_id AND cs.user_id = get_current_user_id()
        )
    );

CREATE POLICY messages_insert_policy ON messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions cs 
            WHERE cs.id = messages.session_id AND cs.user_id = get_current_user_id()
        )
    );

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ projects
-- ============================================================================

CREATE POLICY projects_select_policy ON projects
    FOR SELECT
    USING (
        -- Пользователь видит свои проекты.
        created_by = get_current_user_id()
        OR (
            -- И проекты своего workspace.
            workspace_id IS NOT NULL 
            AND user_has_workspace_access(workspace_id)
        )
    );

CREATE POLICY projects_insert_policy ON projects
    FOR INSERT
    WITH CHECK (created_by = get_current_user_id());

CREATE POLICY projects_update_policy ON projects
    FOR UPDATE
    USING (created_by = get_current_user_id());

CREATE POLICY projects_delete_policy ON projects
    FOR DELETE
    USING (created_by = get_current_user_id());

-- ============================================================================
-- ПОЛИТИКИ RLS ДЛЯ ТАБЛИЦЫ document_uploads
-- ============================================================================

CREATE POLICY document_uploads_select_policy ON document_uploads
    FOR SELECT
    USING (user_has_workspace_access(workspace_id));

CREATE POLICY document_uploads_insert_policy ON document_uploads
    FOR INSERT
    WITH CHECK (
        uploaded_by = get_current_user_id() 
        AND user_has_workspace_access(workspace_id)
    );