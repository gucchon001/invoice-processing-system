# 🏗️ システムアーキテクチャUML図

**作成日**: 2025年1月24日  
**バージョン**: 1.1  
**対象システム**: 請求書処理自動化システム

**v1.1更新内容**: 関連ドキュメントリンクを統一フォーマット化（3カテゴリ分類）

## 📊 概要

本ドキュメントは請求書処理自動化システムのシステムアーキテクチャをUML図で可視化し、各コンポーネントの関係性と責任範囲を明確に示します。

## 🏗️ 全体システムアーキテクチャ図

### レイヤードアーキテクチャ構成

```mermaid
graph TB
    subgraph "🌐 外部システム層"
        USER[ユーザー]
        GOOGLE[Google Services]
        INTERNET[インターネット]
    end
    
    subgraph "📱 プレゼンテーション層"
        UI[Streamlit UI]
        AUTH[Google OAuth Handler]
        PAGES[ページコンポーネント]
        SESSION[セッション管理]
    end
    
    subgraph "🧠 ビジネスロジック層"
        UWE[統一ワークフローエンジン<br/>UnifiedWorkflowEngine]
        SERVICES[サービス層]
        MODELS[データモデル層]
        VALIDATION[検証・バリデーション]
    end
    
    subgraph "🔧 インフラストラクチャ層"
        DATABASE[データベース<br/>Supabase PostgreSQL]
        AI[AI処理<br/>Gemini API]
        STORAGE[ファイルストレージ<br/>Google Drive API]
        AGGRID[UI拡張<br/>ag-Grid]
    end
    
    %% 外部からの接続
    USER --> UI
    GOOGLE --> AUTH
    INTERNET --> AI
    INTERNET --> DATABASE
    
    %% プレゼンテーション層内の関係
    UI --> AUTH
    UI --> PAGES
    UI --> SESSION
    
    %% ビジネスロジック層への接続
    PAGES --> UWE
    UWE --> SERVICES
    UWE --> MODELS
    UWE --> VALIDATION
    
    %% インフラストラクチャ層への接続
    UWE --> DATABASE
    UWE --> AI
    UWE --> STORAGE
    UI --> AGGRID
    
    %% データフロー
    STORAGE --> AI
    AI --> DATABASE
    DATABASE --> AGGRID
    
    %% スタイリング
    style UWE fill:#90EE90,stroke:#333,stroke-width:3px
    style UI fill:#87CEEB,stroke:#333,stroke-width:2px
    style DATABASE fill:#FFB6C1,stroke:#333,stroke-width:2px
    style AI fill:#DDA0DD,stroke:#333,stroke-width:2px
    style STORAGE fill:#F0E68C,stroke:#333,stroke-width:2px
```

## 📦 コンポーネント構成図

### プレゼンテーション層の詳細構成

```mermaid
graph TD
    subgraph "📱 Streamlit アプリケーション"
        MAIN[app.py<br/>メインアプリ]
        SIDEBAR[components/sidebar.py<br/>サイドバー]
    end
    
    subgraph "📄 ページコンポーネント"
        INVOICE[pages/invoice_processing.py<br/>請求書処理]
        TEST[pages/test_pages.py<br/>テストページ]
        SETTINGS[pages/settings.py<br/>設定・ダッシュボード]
    end
    
    subgraph "🔐 認証システム"
        OAUTH[auth/oauth_handler.py<br/>Google OAuth]
        SESSION_MGR[セッション管理]
    end
    
    MAIN --> SIDEBAR
    MAIN --> INVOICE
    MAIN --> TEST
    MAIN --> SETTINGS
    MAIN --> OAUTH
    OAUTH --> SESSION_MGR
    
    style MAIN fill:#87CEEB
    style OAUTH fill:#FFD700
```

### ビジネスロジック層の詳細構成

