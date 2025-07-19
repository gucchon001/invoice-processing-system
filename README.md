# 請求書処理自動化システム

PythonとStreamlitで構築された請求書処理自動化システムです。

## 🏗️ プロジェクト構造

```
invoice-processing-system/
├── src/                          # メインソースコード
│   ├── app/                      # Streamlitアプリケーション
│   │   ├── main.py              # メインアプリケーション
│   │   └── __init__.py
│   ├── core/                     # ビジネスロジック
│   │   ├── models/              # データモデル
│   │   ├── services/            # ビジネスサービス
│   │   ├── workflows/           # ワークフロー処理
│   │   └── __init__.py
│   ├── infrastructure/          # 外部サービス連携
│   │   ├── ai/                  # AI サービス (Gemini API)
│   │   │   ├── gemini_helper.py
│   │   │   └── __init__.py
│   │   ├── auth/                # 認証 (Google OAuth)
│   │   │   ├── oauth_handler.py
│   │   │   └── __init__.py
│   │   ├── database/            # データベース (Supabase)
│   │   │   ├── database.py
│   │   │   └── __init__.py
│   │   ├── storage/             # ストレージ (Google Drive)
│   │   │   ├── google_drive_helper.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── utils/                   # ユーティリティ
│   │   └── __init__.py
│   └── __init__.py
├── tests/                       # テストコード
├── scripts/                     # 運用・デプロイスクリプト
│   └── run_app.ps1
├── sql/                         # データベーススクリプト
│   └── create_tables.sql
├── docs/                        # ドキュメント
├── config/                      # 設定ファイル
├── .streamlit/                  # Streamlit設定
├── requirements.txt             # Python依存関係
└── app.py                       # エントリーポイント
```

## 🚀 使用方法

### 基本起動
```bash
# PowerShell環境での起動
.\run_app.ps1 --env dev

# または直接Streamlit起動
streamlit run app.py --server.port 8701
```

### 開発環境セットアップ
```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化 (Windows)
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

## 🔧 設定

### 必要な設定ファイル
- `.streamlit/secrets.toml` - 認証情報とAPIキー

設定内容：
- Google OAuth認証情報
- Supabaseデータベース接続情報
- Gemini API キー
- Google Drive APIサービスアカウント情報

## 📋 機能

- **PDF請求書アップロード**
- **AIによる情報抽出** (Gemini API)
- **Google Drive連携** (共有ドライブ対応)
- **Supabaseデータベース管理**
- **Google OAuth認証**

## 🏛️ アーキテクチャ

### レイヤー構造
- **App Layer** (`src/app/`) - UI・UX層
- **Core Layer** (`src/core/`) - ビジネスロジック層
- **Infrastructure Layer** (`src/infrastructure/`) - 外部サービス連携層
- **Utils Layer** (`src/utils/`) - 共通ユーティリティ層

### 設計原則
- **Clean Architecture** - 依存関係の逆転
- **モジュラー設計** - 疎結合・高凝集
- **テスタビリティ** - 単体テスト可能な構造

## 📚 技術スタック

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: Supabase (PostgreSQL)
- **Storage**: Google Drive API
- **AI**: Google Gemini API  
- **Auth**: Google OAuth 2.0
- **Deploy**: Google Cloud Run

## 🔐 セキュリティ

- 機密情報は `.streamlit/secrets.toml` で管理
- `config/` ディレクトリと `*.json` ファイルは Git 除外
- サービスアカウント認証による安全なAPI連携

## 📖 ドキュメント

- `/docs` - 設計書・仕様書
- 各モジュールの docstring - API仕様

## 🧪 テスト

```bash
# テスト実行
pytest tests/

# 統合テスト
streamlit run app.py
# ブラウザで http://localhost:8701 にアクセス
```

## 📞 サポート

技術的な質問や問題が発生した場合は、プロジェクトチームまでご連絡ください。 