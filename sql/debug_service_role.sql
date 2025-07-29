-- 🔍 Service Role Key動作確認デバッグSQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: Service Role Key使用時の権限とRLS状態を確認

-- ============================================================
-- 1. 現在の接続ロール確認
-- ============================================================
SELECT 
    current_user as "現在のユーザー",
    current_role as "現在のロール",
    session_user as "セッションユーザー";

-- ============================================================
-- 2. RLS状態確認
-- ============================================================
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS有効"
FROM pg_tables 
WHERE tablename = 'invoices';

-- ============================================================
-- 3. Service Role権限でのテスト挿入
-- ============================================================
-- Service Role Keyなら認証不要で挿入可能
INSERT INTO invoices (
    user_email, 
    status, 
    file_name, 
    created_at, 
    updated_at, 
    uploaded_at
) VALUES (
    'service-role-test@example.com',
    'test',
    'service-role-test.pdf',
    NOW(),
    NOW(),
    NOW()
);

-- ============================================================
-- 4. テストデータ確認
-- ============================================================
SELECT 
    id,
    user_email,
    file_name,
    status,
    created_at
FROM invoices 
WHERE file_name = 'service-role-test.pdf';

-- ============================================================
-- 5. テストデータ削除
-- ============================================================
DELETE FROM invoices 
WHERE file_name = 'service-role-test.pdf'; 