```mermaid
graph TD
    subgraph "🧠 統一ワークフローエンジン"
        UWE[UnifiedWorkflowEngine<br/>統一処理エンジン]
        PROGRESS[進捗管理システム]
        CALLBACK[コールバック管理]
    end
    
    subgraph "🔧 コアサービス"
        PROMPT_MGR[UnifiedPromptManager<br/>プロンプト管理]
        PROMPT_SEL[PromptSelector<br/>プロンプト選択]
        VALIDATOR[InvoiceValidator<br/>検証システム]
        DISPLAY[WorkflowDisplayManager<br/>表示管理]
    end
    
    subgraph "📊 データモデル"
        WORKFLOW_MODEL[WorkflowModels<br/>ワークフローモデル]
        RESULT_MODEL[ResultModels<br/>結果モデル]
        PROGRESS_MODEL[ProgressModels<br/>進捗モデル]
    end
    
    UWE --> PROGRESS
    UWE --> CALLBACK
    UWE --> PROMPT_MGR
    UWE --> PROMPT_SEL
    UWE --> VALIDATOR
    UWE --> DISPLAY
    
    PROMPT_SEL --> PROMPT_MGR
    UWE --> WORKFLOW_MODEL
    UWE --> RESULT_MODEL
    PROGRESS --> PROGRESS_MODEL
    
    style UWE fill:#90EE90,stroke:#333,stroke-width:3px
```

### インフラストラクチャ層の詳細構成

```mermaid
graph TD
    subgraph "🗄️ データ層"
        DB_MGR[DatabaseManager<br/>データベース管理]
        SUPABASE[(Supabase<br/>PostgreSQL)]
    end
    
    subgraph "🤖 AI処理層"
        GEMINI_MGR[GeminiAPIManager<br/>AI処理管理]
        GEMINI_API[Google Gemini API]
    end
    
    subgraph "☁️ ストレージ層"
        DRIVE_MGR[GoogleDriveManager<br/>ファイル管理]
        GDRIVE_API[Google Drive API]
    end
    
    subgraph "🎨 UI拡張層"
        AGGRID_MGR[AgGridManager<br/>グリッド管理]
        AGGRID_LIB[ag-Grid Library]
        VALIDATION_UI[ValidationDisplay<br/>検証結果表示]
    end
    
    DB_MGR --> SUPABASE
    GEMINI_MGR --> GEMINI_API
    DRIVE_MGR --> GDRIVE_API
    AGGRID_MGR --> AGGRID_LIB
    
    style SUPABASE fill:#FFB6C1
    style GEMINI_API fill:#DDA0DD
    style GDRIVE_API fill:#F0E68C
    style AGGRID_LIB fill:#98FB98
```

## 🔄 データフロー図

### 主要データフローパターン

```mermaid
flowchart TD
    INPUT[PDFファイル入力] --> UPLOAD[ファイルアップロード]
    UPLOAD --> STORE[Google Drive保存]
    STORE --> EXTRACT[AI情報抽出]
    EXTRACT --> VALIDATE[データ検証]
    VALIDATE --> SAVE[データベース保存]
    SAVE --> DISPLAY[結果表示]
    
    subgraph "📊 データ変換"
        PDF[PDF Binary]
        JSON[JSON Data]
        VALIDATED[Validated Data]
        RECORD[Database Record]
    end
    
    UPLOAD --> PDF
    EXTRACT --> JSON
    VALIDATE --> VALIDATED
    SAVE --> RECORD
    
    style INPUT fill:#E6E6FA
    style DISPLAY fill:#E6E6FA
    style PDF fill:#FFF8DC
    style JSON fill:#F0FFF0
    style VALIDATED fill:#F5FFFA
    style RECORD fill:#FFF0F5
```

## 🛡️ セキュリティアーキテクチャ

### セキュリティ層とアクセス制御

```mermaid
graph TD
    subgraph "🔐 認証・認可層"
        OAUTH[Google OAuth 2.0]
        JWT[JWT Token管理]
        RLS[Row Level Security]
    end
    
    subgraph "🛡️ データ保護層"
        ENCRYPT[データ暗号化]
        MASK[ログマスキング]
        BACKUP[バックアップ暗号化]
    end
    
    subgraph "🔍 監査・ログ層"
        AUDIT[監査ログ]
        ACCESS_LOG[アクセスログ]
        ERROR_LOG[エラーログ]
    end
    
    OAUTH --> JWT
    JWT --> RLS
    RLS --> ENCRYPT
    ENCRYPT --> MASK
    MASK --> BACKUP
    
    OAUTH --> AUDIT
    JWT --> ACCESS_LOG
    RLS --> ERROR_LOG
    
    style OAUTH fill:#FFD700
    style RLS fill:#FFA07A
    style ENCRYPT fill:#98FB98
```

