-- ============================================================================
-- ТАБЛИЦА: document_uploads
-- Назначение: Отслеживание процесса загрузки документов (Post-MVP Feature #3)
-- ============================================================================

CREATE TABLE document_uploads (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Workspace, в который загружается документ.
    -- ON DELETE CASCADE: при удалении workspace удаляется история загрузок.
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Пользователь, загрузивший документ.
    -- ON DELETE CASCADE: при удалении пользователя история загрузок сохраняется? 
    -- В DDL указано CASCADE, но логичнее SET NULL. Проверить!
    uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Оригинальное имя загруженного файла (например, "СП_113_13330_2023.pdf").
    original_filename TEXT NOT NULL,
    
    -- Путь к файлу в объектном хранилище (S3/MinIO).
    storage_path TEXT NOT NULL,
    
    -- MIME-тип файла (например, "application/pdf").
    mime_type TEXT,
    
    -- Размер файла в байтах.
    file_size_bytes BIGINT,
    
    -- Статус обработки: 'pending', 'processing', 'completed', 'failed'.
    processing_status TEXT NOT NULL DEFAULT 'pending',
    
    -- JSONB массив ошибок валидации/обработки.
    -- Пример: [{"field": "pages", "error": "Unable to parse page 5"}].
    validation_errors JSONB DEFAULT '[]',
    
    -- Ссылка на созданный документ после успешной обработки.
    -- ON DELETE SET NULL: при удалении документа запись о загрузке сохраняется.
    resulting_doc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    
    -- Время создания записи о загрузке.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время завершения обработки (успешной или с ошибкой).
    completed_at TIMESTAMPTZ,
    
    -- Проверка допустимых значений статуса обработки.
    CONSTRAINT valid_upload_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- Проверка, что размер файла положительный (если указан).
    CONSTRAINT positive_file_size CHECK (file_size_bytes IS NULL OR file_size_bytes > 0)
);

-- Индекс для поиска всех загрузок в конкретном workspace.
CREATE INDEX idx_uploads_workspace ON document_uploads(workspace_id);

-- Индекс для фильтрации загрузок по статусу (например, найти все pending).
CREATE INDEX idx_uploads_status ON document_uploads(processing_status);

-- Индекс для сортировки загрузок по дате создания (частый запрос в админке).
CREATE INDEX idx_uploads_created ON document_uploads(created_at DESC);

-- Индекс для поиска всех загрузок конкретного пользователя.
CREATE INDEX idx_uploads_uploaded_by ON document_uploads(uploaded_by);