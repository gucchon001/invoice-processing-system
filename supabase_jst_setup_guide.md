# Supabase JST時刻対応 設定ガイド

## 🚨 重要な仕様理解

### Supabaseの時刻仕様
- **PostgreSQL**: `timestamp with time zone` は内部的にUTCで保存
- **デフォルト値**: `DEFAULT now()` はUTC時刻で動作
- **推奨**: Supabase公式はUTC維持を推奨

## 🔧 解決方法1: テーブルスキーマ変更（推奨）

### Supabase管理画面での実行手順

1. **Supabase管理画面にログイン**
2. **SQL Editor** を開く
3. **以下のSQLを実行**:

```sql
-- invoicesテーブルのJST対応
ALTER TABLE invoices 
  ALTER COLUMN created_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

ALTER TABLE invoices 
  ALTER COLUMN updated_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

-- invoice_line_itemsテーブルのJST対応  
ALTER TABLE invoice_line_items 
  ALTER COLUMN created_at SET DEFAULT timezone('Asia/Tokyo'::text, now());

ALTER TABLE invoice_line_items 
  ALTER COLUMN updated_at SET DEFAULT timezone('Asia/Tokyo'::text, now());
```

4. **設定確認**:

```sql
-- デフォルト値の確認
SELECT 
  table_name,
  column_name, 
  column_default
FROM information_schema.columns 
WHERE table_name IN ('invoices', 'invoice_line_items')
  AND table_schema = 'public'
  AND column_name IN ('created_at', 'updated_at')
ORDER BY table_name, column_name;
```

### 期待される結果
```
table_name         | column_name | column_default
invoice_line_items | created_at  | timezone('Asia/Tokyo'::text, now())
invoice_line_items | updated_at  | timezone('Asia/Tokyo'::text, now())
invoices          | created_at  | timezone('Asia/Tokyo'::text, now())
invoices          | updated_at  | timezone('Asia/Tokyo'::text, now())
```

## 🔧 解決方法2: アプリケーション側対応（現在実装済み）

### 統一ワークフロー修正済み
- ✅ `get_jst_now()` 関数実装
- ✅ 全 `datetime.now()` をJST対応
- ✅ `created_at`, `updated_at` に明示的JST設定

### データベース保存修正済み
- ✅ `DatabaseManager`: JST時刻で保存
- ✅ 明細保存: JST時刻対応

## 🎯 推奨アプローチ

### 最適解: **方法1 + 方法2の併用**

1. **テーブルスキーマ変更** (方法1) 
   - 新規レコードのデフォルト値がJST
   - データベース全体の一貫性

2. **アプリケーション側保証** (方法2 - 実装済み)
   - 明示的なJST時刻設定
   - ダブル保証

## 🧪 設定確認方法

### 1. 新規テストレコード作成
```python
# アプリケーションでPDFアップロード
# → created_atがJST (+09:00) で保存されるか確認
```

### 2. デフォルト値確認
```sql
-- Supabase SQL Editorで実行
INSERT INTO invoices (file_name) VALUES ('test_jst.pdf');

SELECT id, created_at, updated_at 
FROM invoices 
ORDER BY id DESC 
LIMIT 1;
```

期待結果: `2025-07-23T19:30:00+09:00` (JST)

## 📝 注意事項

### 既存データ
- **既存レコード**: UTC時刻のまま (変更不要)
- **新規レコード**: JST時刻で保存

### 表示制御
- **アプリケーション**: JST時刻で表示 (実装済み)
- **データベース**: JST時刻で保存 (設定後)

## ✅ 完了チェックリスト

- [ ] Supabase管理画面でSQL実行
- [ ] デフォルト値確認クエリ実行
- [ ] 新規PDFテストアップロード
- [ ] JST時刻保存確認 (+09:00)
- [ ] ブラウザ表示確認

## 🎉 設定完了後の効果

- **新規データ**: 自動的にJST時刻保存
- **アプリケーション**: JST時刻表示
- **一貫性**: データベース・UI両方でJST対応
- **運用性**: 日本時間での直感的操作 