## 📈 スケーラビリティ設計

### 水平スケーリング対応

```mermaid
graph TD
    subgraph "⚖️ ロードバランサ層"
        LB[ロードバランサ]
    end
    
    subgraph "🔄 アプリケーション層（スケーラブル）"
        APP1[Streamlit Instance 1]
        APP2[Streamlit Instance 2]
        APP3[Streamlit Instance N]
    end
    
    subgraph "💾 データ層（共有）"
        DB_SHARED[(共有データベース)]
        CACHE[(Redisキャッシュ)]
        STORAGE_SHARED[(共有ストレージ)]
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> DB_SHARED
    APP2 --> DB_SHARED
    APP3 --> DB_SHARED
    
    APP1 --> CACHE
    APP2 --> CACHE
    APP3 --> CACHE
    
    APP1 --> STORAGE_SHARED
    APP2 --> STORAGE_SHARED
    APP3 --> STORAGE_SHARED
    
    style LB fill:#FF6347
    style DB_SHARED fill:#4682B4
    style CACHE fill:#FF4500
    style STORAGE_SHARED fill:#32CD32
```

## 🔧 技術スタック構成

### 技術要素とバージョン管理

```mermaid
mindmap
  root((技術スタック))
    Frontend
      Streamlit 1.28+
      ag-Grid Community
      HTML/CSS/JavaScript
    Backend
      Python 3.9+
      FastAPI (将来)
      Pydantic
    AI/ML
      Google Gemini 2.0
      LangChain (将来)
      Prompt Engineering
    Database
      Supabase PostgreSQL
      Row Level Security
      JSONB Support
    Authentication
      Google OAuth 2.0
      JWT Tokens
      Session Management
    Storage
      Google Drive API
      File Management
      Binary Storage
    Monitoring
      Structured Logging
      Error Tracking
      Performance Metrics
```

## 📊 パフォーマンス要件

### レスポンス時間とスループット目標

| コンポーネント | 目標レスポンス時間 | 最大スループット | 備考 |
|---------------|------------------|-----------------|------|
| UI表示 | < 200ms | 100 concurrent users | 初期表示 |
| 単一ファイル処理 | < 10秒 | 10 files/min | PDF→DB完了 |
| バッチ処理(5ファイル) | < 60秒 | 2 batches/min | 並列処理時 |
| ダッシュボード | < 3秒 | 50 requests/min | ag-Grid表示 |
| API応答 | < 500ms | 200 requests/min | データベースクエリ |

## 🚀 今後の発展計画

### アーキテクチャ進化ロードマップ

```mermaid
timeline
    title システムアーキテクチャ進化計画
    
    Phase 1 : 現在のモノリス
             : Streamlit統合アプリ
             : 同期処理中心
             : 単一インスタンス
    
    Phase 2 : マイクロサービス化
             : API分離
             : 非同期処理導入
             : Redis キャッシュ
    
    Phase 3 : スケーラビリティ強化
             : 水平スケーリング
             : ロードバランサ
             : データベース最適化
    
    Phase 4 : AI/ML強化
             : 複数AIモデル対応
             : MLOps パイプライン
             : リアルタイム処理
```

---

**最終更新**: 2025年1月24日  
**承認者**: システムアーキテクト  
**レビュー予定**: 2025年2月24日

**関連ドキュメント**:

### 📚 統合設計書
- [15_システムアーキテクチャ設計書.md](15_システムアーキテクチャ設計書.md) - システム全体設計（統合版）
- [16_データベース設計書.md](16_データベース設計書.md) - データベース設計（統合版）

### 🏗️ 詳細設計書（独立版）
- [18_データベースER図.md](18_データベースER図.md) - データベースER図・関係性
- [19_テーブル設計詳細仕様書.md](19_テーブル設計詳細仕様書.md) - テーブル仕様・制約・インデックス
- [20_シーケンス図集.md](20_シーケンス図集.md) - 処理フロー・正常系・異常系
- [21_クラス図.md](21_クラス図.md) - クラス構造・コンポーネント関係

### 📋 ドキュメント管理
- [00_DOCS_INDEX.md](00_DOCS_INDEX.md) - 全ドキュメント一覧・関連性 