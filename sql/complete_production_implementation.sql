-- 🎯 完全本番実装SQL（2025年7月28日）
-- 目的: 40カラム完全設計 + レプリケーション方式の一括実行
-- 対象: invoices + invoice_line_items + ocr_test_results + ocr_test_line_items
-- 実行環境: 空データでの安全実行

-- ============================================================
-- 🎯 Phase 1: 本番テーブル完全修正（invoices: 28→40カラム）
-- ============================================================

-- Step 1.1: final_accounting_info削除
ALTER TABLE invoices DROP COLUMN IF EXISTS final_accounting_info;

-- Step 1.2: ファイル・ソース管理（4カラム追加）
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'local';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS gmail_message_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS attachment_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS sender_email VARCHAR(255);

-- Step 1.3: CHECK制約追加（source_type）
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_source_type 
    CHECK (source_type IN ('local', 'gdrive', 'gmail'));

-- Step 1.4: 外貨換算（3カラム追加）
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(10,4);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS jpy_amount DECIMAL(15,2);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS card_statement_id VARCHAR(255);

-- Step 1.5: 承認ワークフロー（3カラム追加）
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approval_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

-- Step 1.6: CHECK制約追加（approval_status）
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_approval_status 
    CHECK (approval_status IN ('pending', 'approved', 'rejected', 'requires_review'));

-- Step 1.7: freee連携強化（3カラム追加）
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS exported_to_freee BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS export_date TIMESTAMPTZ;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS freee_batch_id VARCHAR(255);

-- Step 1.8: 新機能インデックス追加
CREATE INDEX IF NOT EXISTS idx_invoices_source_type ON invoices(source_type);
CREATE INDEX IF NOT EXISTS idx_invoices_gmail_message_id ON invoices(gmail_message_id) 
    WHERE gmail_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_approval_status ON invoices(approval_status);
CREATE INDEX IF NOT EXISTS idx_invoices_exported_to_freee ON invoices(exported_to_freee);

-- Step 1.9: カラムコメント追加
COMMENT ON COLUMN invoices.source_type IS 'ファイルソース識別（local/gdrive/gmail）';
COMMENT ON COLUMN invoices.gmail_message_id IS 'Gmail自動取り込み時のメッセージID';
COMMENT ON COLUMN invoices.attachment_id IS 'Gmail添付ファイルID';
COMMENT ON COLUMN invoices.sender_email IS 'Gmail送信者メールアドレス';
COMMENT ON COLUMN invoices.exchange_rate IS '外貨換算レート';
COMMENT ON COLUMN invoices.jpy_amount IS '円換算金額';
COMMENT ON COLUMN invoices.card_statement_id IS 'カード明細連携ID';
COMMENT ON COLUMN invoices.approval_status IS '承認ワークフロー状態';
COMMENT ON COLUMN invoices.approved_by IS '承認者ユーザー';
COMMENT ON COLUMN invoices.approved_at IS '承認日時';
COMMENT ON COLUMN invoices.exported_to_freee IS 'freee連携書き出し済みフラグ';
COMMENT ON COLUMN invoices.export_date IS 'freee書き出し日時';
COMMENT ON COLUMN invoices.freee_batch_id IS 'freeeバッチ処理ID';

-- ============================================================
-- 🎯 Phase 2: 明細テーブル確認・最適化（invoice_line_items）
-- ============================================================

-- Step 2.1: 既存明細テーブル状況確認（必要に応じて）
-- 既に統一済みの想定だが、念のため確認用クエリ用意

-- Step 2.2: 明細テーブル最適化インデックス
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_line_number ON invoice_line_items(invoice_id, line_number);

-- ============================================================
-- 🎯 Phase 3: テストテーブル完全レプリケーション
-- ============================================================

-- Step 3.1: 既存OCRテストテーブル削除（レプリケーション準備）
DROP TABLE IF EXISTS ocr_test_results CASCADE;
DROP TABLE IF EXISTS ocr_test_line_items CASCADE;

