-- ============================================================================
-- ТАБЛИЦА: user_workspaces
-- Назначение: Связь многие-ко-многим между пользователями и workspaces с указанием роли
-- ============================================================================

CREATE TABLE user_workspaces (
    -- Внешний ключ на пользователя.
    -- ON DELETE CASCADE: при удалении пользователя удаляются все его связи с workspaces.
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Внешний ключ на workspace.
    -- ON DELETE CASCADE: при удалении workspace удаляются все связи с пользователями.
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Роль пользователя в workspace. По умолчанию 'engineer' (обычный инженер).
    -- Возможные значения: 'owner', 'admin', 'engineer', 'viewer', 'compliance', 'support'.
    role TEXT NOT NULL DEFAULT 'engineer',
    
    -- Дата и время добавления пользователя в workspace.
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Кто пригласил пользователя (для аудита действий).
    -- ON DELETE SET NULL: при удалении пригласившего связь не теряется.
    invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Составной первичный ключ (user_id, workspace_id).
    -- Гарантирует, что пользователь не может быть добавлен в один workspace дважды.
    PRIMARY KEY (user_id, workspace_id),
    
    -- Проверка допустимых значений роли.
    CONSTRAINT valid_role CHECK (role IN ('owner', 'admin', 'engineer', 'viewer', 'compliance', 'support'))
);

-- Индекс для быстрого поиска всех пользователей конкретного workspace.
CREATE INDEX idx_user_workspaces_workspace ON user_workspaces(workspace_id);

-- Индекс для быстрой фильтрации пользователей по роли (например, найти всех админов).
CREATE INDEX idx_user_workspaces_role ON user_workspaces(role);