-- invoicesテーブル完全拡張SQL
-- OCRテストと同じ詳細構造に統一

-- Step 1: 請求書基本情報カラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS issuer_name VARCHAR(255);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(255);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(100);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS registration_number VARCHAR(50);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'JPY';

-- Step 2: 金額関連カラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS total_amount_tax_included DECIMAL(15,2);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS total_amount_tax_excluded DECIMAL(15,2);

-- Step 3: 日付関連カラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS due_date DATE;

-- Step 4: JSON形式データカラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS key_info JSONB;
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS raw_response JSONB;

-- Step 5: 検証・品質管理カラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT true;
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS validation_errors TEXT[];
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS validation_warnings TEXT[];
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS completeness_score DECIMAL(5,2);

-- Step 6: 処理時間カラムを追加
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS processing_time DECIMAL(8,2);

-- Step 7: 既存カラムの拡張（Google Driveファイル管理用）
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS gdrive_file_id VARCHAR(255);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);

-- Step 8: カラムコメントを追加
COMMENT ON COLUMN public.invoices.issuer_name IS '請求元企業名';
COMMENT ON COLUMN public.invoices.recipient_name IS '請求先企業名';
COMMENT ON COLUMN public.invoices.invoice_number IS '請求書番号';
COMMENT ON COLUMN public.invoices.registration_number IS '登録番号（インボイス番号）';
COMMENT ON COLUMN public.invoices.currency IS '通貨コード';
COMMENT ON COLUMN public.invoices.total_amount_tax_included IS '税込金額';
COMMENT ON COLUMN public.invoices.total_amount_tax_excluded IS '税抜金額';
COMMENT ON COLUMN public.invoices.issue_date IS '発行日';
COMMENT ON COLUMN public.invoices.due_date IS '支払期日';
COMMENT ON COLUMN public.invoices.key_info IS 'キー情報（JSON形式）';
COMMENT ON COLUMN public.invoices.raw_response IS '生のAI応答（JSON形式）';
COMMENT ON COLUMN public.invoices.is_valid IS '検証状況';
COMMENT ON COLUMN public.invoices.validation_errors IS '検証エラー一覧';
COMMENT ON COLUMN public.invoices.validation_warnings IS '検証警告一覧';
COMMENT ON COLUMN public.invoices.completeness_score IS '完全性スコア（0-100）';
COMMENT ON COLUMN public.invoices.processing_time IS '処理時間（秒）';
COMMENT ON COLUMN public.invoices.gdrive_file_id IS 'Google DriveファイルID';
COMMENT ON COLUMN public.invoices.file_path IS 'ファイルパス';

-- Step 9: インデックス作成（検索性能向上）
CREATE INDEX IF NOT EXISTS idx_invoices_issuer_name ON public.invoices(issuer_name);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON public.invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON public.invoices(issue_date);
CREATE INDEX IF NOT EXISTS idx_invoices_total_amount ON public.invoices(total_amount_tax_included);
CREATE INDEX IF NOT EXISTS idx_invoices_currency ON public.invoices(currency);
CREATE INDEX IF NOT EXISTS idx_invoices_is_valid ON public.invoices(is_valid);

-- Step 10: JSON検索用GINインデックス
CREATE INDEX IF NOT EXISTS idx_invoices_key_info_gin ON public.invoices USING GIN (key_info);
CREATE INDEX IF NOT EXISTS idx_invoices_raw_response_gin ON public.invoices USING GIN (raw_response);

-- Step 11: 明細テーブルを作成
CREATE TABLE IF NOT EXISTS public.invoice_line_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES public.invoices(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_description TEXT,
    quantity DECIMAL(10,2),
    unit_price DECIMAL(15,2),
    amount DECIMAL(15,2),
    tax_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Step 12: 明細テーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON public.invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_line_number ON public.invoice_line_items(invoice_id, line_number);

-- Step 13: 明細テーブルのコメント
COMMENT ON TABLE public.invoice_line_items IS '請求書明細テーブル';
COMMENT ON COLUMN public.invoice_line_items.invoice_id IS '請求書ID（外部キー）';
COMMENT ON COLUMN public.invoice_line_items.line_number IS '明細行番号';
COMMENT ON COLUMN public.invoice_line_items.item_description IS '商品・サービス名';
COMMENT ON COLUMN public.invoice_line_items.quantity IS '数量';
COMMENT ON COLUMN public.invoice_line_items.unit_price IS '単価';
COMMENT ON COLUMN public.invoice_line_items.amount IS '金額';
COMMENT ON COLUMN public.invoice_line_items.tax_rate IS '税率（%）';

-- Step 14: 拡張後のテーブル構造確認クエリ
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'invoices' AND table_schema = 'public'
-- ORDER BY ordinal_position;

-- Step 15: 成功確認用サンプルクエリ
-- SELECT COUNT(*) as total_columns 
-- FROM information_schema.columns 
-- WHERE table_name = 'invoices' AND table_schema = 'public';

COMMIT; 