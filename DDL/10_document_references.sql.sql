-- ============================================================================
-- ТАБЛИЦА: document_references
-- Назначение: Связи между документами и библиографическими ссылками
-- ============================================================================
CREATE TABLE document_references (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Документ, в котором встречается ссылка.
    -- ON DELETE CASCADE: при удалении документа удаляются его ссылки.
    source_doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Маркер ссылки в тексте (например, "[1]", "[6]", "[15]").
    ref_marker TEXT NOT NULL,
    
    -- Расшифрованное название документа-источника.
    -- Например: "Федеральный закон №190-ФЗ 'Градостроительный кодекс РФ'".
    resolved_title TEXT,
    
    -- Ссылка на документ в системе, если он загружен в базу.
    -- ON DELETE SET NULL: при удалении целевого документа связь обнуляется.
    target_doc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    
    -- Время создания записи.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для поиска всех ссылок в конкретном документе.
CREATE INDEX idx_ref_source_doc ON document_references(source_doc_id);

-- Индекс для поиска документов, которые ссылаются на конкретный документ.
CREATE INDEX idx_ref_target_doc ON document_references(target_doc_id);