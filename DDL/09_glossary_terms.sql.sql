-- ============================================================================
-- ТАБЛИЦА: glossary_terms (п.5 "Ответов на вопросы")
-- Назначение: Централизованное хранилище терминов для нормализации и query rewriting
-- ============================================================================
CREATE TABLE glossary_terms (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Термин (например, "пандус", "рампа").
    term TEXT NOT NULL,
    
    -- Определение термина из нормативного документа.
    definition TEXT NOT NULL,
    
    -- Ссылка на документ-источник (глава "Термины и определения").
    -- ON DELETE CASCADE: при удалении документа удаляются его термины.
    source_doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Синонимы и альтернативные написания термина (например, ["рампа", "наклонная поверхность"]).
    -- Используется для расширения поискового запроса (query expansion).
    aliases TEXT[] DEFAULT '{}',
    
    -- Время создания записи.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- GIN индекс с триграммами для нечеткого поиска по термину.
-- Позволяет находить термины даже с опечатками (например, "пондус" -> "пандус").
CREATE INDEX idx_glossary_term ON glossary_terms USING GIN (term gin_trgm_ops);

-- Индекс для поиска всех терминов из конкретного документа.
CREATE INDEX idx_glossary_source ON glossary_terms(source_doc_id);