-- 🔒 invoicesテーブル RLS再有効化SQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: セキュリティ復旧とポリシー動作確認

-- ============================================================
-- 1. RLS再有効化
-- ============================================================
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 2. 現在のポリシー確認
-- ============================================================
SELECT 
    tablename,
    policyname as "ポリシー名",
    cmd as "コマンド",
    qual as "条件式",
    with_check as "チェック式"
FROM pg_policies 
WHERE tablename = 'invoices'
ORDER BY cmd, policyname;

-- ============================================================
-- 3. RLS有効状況確認
-- ============================================================
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS有効"
FROM pg_tables 
WHERE tablename = 'invoices';

-- ============================================================
-- 4. 認証状態確認（重要）
-- ============================================================
SELECT 
    auth.uid() as "認証済みユーザーID",
    auth.email() as "認証済みメールアドレス",
    auth.role() as "認証済みロール";

-- ============================================================
-- 5. 既存データアクセステスト
-- ============================================================
-- 現在保存されているデータが見えるかテスト
SELECT 
    id,
    user_email,
    file_name,
    status,
    created_at
FROM invoices 
ORDER BY created_at DESC 
LIMIT 3; 