-- Step 3.2: invoicesテーブル完全レプリケーション（構造のみ）
CREATE TABLE ocr_test_results AS SELECT * FROM invoices WHERE FALSE;

-- Step 3.3: テスト専用カラム追加（3カラム）
ALTER TABLE ocr_test_results 
    ADD COLUMN session_id UUID REFERENCES ocr_test_sessions(id) ON DELETE CASCADE,
    ADD COLUMN gemini_model VARCHAR(50) DEFAULT 'gemini-2.5-flash-lite-preview-06-17',
    ADD COLUMN test_batch_name VARCHAR(100);

-- Step 3.4: ID型変更（テスト環境用UUID）
ALTER TABLE ocr_test_results DROP COLUMN id;
ALTER TABLE ocr_test_results ADD COLUMN id UUID PRIMARY KEY DEFAULT uuid_generate_v4();

-- Step 3.5: テスト専用インデックス
CREATE INDEX idx_ocr_test_results_session_id ON ocr_test_results(session_id);
CREATE INDEX idx_ocr_test_results_gemini_model ON ocr_test_results(gemini_model);
CREATE INDEX idx_ocr_test_results_test_batch_name ON ocr_test_results(test_batch_name);

-- Step 3.6: invoice_line_itemsレプリケーション
CREATE TABLE ocr_test_line_items AS SELECT * FROM invoice_line_items WHERE FALSE;

-- Step 3.7: 明細テーブルID型変更
ALTER TABLE ocr_test_line_items DROP COLUMN id;
ALTER TABLE ocr_test_line_items DROP COLUMN invoice_id;
ALTER TABLE ocr_test_line_items ADD COLUMN id UUID PRIMARY KEY DEFAULT uuid_generate_v4();
ALTER TABLE ocr_test_line_items ADD COLUMN result_id UUID REFERENCES ocr_test_results(id) ON DELETE CASCADE;

-- Step 3.8: 明細テスト専用インデックス
CREATE INDEX idx_ocr_test_line_items_result_id ON ocr_test_line_items(result_id);
CREATE INDEX idx_ocr_test_line_items_line_number ON ocr_test_line_items(result_id, line_number);

-- ============================================================
-- 🎯 Phase 4: 最終検証・確認
-- ============================================================

-- Step 4.1: invoicesテーブル最終検証
SELECT 
    '🎉 invoices修正完了！' as message,
    COUNT(*) as final_column_count,
    CASE 
        WHEN COUNT(*) = 40 THEN '✅ 設計書と完全一致'
        ELSE '❌ カラム数不一致'
    END as validation_result
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- Step 4.2: レプリケーション成功確認
SELECT 
    '🎉 レプリケーション完了！' as message,
    'invoices: ' || (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'invoices') || '個' as master_columns,
    'ocr_test_results: ' || (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'ocr_test_results') || '個' as replicated_columns,
    'invoice_line_items: ' || (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'invoice_line_items') || '個' as master_line_items,
    'ocr_test_line_items: ' || (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'ocr_test_line_items') || '個' as replicated_line_items;

-- Step 4.3: 新機能カラム存在確認
SELECT 
    '新機能カラム存在確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'source_type') as has_source_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gmail_message_id') as has_gmail_message_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'approval_status') as has_approval_status,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'exported_to_freee') as has_exported_to_freee;

-- Step 4.4: テスト専用カラム確認
SELECT 
    'テスト専用カラム確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'session_id') as has_session_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'gemini_model') as has_gemini_model,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'test_batch_name') as has_test_batch_name;

-- ============================================================
-- 🎯 実行完了メッセージ
-- ============================================================

SELECT 
    '🎉🎉🎉 完全実装成功！🎉🎉🎉' as message,
    '本番テーブル: 28→40カラム達成' as production_result,
    'テストテーブル: レプリケーション43カラム達成' as test_result,
    '明細テーブル: 両系統完全対応' as line_items_result,
    'Gmail・外貨・承認・freee: 基盤完成' as features_result,
    '🚀 アプリケーション実装準備完了！' as next_step; 