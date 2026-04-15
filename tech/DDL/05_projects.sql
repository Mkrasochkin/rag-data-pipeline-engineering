-- ============================================================================
-- ТАБЛИЦА: projects
-- Назначение: Группировка чат-сессий по проектам (Feature #1 из ТЗ)
-- ============================================================================

CREATE TABLE projects (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Связь с workspace. NULL для личных проектов пользователей (вне workspace).
    -- ON DELETE CASCADE: при удалении workspace удаляются все его проекты.
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Пользователь, создавший проект.
    -- ON DELETE CASCADE: при удалении пользователя удаляются его проекты.
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Название проекта (например, "ЖК Солнечный", "Школа №45").
    name TEXT NOT NULL,
    
    -- Описание проекта (опционально).
    description TEXT,
    
    -- Метаданные проекта в формате JSONB.
    -- Хранит: адрес объекта, тип здания, этажность, дату начала проектирования.
    -- Используется для выбора корректной версии нормативов (п.8.4 ТЗ).
    project_metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Флаг активности проекта. FALSE = архивный проект.
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Время создания проекта.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время последнего обновления. Обновляется триггером.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Уникальность имени проекта в рамках: workspace + пользователь.
    -- Позволяет разным пользователям иметь проекты с одинаковыми названиями.
    CONSTRAINT unique_project_name_per_user UNIQUE (workspace_id, created_by, name)
);

-- Индекс для поиска всех проектов, созданных конкретным пользователем.
CREATE INDEX idx_projects_created_by ON projects(created_by);

-- Индекс для поиска всех проектов в конкретном workspace.
CREATE INDEX idx_projects_workspace ON projects(workspace_id);

-- Частичный индекс для быстрого получения только активных проектов.
CREATE INDEX idx_projects_active ON projects(is_active) WHERE is_active = true;