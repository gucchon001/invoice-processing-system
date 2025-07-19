-- 請求書処理自動化システム - Supabase テーブル作成スクリプト
-- 仕様書v2.7に基づくテーブル定義

-- 1. ユーザーテーブル
CREATE TABLE IF NOT EXISTS public.users (
    email VARCHAR(255) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin'))
);

-- 2. 請求書データテーブル
CREATE TABLE IF NOT EXISTS public.invoices (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email),
    status VARCHAR(50) DEFAULT 'uploaded',
    file_name VARCHAR(255) NOT NULL,
    gdrive_file_id VARCHAR(255),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    issuer VARCHAR(255),
    payer VARCHAR(255),
    main_invoice_number VARCHAR(255),
    receipt_number VARCHAR(255),
    t_number VARCHAR(50),
    issue_date DATE,
    due_date DATE,
    currency VARCHAR(10) DEFAULT 'JPY',
    amount_inclusive_tax DECIMAL(12, 2),
    amount_exclusive_tax DECIMAL(12, 2),
    key_info JSONB,
    line_items JSONB,
    final_accounting_info JSONB
);

-- 3. 支払マスタテーブル
CREATE TABLE IF NOT EXISTS public.payment_masters (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    content VARCHAR(255),
    additional_condition VARCHAR(255),
    processing_rules JSONB,
    account_title VARCHAR(100),
    item VARCHAR(100),
    payment_method VARCHAR(50),
    department VARCHAR(100),
    approval_status VARCHAR(20) DEFAULT 'pending' CHECK (approval_status IN ('approved', 'pending')),
    created_by VARCHAR(255) NOT NULL REFERENCES users(email)
);

-- 4. カード明細データテーブル
CREATE TABLE IF NOT EXISTS public.card_statements (
    id SERIAL PRIMARY KEY,
    transaction_date DATE,
    merchant_name VARCHAR(255),
    jpy_amount DECIMAL(12, 2),
    foreign_currency_amount DECIMAL(12, 2),
    foreign_currency_code VARCHAR(10),
    exchange_rate DECIMAL(10, 4)
);

-- 5. ユーザー設定テーブル
CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_email VARCHAR(255) PRIMARY KEY REFERENCES users(email),
    notify_on_success BOOLEAN DEFAULT true,
    notify_on_error BOOLEAN DEFAULT true
);

-- 6. 経理ルールテーブル
CREATE TABLE IF NOT EXISTS public.accounting_rules (
    id SERIAL PRIMARY KEY,
    rule_category VARCHAR(100) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    rule_description TEXT,
    rule_conditions JSONB,
    rule_values JSONB,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('error', 'warning', 'info')),
    handbook_url VARCHAR(500),
    slide_number INTEGER,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. ルールチェック実行セッションテーブル
CREATE TABLE IF NOT EXISTS public.rule_check_sessions (
    id SERIAL PRIMARY KEY,
    executed_by VARCHAR(255) NOT NULL REFERENCES users(email),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    total_invoices INTEGER DEFAULT 0,
    compliant_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    violation_count INTEGER DEFAULT 0,
    handbook_version VARCHAR(100)
);

-- 8. ルールチェック結果テーブル
CREATE TABLE IF NOT EXISTS public.rule_check_results (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES rule_check_sessions(id),
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    rule_id INTEGER NOT NULL REFERENCES accounting_rules(id),
    check_result VARCHAR(20) NOT NULL CHECK (check_result IN ('compliant', 'warning', 'violation')),
    current_value TEXT,
    expected_value TEXT,
    violation_reason TEXT,
    suggestion TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_invoices_user_email ON invoices(user_email);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_uploaded_at ON invoices(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_payment_masters_approval_status ON payment_masters(approval_status);
CREATE INDEX IF NOT EXISTS idx_rule_check_results_session_id ON rule_check_results(session_id);

-- 初期データの投入
INSERT INTO public.users (email, name, role) VALUES 
('y-haraguchi@tomonokai-corp.com', '原口陽一郎', 'admin')
ON CONFLICT (email) DO NOTHING;

-- RLSポリシーの設定（Row Level Security）
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_masters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- 基本的なRLSポリシー
CREATE POLICY "Users can view their own data" ON public.users FOR SELECT USING (auth.email() = email);
CREATE POLICY "Users can view their own invoices" ON public.invoices FOR ALL USING (auth.email() = user_email);
CREATE POLICY "Users can view approved masters" ON public.payment_masters FOR SELECT USING (approval_status = 'approved' OR auth.email() = created_by);
CREATE POLICY "Users can manage their own preferences" ON public.user_preferences FOR ALL USING (auth.email() = user_email);

COMMIT; 