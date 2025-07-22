-- invoicesテーブルにextracted_dataカラムを追加
-- AI抽出データをJSONB形式で保存するため

ALTER TABLE public.invoices 
ADD COLUMN IF NOT EXISTS extracted_data JSONB;

-- カラムにコメントを追加
COMMENT ON COLUMN public.invoices.extracted_data IS 'AI抽出された請求書データ（JSON形式）';

-- インデックス作成（JSON検索高速化のため）
CREATE INDEX IF NOT EXISTS idx_invoices_extracted_data_gin 
ON public.invoices USING GIN (extracted_data);

-- 既存データの確認
SELECT id, file_name, status, 
       CASE 
           WHEN extracted_data IS NULL THEN 'NULL'
           ELSE 'HAS_DATA'
       END as extracted_data_status
FROM public.invoices 
ORDER BY id DESC 
LIMIT 5; 