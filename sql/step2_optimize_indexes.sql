-- ================================================================
-- Step 2: インデックス最適化（RAISE NOTICEなし）
-- ================================================================

-- 複合インデックス作成：ユーザー・ステータス・作成日時
CREATE INDEX IF NOT EXISTS idx_invoices_user_status_created 
ON invoices(user_email, status, created_at);

-- 複合インデックス作成：セッション・有効性・スコア
CREATE INDEX IF NOT EXISTS idx_ocr_results_session_valid_score 
ON ocr_test_results(session_id, is_valid, completeness_score);

-- 既存インデックス確認クエリ（必要に応じて実行）
-- SELECT indexname, tablename, indexdef 
-- FROM pg_indexes 
-- WHERE tablename IN ('invoices', 'ocr_test_results', 'ocr_test_sessions')
-- ORDER BY tablename, indexname; 