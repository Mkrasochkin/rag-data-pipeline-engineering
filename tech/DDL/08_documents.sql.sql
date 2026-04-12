-- ============================================================================
-- ТАБЛИЦА: documents
-- Назначение: Метаданные нормативных документов в базе знаний
-- ВАЖНО: Реализована версионность согласно п.8.4 ТЗ
-- ============================================================================

CREATE TABLE documents (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Привязка к workspace. NULL = публичный документ, доступный всем.
    -- ON DELETE CASCADE: при удалении workspace удаляются его приватные документы.
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- UUID семейства документов. Группирует разные версии одного документа.
    -- Например, СП 113.13330.2016 и СП 113.13330.2023 имеют одинаковый document_family_id.
    document_family_id UUID,
    
    -- Тип документа. TEXT без ограничений, так как типов может быть много.
    -- Основные: 'СП', 'ГОСТ', 'СанПиН', 'ТР ТС', 'РМД', 'Пособие', 'Договор', 'Политика'.
    type TEXT NOT NULL,
    
    -- Тематика документа (например, "Пожарная безопасность", "Вентиляция").
    topic TEXT,
    
    -- Обозначение документа (например, "113.13330.2023").
    designation TEXT NOT NULL,
    
    -- Полное официальное название документа.
    official_title TEXT NOT NULL,
    
    -- Год утверждения/издания.
    year INT NOT NULL,
    
    -- Теги для фильтрации и поиска. Массив строк.
    tags TEXT[] DEFAULT '{}',
    
    -- Дата вступления документа в силу..
    valid_from DATE,
    
    -- Дата окончания действия документа. NULL = действующий.
    valid_to DATE,
    
    -- Флаг обязательности применения (может быть рекомендательным).
    is_mandatory BOOLEAN DEFAULT FALSE,
    
    -- Видимость документа: 'public' (всем), 'private' (только workspace), 'shared' (несколько workspaces).
    visibility TEXT NOT NULL DEFAULT 'public',
    
    -- Источник документа: 'official' (из реестра), 'uploaded' (загружен), 'parsed' (спарсен).
    source_type TEXT NOT NULL DEFAULT 'official',
    
    -- Кто загрузил документ (для приватных документов workspace).
    -- ON DELETE SET NULL: при удалении пользователя документ сохраняется.
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Статус версии: 'active' (действующая), 'superseded' (заменена).
    version_status TEXT DEFAULT 'active',
    
    -- Ссылка на версию, которую заменяет этот документ.
    supersedes_id UUID REFERENCES documents(id),
    
    -- Ссылка на версию, которой заменен этот документ.
    superseded_by_id UUID REFERENCES documents(id),
    
    -- Метаданные обработки: статус парсинга, ошибки, количество чанков и т.д.
    processing_metadata JSONB DEFAULT '{}',
    
    -- Время создания записи.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время последнего обновления. Обновляется триггером.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка допустимых значений видимости.
    CONSTRAINT valid_visibility CHECK (visibility IN ('public', 'private', 'shared')),
    
    -- Проверка допустимых значений статуса версии.
    CONSTRAINT valid_version_status CHECK (version_status IN ('active', 'superseded')),
    
    -- Проверка допустимых значений источника.
    CONSTRAINT valid_source CHECK (source_type IN ('official', 'uploaded', 'parsed'))
);

-- Частичный уникальный индекс: гарантирует, что в публичной базе только ОДНА активная версия документа.
-- Предотвращает ситуацию, когда одновременно активны СП 113.13330.2016 и СП 113.13330.2023.
CREATE UNIQUE INDEX idx_unique_active_version_per_family 
    ON documents (document_family_id) 
    WHERE visibility = 'public' AND version_status = 'active';

-- Индекс для поиска всех версий одного семейства документов.
CREATE INDEX idx_documents_family ON documents(document_family_id);

-- Индекс для фильтрации документов по диапазону дат действия.
-- Используется для проверки актуальности документа на дату проекта.
CREATE INDEX idx_documents_valid_range ON documents(valid_from, valid_to) WHERE valid_from IS NOT NULL;

-- Индекс для поиска документов в конкретном workspace.
CREATE INDEX idx_documents_workspace ON documents(workspace_id);

-- Индекс для фильтрации документов по типу.
CREATE INDEX idx_documents_type ON documents(type);

-- Индекс для поиска документов по обозначению (частый запрос).
CREATE INDEX idx_documents_designation ON documents(designation);

-- Индекс для фильтрации документов по видимости.
CREATE INDEX idx_documents_visibility ON documents(visibility);

-- Индекс для фильтрации документов по статусу версии.
CREATE INDEX idx_documents_version_status ON documents(version_status);

-- GIN индекс для быстрого поиска по массиву тегов.
CREATE INDEX idx_documents_tags ON documents USING GIN (tags);

-- Составной индекс для быстрого поиска публичных активных документов по обозначению и году.
CREATE INDEX idx_documents_public_active ON documents(designation, year) 
    WHERE visibility = 'public' AND version_status = 'active';