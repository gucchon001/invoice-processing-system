-- invoicesテーブルとinvoice_line_itemsテーブルのタイムゾーンをJSTに変更

-- 1. invoicesテーブルの時刻カラムをJSTデフォルトに変更
ALTER TABLE invoices 
  ALTER COLUMN created_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

ALTER TABLE invoices 
  ALTER COLUMN updated_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

-- 2. invoice_line_itemsテーブルの時刻カラムをJSTデフォルトに変更
ALTER TABLE invoice_line_items 
  ALTER COLUMN created_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

ALTER TABLE invoice_line_items 
  ALTER COLUMN updated_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

-- 3. 確認クエリ：デフォルト値の確認
SELECT 
  table_name,
  column_name, 
  column_default,
  data_type
FROM information_schema.columns 
WHERE table_name IN ('invoices', 'invoice_line_items')
  AND table_schema = 'public'
  AND column_name IN ('created_at', 'updated_at')
ORDER BY table_name, column_name;

-- 4. タイムゾーン確認クエリ
SELECT name, abbrev, utc_offset, is_dst
FROM pg_timezone_names() 
WHERE name = 'Asia/Tokyo'; 