# invoicesテーブル設計書 vs 実際の差分分析

**作成日**: 2025-07-28  
**目的**: 完全設計書と現在のinvoicesテーブルの差分確認

## 📋 設計書期待値（40カラム）

### **🔑 基本キー・識別（6カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 1 | `id` | SERIAL | - | PRIMARY KEY | 主キー |
| 2 | `user_email` | VARCHAR | 255 | NOT NULL | ユーザー識別 |
| 3 | `status` | VARCHAR | 50 | DEFAULT 'uploaded' + CHECK | 処理状況 |
| 4 | `uploaded_at` | TIMESTAMPTZ | - | DEFAULT NOW() | アップロード時刻 |
| 5 | `created_at` | TIMESTAMPTZ | - | DEFAULT timezone('Asia/Tokyo', NOW()) | 作成時刻 |
| 6 | `updated_at` | TIMESTAMPTZ | - | DEFAULT timezone('Asia/Tokyo', NOW()) | 更新時刻 |

### **📁 ファイル・ソース管理（7カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 7 | `source_type` | VARCHAR | 20 | DEFAULT 'local' + CHECK | **NEW** ファイルソース識別 |
| 8 | `file_name` | VARCHAR | 255 | NOT NULL | ファイル名 |
| 9 | `gdrive_file_id` | VARCHAR | 255 | - | Google Drive ID |
| 10 | `file_path` | VARCHAR | 500 | - | ファイルパス |
| 11 | `gmail_message_id` | VARCHAR | 255 | - | **NEW** Gmail Message ID |
| 12 | `attachment_id` | VARCHAR | 255 | - | **NEW** 添付ファイルID |
| 13 | `sender_email` | VARCHAR | 255 | - | **NEW** 送信者メール |

### **📄 請求書基本情報（6カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 14 | `issuer_name` | VARCHAR | 255 | - | 請求書発行者名 |
| 15 | `recipient_name` | VARCHAR | 255 | - | 請求先企業名 |
| 16 | `main_invoice_number` | VARCHAR | 255 | - | メイン請求書番号 |
| 17 | `receipt_number` | VARCHAR | 255 | - | **確認済み** 受領書番号 |
| 18 | `t_number` | VARCHAR | 50 | - | 適格請求書登録番号 |
| 19 | `issue_date` | DATE | - | - | 請求書発行日 |
| 20 | `due_date` | DATE | - | - | 支払期日 |

### **💰 金額・通貨情報（6カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 21 | `currency` | VARCHAR | 10 | DEFAULT 'JPY' | 通貨コード |
| 22 | `total_amount_tax_included` | DECIMAL | 15,2 | - | 税込合計金額 |
| 23 | `total_amount_tax_excluded` | DECIMAL | 15,2 | - | 税抜合計金額 |
| 24 | `exchange_rate` | DECIMAL | 10,4 | - | **NEW** 為替レート |
| 25 | `jpy_amount` | DECIMAL | 15,2 | - | **NEW** 円換算金額 |
| 26 | `card_statement_id` | VARCHAR | 255 | - | **NEW** カード明細ID |

### **🤖 AI処理・検証結果（8カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 27 | `extracted_data` | JSONB | - | - | AI抽出データ |
| 28 | `raw_response` | JSONB | - | - | 生のAI応答 |
| 29 | `key_info` | JSONB | - | - | **確認済み** 動的キー情報 |
| 30 | `is_valid` | BOOLEAN | - | DEFAULT TRUE | 検証結果フラグ |
| 31 | `validation_errors` | TEXT[] | - | - | 検証エラー配列 |
| 32 | `validation_warnings` | TEXT[] | - | - | 検証警告配列 |
| 33 | `completeness_score` | DECIMAL | 5,2 | - | **確認済み** 完全性スコア |
| 34 | `processing_time` | DECIMAL | 8,2 | - | **確認済み** AI処理時間 |

### **✅ 承認ワークフロー（3カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 35 | `approval_status` | VARCHAR | 50 | DEFAULT 'pending' + CHECK | **NEW** 承認状況 |
| 36 | `approved_by` | VARCHAR | 255 | - | **NEW** 承認者 |
| 37 | `approved_at` | TIMESTAMPTZ | - | - | **NEW** 承認日時 |

### **📊 freee連携強化（3カラム）**
| # | カラム名 | データ型 | サイズ | 制約 | 用途 |
|---|----------|----------|-------|------|------|
| 38 | `exported_to_freee` | BOOLEAN | - | DEFAULT FALSE | **NEW** freee書き出し済み |
| 39 | `export_date` | TIMESTAMPTZ | - | - | **NEW** 書き出し日時 |
| 40 | `freee_batch_id` | VARCHAR | 255 | - | **NEW** freeeバッチID |

---

## ❌ 削除予定カラム

| カラム名 | 理由 | アクション |
|----------|------|----------|
| `gemini_model` | 本番では不要（ユーザー指摘） | **削除** |
| `final_accounting_info` | 削除OK（ユーザー指摘） | **削除** |

---

## 🔍 想定される差分

### **新規追加が必要（13カラム）**
- `source_type`, `gmail_message_id`, `attachment_id`, `sender_email`
- `exchange_rate`, `jpy_amount`, `card_statement_id`
- `approval_status`, `approved_by`, `approved_at`
- `exported_to_freee`, `export_date`, `freee_batch_id`

### **削除が必要（2カラム）**
- `gemini_model`, `final_accounting_info`

### **保持（25カラム）**
- 既存の基本カラム群

---

## 📊 実行手順

1. **現状確認**: `sql/check_current_invoices_table.sql` 実行
2. **差分分析**: 実際の結果とこの表を比較
3. **移行計画**: 差分に基づく具体的な修正SQL作成

**次のステップ**: SQLを実行して実際の差分を確認してください。 