-- ============================================================================
-- ТАБЛИЦА: workspaces
-- Назначение: Изолированные рабочие пространства для B2B клиентов и personal аккаунтов
-- ============================================================================

CREATE TABLE workspaces (
    -- Первичный ключ. UUID v4.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Название рабочего пространства (например, "ООО Проектный Институт №5").
    name TEXT NOT NULL,
    
    -- Уровень биллинга workspace. Определяет лимиты и доступные функции.
    -- По умолчанию 'free'. Значения: 'free', 'pro', 'business', 'enterprise', 'enterprise_plus'.
    billing_tier TEXT NOT NULL DEFAULT 'free',
    
    -- Денормализованный счетчик пользователей в workspace.
    -- Обновляется триггерами. Используется для быстрой проверки лимита max_users.
    user_count INT NOT NULL DEFAULT 0,
    
    -- Денормализованный счетчик загруженных документов в workspace.
    -- Обновляется триггерами. Используется для быстрой проверки лимита max_documents.
    document_count INT NOT NULL DEFAULT 0,
    
    -- Количество запросов к LLM/RAG, использованных в текущем расчетном периоде.
    -- Инкрементируется при каждом вызове. Сбрасывается в 0 по cron-задаче.
    queries_used_this_month INT NOT NULL DEFAULT 0,
    
    -- Статус подписки: 'active' (активна), 'past_due' (просрочена), 'canceled' (отменена), 'trial' (пробный период).
    subscription_status TEXT NOT NULL DEFAULT 'active',
    
    -- Дата окончания пробного периода. По умолчанию +14 дней от создания.
    -- NULL, если пробный период не применяется или уже завершен.
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    
    -- Дата следующего сброса счетчиков квот (обычно первое число следующего месяца).
    quota_reset_at TIMESTAMPTZ NOT NULL DEFAULT (DATE_TRUNC('month', NOW()) + INTERVAL '1 month'),
    
    -- Флаг, активирована ли собственная база знаний для этого workspace.
    -- TRUE, если клиент оплатил опцию custom KB.
    custom_kb_enabled BOOLEAN DEFAULT FALSE,
    
    -- Дата активации собственной базы знаний.
    -- Используется для биллинга (единоразовый платеж взимается при первой активации).
    custom_kb_activated_at TIMESTAMPTZ,
    
    -- Ссылка на пользователя, создавшего workspace.
    -- ON DELETE SET NULL: при удалении пользователя workspace сохраняется.
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Время создания workspace.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Время последнего обновления workspace. Обновляется триггером.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка допустимых значений billing_tier.
    CONSTRAINT valid_billing_tier CHECK (billing_tier IN ('free', 'pro', 'business', 'enterprise', 'enterprise_plus')),
    
    -- Проверка допустимых значений статуса подписки.
    CONSTRAINT valid_subscription_status CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'trial')),
    
    -- Проверка, что счетчики не могут быть отрицательными.
    CONSTRAINT non_negative_counts CHECK (user_count >= 0 AND document_count >= 0 AND queries_used_this_month >= 0)
);

-- Индекс для быстрой фильтрации workspaces по уровню биллинга.
CREATE INDEX idx_workspaces_billing ON workspaces(billing_tier);

-- Индекс для поиска всех workspaces, созданных конкретным пользователем.
CREATE INDEX idx_workspaces_created_by ON workspaces(created_by);

-- Индекс для фильтрации workspaces по статусу подписки (например, найти все просроченные).
CREATE INDEX idx_workspaces_status ON workspaces(subscription_status);

-- Составной индекс для мониторинга использования квот.
-- Применяется только к активным подпискам для оптимизации.
CREATE INDEX idx_workspaces_quota_usage ON workspaces(queries_used_this_month, quota_reset_at) 
    WHERE subscription_status = 'active';