-- ============================================================================
-- ТАБЛИЦА: chunks
-- Назначение: Фрагменты документов для векторного поиска (RAG)
-- ВАЖНО: Один чанк может содержать НЕСКОЛЬКО пунктов, если они короткие и идут подряд
-- Вектор хранится во внешней векторной БД (Qdrant), связь через qdrant_point_id
-- ============================================================================

CREATE TABLE chunks (
    -- Первичный ключ. UUID v4 генерируется автоматически.
    -- Этот же ID используется как Point ID в Qdrant для синхронизации.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ID точки в Qdrant. Дублирует id для удобства внешних запросов и дебага.
    -- Уникальное, так как каждый чанк имеет ровно один вектор в Qdrant.
    qdrant_point_id UUID UNIQUE,
    
    -- Связь с документом. Обязательное поле.
    -- ON DELETE CASCADE: при удалении документа удаляются все его чанки.
    doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Связь с разделом документа. Может быть NULL, если чанк не привязан к разделу.
    -- ON DELETE SET NULL: при удалении раздела чанк сохраняется.
    section_id UUID REFERENCES document_sections(id) ON DELETE SET NULL,
    
    -- Денормализованный workspace_id. КРИТИЧЕСКИ ВАЖНО для RLS и фильтрации поиска.
    -- Передается в Qdrant как payload для фильтрации результатов по workspace.
    -- ON DELETE CASCADE: при удалении workspace удаляются все его чанки.
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Путь в иерархии разделов (копия из document_sections.hierarchy_path).
    -- Используется для отображения контекста в UI и навигации.
    section_path TEXT,
    
    -- Начальный пункт в чанке (например, "5.26.1")
    -- Может быть NULL, если чанк не привязан к конкретному пункту
    clause_start TEXT,
    
    -- Конечный пункт в чанке (например, "5.26.3")
    -- Если чанк содержит только один пункт, clause_start = clause_end
    -- NULL, если чанк не привязан к пунктам
    clause_end TEXT,
    
    -- Массив ВСЕХ номеров пунктов, включенных в чанк
    -- Пример: ['5.26.1', '5.26.2', '5.26.3']
    -- Используется для точного поиска по номеру пункта (UC1) и валидации ответов LLM
    -- GIN индекс позволяет быстро искать: WHERE '5.26.1' = ANY(clause_numbers)
    clause_numbers TEXT[] DEFAULT '{}',
    
    -- Человеко-читаемое отображение пунктов для UI
    -- Например: "п. 5.26.1" (один пункт) или "пп. 5.26.1-5.26.3" (диапазон)
    -- Генерируется в ETL пайплайне, чтобы не вычислять на лету
    clause_display TEXT,
    
    -- Количество пунктов, объединенных в этот чанк
    -- 0 = чанк без пунктов
    -- 1 = один пункт
    -- >1 = несколько пунктов объединены
    merged_clauses_count INT DEFAULT 1,
    
    -- Порядковый номер чанка в документе.
    -- Используется для навигации ("следующий чанк", "предыдущий чанк") и сортировки.
    chunk_index INT,
    
    -- Тип контента: 'text', 'table', 'formula', 'image'
    -- Определяет, как отображать и обрабатывать чанк.
    content_type TEXT NOT NULL DEFAULT 'text',
    
    -- Ссылка на родительский чанк для иерархической навигации.
    -- Например, чанк с таблицей может быть дочерним для чанка с текстом.
    -- ON DELETE SET NULL: при удалении родителя связь обнуляется.
    parent_chunk_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
    
    -- URL для изображений
    -- NULL для текстовых чанков.
    content_url TEXT,
    
    -- Текстовое содержимое чанка. ОБЯЗАТЕЛЬНОЕ ПОЛЕ.
    -- Для объединенных пунктов содержит текст всех пунктов подряд с сохранением нумерации.
    -- Для чанков типа 'image'/'table' содержит OCR-текст или текстовое описание.
    -- Используется для полнотекстового поиска и как контекст для LLM.
    text_content TEXT NOT NULL,
    
    -- Количество токенов в text_content.
    -- Используется для контроля размера чанка при объединении пунктов (лимит ~500 токенов).
    token_count INT,
    
    -- Время создания чанка.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка допустимых значений типа контента.
    CONSTRAINT valid_content_type CHECK (content_type IN ('text', 'table', 'formula', 'image')),
    
    -- Проверка, что если указан clause_start, то и clause_end должен быть указан.
    CONSTRAINT clause_range_valid CHECK (
        (clause_start IS NULL AND clause_end IS NULL) OR 
        (clause_start IS NOT NULL AND clause_end IS NOT NULL)
    ),
    
    -- Проверка, что merged_clauses_count соответствует clause_numbers
    CONSTRAINT merged_count_valid CHECK (
        merged_clauses_count >= 0 AND
        (clause_numbers IS NULL OR array_length(clause_numbers, 1) = merged_clauses_count)
    )
);

-- Индекс для поиска всех чанков конкретного документа.
-- Высокочастотный запрос при навигации по документу.
CREATE INDEX idx_chunks_doc ON chunks(doc_id);

-- Индекс для поиска чанков в конкретном разделе.
CREATE INDEX idx_chunks_section ON chunks(section_id);

-- Индекс для фильтрации чанков по workspace.
-- КРИТИЧЕСКИ ВАЖНО для RLS и быстрой фильтрации при поиске.
CREATE INDEX idx_chunks_workspace ON chunks(workspace_id);

-- Индекс для фильтрации чанков по типу контента.
-- Используется, когда нужно искать только текст или только таблицы.
CREATE INDEX idx_chunks_type ON chunks(content_type);

-- Индекс для поиска дочерних чанков по родителю.
CREATE INDEX idx_chunks_parent ON chunks(parent_chunk_id);

-- Составной индекс для сортировки чанков по порядку в документе.
-- Используется для пагинации и навигации "следующий/предыдущий".
CREATE INDEX idx_chunks_doc_index ON chunks(doc_id, chunk_index);

-- Индекс для поиска по начальному пункту.
-- Используется при запросах вида "найти все чанки, начиная с пункта 5.26".
CREATE INDEX idx_chunks_clause_start ON chunks(clause_start) WHERE clause_start IS NOT NULL;

-- GIN индекс для поиска по массиву номеров пунктов.
-- КЛЮЧЕВОЙ ИНДЕКС для UC1: "В каком пункте описываются требования к уклонам?"
-- Позволяет искать: WHERE '5.26.1' = ANY(clause_numbers)
CREATE INDEX idx_chunks_clause_numbers ON chunks USING GIN (clause_numbers);

-- GIN индекс с триграммами для полнотекстового поиска по содержимому.
-- Используется в гибридном поиске (векторный + полнотекстовый).
-- pg_trgm поддерживает нечеткий поиск и поиск по подстроке.
CREATE INDEX idx_chunks_text_content ON chunks USING GIN (text_content gin_trgm_ops);

-- Индекс для поиска по qdrant_point_id (используется при синхронизации и удалении).
CREATE INDEX idx_chunks_qdrant_point ON chunks(qdrant_point_id) WHERE qdrant_point_id IS NOT NULL;