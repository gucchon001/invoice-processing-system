# テーブル構造統一提案書

## 🎯 現状分析

### OCRテストシステム
- **専用テーブル**: `ocr_test_results`
- **詳細フィールド**: 請求書データを完全に保存可能
- **検証機能**: エラー・警告・完全性スコア
- **明細対応**: 専用の `ocr_test_line_items` テーブル

### メインシステム
- **基本テーブル**: `invoices`
- **限定フィールド**: 基本情報のみ（5列）
- **AI抽出データ**: 保存できない状態

## 🚀 統一案：Option A（推奨）

### メインシステムを OCRテストと同じ構造に統一

```sql
-- invoicesテーブルを拡張
ALTER TABLE public.invoices ADD COLUMN issuer_name VARCHAR(255);
ALTER TABLE public.invoices ADD COLUMN recipient_name VARCHAR(255);
ALTER TABLE public.invoices ADD COLUMN invoice_number VARCHAR(100);
ALTER TABLE public.invoices ADD COLUMN currency VARCHAR(10);
ALTER TABLE public.invoices ADD COLUMN total_amount_tax_included DECIMAL(15,2);
ALTER TABLE public.invoices ADD COLUMN total_amount_tax_excluded DECIMAL(15,2);
ALTER TABLE public.invoices ADD COLUMN issue_date DATE;
ALTER TABLE public.invoices ADD COLUMN due_date DATE;
ALTER TABLE public.invoices ADD COLUMN key_info JSONB;
ALTER TABLE public.invoices ADD COLUMN raw_response JSONB;
ALTER TABLE public.invoices ADD COLUMN validation_errors TEXT[];
ALTER TABLE public.invoices ADD COLUMN validation_warnings TEXT[];
ALTER TABLE public.invoices ADD COLUMN completeness_score DECIMAL(5,2);

-- 明細テーブル作成
CREATE TABLE public.invoice_line_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES public.invoices(id),
    line_number INTEGER,
    item_description TEXT,
    quantity DECIMAL(10,2),
    unit_price DECIMAL(15,2),
    amount DECIMAL(15,2),
    tax_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### メリット
- ✅ **完全なデータ保存**: AI抽出結果を完全保存
- ✅ **ブラウザ表示**: 正しい情報を表示可能
- ✅ **検証機能**: エラー・警告情報も保存
- ✅ **明細対応**: 詳細な明細情報も管理
- ✅ **統一性**: OCRテストと同じ高品質な構造

## 🔄 統一案：Option B（軽量版）

### extracted_data カラムのみ追加

```sql
-- 最小限の変更
ALTER TABLE public.invoices ADD COLUMN extracted_data JSONB;
```

### メリット・デメリット
- ✅ **最小変更**: 既存システムへの影響最小
- ✅ **柔軟性**: JSON で任意のデータ構造を保存
- ❌ **検索性**: 個別フィールドでの検索が困難
- ❌ **パフォーマンス**: JSON 内データの集計が重い

## 📊 推奨：Option A

**理由**:
1. OCRテストで **実証済みの優秀な構造**
2. ブラウザ表示の **完全対応**
3. **検索・分析・集計** が容易
4. **拡張性** が高い

## 🚀 実装手順

1. **バックアップ作成**
2. **テーブル拡張SQL実行**
3. **データ保存ロジック更新**
4. **ブラウザ表示確認**
5. **既存データの移行**（必要に応じて） 