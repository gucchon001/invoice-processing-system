-- 🚨 緊急回避策: invoicesテーブル RLS一時無効化
-- ⚠️  注意: セキュリティリスクがあるため、テスト確認後は必ずRLSを再有効化してください
-- 実行環境: Supabase Web UI SQL Editor

-- ============================================================
-- 1. RLS一時無効化
-- ============================================================
ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;

-- 確認用クエリ
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS有効（false=無効）"
FROM pg_tables 
WHERE tablename = 'invoices';

-- ============================================================
-- ⚠️  テスト完了後、以下を必ず実行してRLSを再有効化してください
-- ============================================================
-- ALTER TABLE invoices ENABLE ROW LEVEL SECURITY; 