-- ============================================================================
-- ТАБЛИЦА: document_sections
-- Назначение: Иерархическая структура разделов документа
-- ============================================================================

CREATE TABLE document_sections (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Связь с документом.
    -- ON DELETE CASCADE: при удалении документа удаляются все его разделы.
    doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Номер/код раздела (например, "5", "5.1", "Приложение А").
    section_code TEXT,
    
    -- Название раздела (например, "Требования к зданиям и сооружениям").
    section_title TEXT NOT NULL,
    
    -- Полный путь в иерархии для быстрой навигации.
    -- Например: "6. Требования > 6.5 Жилые здания > 6.5.6 Одноквартирные жилые дома".
    hierarchy_path TEXT,
    
    -- Уровень вложенности (0 = корневой, 1 = раздел первого уровня и т.д.).
    level INT NOT NULL DEFAULT 0,
    
    -- Ссылка на родительский раздел для построения дерева.
    -- ON DELETE CASCADE: при удалении родителя удаляются все дочерние разделы.
    parent_section_id UUID REFERENCES document_sections(id) ON DELETE CASCADE,
    
    -- Время создания записи.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для поиска всех разделов конкретного документа.
CREATE INDEX idx_sections_doc ON document_sections(doc_id);

-- Индекс для поиска дочерних разделов по родителю.
CREATE INDEX idx_sections_parent ON document_sections(parent_section_id);

-- Индекс для поиска разделов по пути в иерархии.
CREATE INDEX idx_sections_path ON document_sections(hierarchy_path);

-- Индекс для поиска разделов по коду/номеру.
CREATE INDEX idx_sections_code ON document_sections(section_code);