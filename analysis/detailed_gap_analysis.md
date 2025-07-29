# invoicesテーブル詳細差分分析レポート

**作成日**: 2025-07-28  
**データソース**: 実際のinvoicesテーブルチェック結果  
**目的**: 完全設計書との正確な差分特定

## 📊 分析結果サマリー

| 分析項目 | 結果 |
|----------|------|
| **現在のカラム数** | **28個** |
| **設計書目標** | **40個** |
| **不足カラム** | **13個** |
| **削除対象** | **1個** |
| **最終カラム数** | **40個** ✅ |

---

## ✅ 既存カラム（28個）- 現状維持

### **🔑 基本キー・識別（6個）** ✅
| # | カラム名 | データ型 | サイズ | 現状 |
|---|----------|----------|-------|------|
| 1 | `id` | integer | 32,0 | ✅ **正常** |
| 2 | `user_email` | character varying | 255 | ✅ **正常** |
| 3 | `status` | character varying | 50 | ✅ **正常** |
| 4 | `uploaded_at` | timestamp with time zone | - | ✅ **正常** |
| 5 | `created_at` | timestamp with time zone | - | ✅ **正常** |
| 6 | `updated_at` | timestamp with time zone | - | ✅ **正常** |

### **📁 ファイル管理（3個）** ✅
| # | カラム名 | データ型 | サイズ | 現状 |
|---|----------|----------|-------|------|
| 7 | `file_name` | character varying | 255 | ✅ **正常** |
| 8 | `gdrive_file_id` | character varying | 255 | ✅ **正常** |
| 9 | `file_path` | character varying | 500 | ✅ **正常** |

### **📄 請求書基本情報（7個）** ✅
| # | カラム名 | データ型 | サイズ | 現状 |
|---|----------|----------|-------|------|
| 10 | `issuer_name` | character varying | 255 | ✅ **正常** |
| 11 | `recipient_name` | character varying | 255 | ✅ **正常** |
| 12 | `main_invoice_number` | character varying | 255 | ✅ **正常** |
| 13 | `receipt_number` | character varying | 255 | ✅ **正常** |
| 14 | `t_number` | character varying | 50 | ✅ **正常** |
| 15 | `issue_date` | date | - | ✅ **正常** |
| 16 | `due_date` | date | - | ✅ **正常** |

### **💰 金額・通貨情報（3個）** ✅
| # | カラム名 | データ型 | サイズ | 現状 |
|---|----------|----------|-------|------|
| 17 | `currency` | character varying | 10 | ✅ **正常** |
| 18 | `total_amount_tax_included` | numeric | 15,2 | ✅ **正常** |
| 19 | `total_amount_tax_excluded` | numeric | 15,2 | ✅ **正常** |

### **🤖 AI処理・検証結果（8個）** ✅
| # | カラム名 | データ型 | サイズ | 現状 |
|---|----------|----------|-------|------|
| 20 | `extracted_data` | jsonb | - | ✅ **正常** |
| 21 | `raw_response` | jsonb | - | ✅ **正常** |
| 22 | `key_info` | jsonb | - | ✅ **正常** |
| 23 | `is_valid` | boolean | - | ✅ **正常** |
| 24 | `validation_errors` | ARRAY | - | ✅ **正常** |
| 25 | `validation_warnings` | ARRAY | - | ✅ **正常** |
| 26 | `completeness_score` | numeric | 5,2 | ✅ **正常** |
| 27 | `processing_time` | numeric | 8,2 | ✅ **正常** |

### **❌ 削除対象（1個）**
| # | カラム名 | データ型 | 理由 | アクション |
|---|----------|----------|------|----------|
| 28 | `final_accounting_info` | jsonb | ユーザー指摘：削除OK | **削除** |

---

## ❌ 不足カラム（13個）- 追加必要

### **📁 ファイル・ソース管理（4個）** ❌
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 29 | `source_type` | VARCHAR | 20 | DEFAULT 'local' + CHECK | **Gmail連携必須** |
| 30 | `gmail_message_id` | VARCHAR | 255 | - | **Gmail Message ID** |
| 31 | `attachment_id` | VARCHAR | 255 | - | **添付ファイル ID** |
| 32 | `sender_email` | VARCHAR | 255 | - | **送信者メール** |

### **💱 外貨換算（3個）** ❌
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 33 | `exchange_rate` | DECIMAL | 10,4 | - | **為替レート** |
| 34 | `jpy_amount` | DECIMAL | 15,2 | - | **円換算金額** |
| 35 | `card_statement_id` | VARCHAR | 255 | - | **カード明細ID** |

### **✅ 承認ワークフロー（3個）** ❌
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 36 | `approval_status` | VARCHAR | 50 | DEFAULT 'pending' + CHECK | **承認状況** |
| 37 | `approved_by` | VARCHAR | 255 | - | **承認者** |
| 38 | `approved_at` | TIMESTAMPTZ | - | - | **承認日時** |

### **📊 freee連携強化（3個）** ❌
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 39 | `exported_to_freee` | BOOLEAN | - | DEFAULT FALSE | **freee書き出し済み** |
| 40 | `export_date` | TIMESTAMPTZ | - | - | **書き出し日時** |
| 41 | `freee_batch_id` | VARCHAR | 255 | - | **freeeバッチID** |

---

## 🔧 データ型検証結果

### **✅ 検証済み重要カラム**
| カラム名 | 期待値 | 実際値 | 状況 |
|----------|--------|--------|------|
| `key_info` | JSONB | jsonb | ✅ **完全一致** |

---

## 📊 インデックス状況

### **✅ 既存インデックス（15個）**
- ✅ `invoices_pkey` (PRIMARY KEY)
- ✅ `idx_invoices_key_info_gin` (key_info GIN)
- ✅ `idx_invoices_extracted_data_gin` (extracted_data GIN)
- ✅ `idx_invoices_user_email` (user_email)
- ✅ `idx_invoices_status` (status)
- ✅ その他10個のインデックス

### **❌ 不足インデックス（新機能用）**
- `idx_invoices_source_type`
- `idx_invoices_gmail_message_id`
- `idx_invoices_approval_status`
- `idx_invoices_exported_to_freee`

---

## 🚀 修正アクション計画

### **Phase 1: 削除（1個）**
```sql
ALTER TABLE invoices DROP COLUMN final_accounting_info;
```

### **Phase 2: 追加（13個）**
```sql
-- ファイル・ソース管理
ALTER TABLE invoices ADD COLUMN source_type VARCHAR(20) DEFAULT 'local';
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_source_type 
    CHECK (source_type IN ('local', 'gdrive', 'gmail'));

-- Gmail連携
ALTER TABLE invoices ADD COLUMN gmail_message_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN attachment_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN sender_email VARCHAR(255);

-- 外貨換算
ALTER TABLE invoices ADD COLUMN exchange_rate DECIMAL(10,4);
ALTER TABLE invoices ADD COLUMN jpy_amount DECIMAL(15,2);
ALTER TABLE invoices ADD COLUMN card_statement_id VARCHAR(255);

-- 承認ワークフロー
ALTER TABLE invoices ADD COLUMN approval_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_approval_status 
    CHECK (approval_status IN ('pending', 'approved', 'rejected', 'requires_review'));
ALTER TABLE invoices ADD COLUMN approved_by VARCHAR(255);
ALTER TABLE invoices ADD COLUMN approved_at TIMESTAMPTZ;

-- freee連携
ALTER TABLE invoices ADD COLUMN exported_to_freee BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN export_date TIMESTAMPTZ;
ALTER TABLE invoices ADD COLUMN freee_batch_id VARCHAR(255);
```

### **Phase 3: インデックス追加**
```sql
CREATE INDEX idx_invoices_source_type ON invoices(source_type);
CREATE INDEX idx_invoices_gmail_message_id ON invoices(gmail_message_id) 
    WHERE gmail_message_id IS NOT NULL;
CREATE INDEX idx_invoices_approval_status ON invoices(approval_status);
CREATE INDEX idx_invoices_exported_to_freee ON invoices(exported_to_freee);
```

---

## ✅ 検証項目

修正後の検証ポイント：
1. **カラム数**: 28 - 1 + 13 = 40個
2. **インデックス数**: 15 + 4 = 19個
3. **制約確認**: CHECK制約の動作確認
4. **アプリケーション**: gemini_modelエラー解決確認

---

**次のステップ**: 段階的修正SQLの実行準備完了 