# 🏗️ システムアーキテクチャUML図

**作成日**: 2025年1月24日  
**最終更新**: 2025年7月28日  
**バージョン**: 2.0  
**対象システム**: 請求書処理自動化システム

**v2.0更新内容**: 40カラム新機能アーキテクチャ完全対応・Gmail連携・外貨換算・承認ワークフロー・freee連携コンポーネント追加  
**v1.2更新内容**: 統一スキーマ完全再構築対応・日付統一  
**v1.1更新内容**: 関連ドキュメントリンクを統一フォーマット化（3カテゴリ分類）

## 📊 概要

本ドキュメントは請求書処理自動化システムのシステムアーキテクチャをUML図で可視化し、各コンポーネントの関係性と責任範囲を明確に示します。

**🎉 2025年7月28日更新**: **40カラム新機能アーキテクチャ完全対応**により、Gmail連携・外貨換算・承認ワークフロー・freee連携の新機能コンポーネントが追加され、マルチソース処理・多通貨対応・承認制御・会計連携を統合したエンタープライズレベルのUMLアーキテクチャ図が完成しました。

## 🏗️ 全体システムアーキテクチャ図

### レイヤードアーキテクチャ構成（v2.0 40カラム新機能対応）

```mermaid
graph TB
    subgraph "🌐 外部システム層（v2.0拡張）"
        USER[ユーザー]
        GOOGLE[Google Services]
        GMAIL[Gmail API]
        EXCHANGE[Exchange Rate API]
        FREEE[freee API]
        SLACK[Slack/Teams/Email API]
        INTERNET[インターネット]
    end
    
    subgraph "📱 プレゼンテーション層（40カラム対応）"
        UI[Streamlit UI]
        AUTH[Google OAuth Handler]
        PAGES[ページコンポーネント]
        SESSION[セッション管理]
        GMAIL_UI[Gmail連携UI ★v2.0 NEW★]
        CURRENCY_UI[外貨換算UI ★v2.0 NEW★]
        APPROVAL_UI[承認ワークフローUI ★v2.0 NEW★]
        FREEE_UI[freee連携UI ★v2.0 NEW★]
    end
    
    subgraph "🧠 ビジネスロジック層（40カラム新機能統合）"
        UWE[統一ワークフローエンジン<br/>UnifiedWorkflowEngine]
        SERVICES[サービス層]
        MODELS[データモデル層]
        VALIDATION[検証・バリデーション]
        GMAIL_SVC[Gmail統合サービス ★v2.0 NEW★]
        CURRENCY_SVC[通貨換算サービス ★v2.0 NEW★]
        APPROVAL_SVC[承認制御サービス ★v2.0 NEW★]
        FREEE_SVC[freee連携サービス ★v2.0 NEW★]
    end
    
    subgraph "🔧 インフラストラクチャ層（40カラム完全対応）"
        DATABASE[データベース<br/>Supabase PostgreSQL<br/>40カラム対応]
        AI[AI処理<br/>Gemini API<br/>新機能プロンプト5種]
        STORAGE[ファイルストレージ<br/>Google Drive API]
        AGGRID[UI拡張<br/>ag-Grid<br/>新機能タブ対応]
        GMAIL_MGR[Gmail API連携 ★v2.0 NEW★]
        EXCHANGE_MGR[為替レートAPI連携 ★v2.0 NEW★]
        FREEE_MGR[freee API連携 ★v2.0 NEW★]
        NOTIFICATION[通知API連携 ★v2.0 NEW★]
    end
    
    %% 外部からの接続（v2.0拡張）
    USER --> UI
    GOOGLE --> AUTH
    GMAIL --> GMAIL_MGR
    EXCHANGE --> EXCHANGE_MGR
    FREEE --> FREEE_MGR
    SLACK --> NOTIFICATION
    INTERNET --> AI
    INTERNET --> DATABASE
    
    %% プレゼンテーション層内の関係（v2.0拡張）
    UI --> AUTH
    UI --> PAGES
    UI --> SESSION
    UI --> GMAIL_UI
    UI --> CURRENCY_UI
    UI --> APPROVAL_UI
    UI --> FREEE_UI
    
    %% ビジネスロジック層への接続（40カラム対応）
    PAGES --> UWE
    GMAIL_UI --> GMAIL_SVC
    CURRENCY_UI --> CURRENCY_SVC
    APPROVAL_UI --> APPROVAL_SVC
    FREEE_UI --> FREEE_SVC
    UWE --> SERVICES
    UWE --> MODELS
    UWE --> VALIDATION
    UWE --> GMAIL_SVC
    UWE --> CURRENCY_SVC
    UWE --> APPROVAL_SVC
    UWE --> FREEE_SVC
    
    %% インフラストラクチャ層への接続（40カラム完全対応）
    UWE --> DATABASE
    UWE --> AI
    UWE --> STORAGE
    UI --> AGGRID
    GMAIL_SVC --> GMAIL_MGR
    CURRENCY_SVC --> EXCHANGE_MGR
    APPROVAL_SVC --> NOTIFICATION
    FREEE_SVC --> FREEE_MGR
    
    %% データフロー（40カラム対応）
    STORAGE --> AI
    GMAIL_MGR --> AI
    AI --> DATABASE
    DATABASE --> AGGRID
    EXCHANGE_MGR --> DATABASE
    FREEE_MGR --> DATABASE
    
    %% スタイリング（v2.0強化）
    style UWE fill:#90EE90,stroke:#333,stroke-width:3px
    style UI fill:#87CEEB,stroke:#333,stroke-width:2px
    style DATABASE fill:#FFB6C1,stroke:#333,stroke-width:2px
    style AI fill:#DDA0DD,stroke:#333,stroke-width:2px
    style STORAGE fill:#F0E68C,stroke:#333,stroke-width:2px
    style GMAIL_UI fill:#FF6B6B,stroke:#333,stroke-width:2px
    style CURRENCY_UI fill:#4ECDC4,stroke:#333,stroke-width:2px
    style APPROVAL_UI fill:#45B7D1,stroke:#333,stroke-width:2px
    style FREEE_UI fill:#96CEB4,stroke:#333,stroke-width:2px
```

## 📦 コンポーネント構成図

### プレゼンテーション層の詳細構成（v2.0 40カラム新機能対応）

```mermaid
graph TD
    subgraph "📱 Streamlit アプリケーション（40カラム対応）"
        MAIN[app.py<br/>メインアプリ<br/>v2.0拡張]
        SIDEBAR[components/sidebar.py<br/>サイドバー<br/>新機能メニュー追加]
    end
    
    subgraph "📄 ページコンポーネント（v2.0拡張）"
        INVOICE[pages/invoice_processing.py<br/>請求書処理<br/>40カラム対応]
        TEST[pages/test_pages.py<br/>テストページ<br/>レプリケーション対応]
        SETTINGS[pages/settings.py<br/>設定・ダッシュボード<br/>新機能設定追加]
        GMAIL_PAGE[pages/gmail_integration.py<br/>Gmail連携ページ ★v2.0 NEW★]
        CURRENCY_PAGE[pages/currency_conversion.py<br/>外貨換算ページ ★v2.0 NEW★]
        APPROVAL_PAGE[pages/approval_workflow.py<br/>承認ワークフローページ ★v2.0 NEW★]
        FREEE_PAGE[pages/freee_integration.py<br/>freee連携ページ ★v2.0 NEW★]
    end
    
    subgraph "🔐 認証システム（v2.0強化）"
        OAUTH[auth/oauth_handler.py<br/>Google OAuth<br/>Gmail OAuth統合]
        SESSION_MGR[セッション管理<br/>40カラム対応]
        GMAIL_AUTH[auth/gmail_oauth.py<br/>Gmail認証 ★v2.0 NEW★]
        FREEE_AUTH[auth/freee_oauth.py<br/>freee認証 ★v2.0 NEW★]
    end
    
    subgraph "🎨 UI拡張コンポーネント（v2.0 NEW）"
        MULTI_SOURCE[components/multi_source_selector.py<br/>マルチソース選択]
        CURRENCY_DISPLAY[components/currency_display.py<br/>外貨表示]
        APPROVAL_ACTIONS[components/approval_actions.py<br/>承認アクション]
        FREEE_STATUS[components/freee_status.py<br/>freee連携状況]
    end
    
    %% 基本接続
    MAIN --> SIDEBAR
    MAIN --> INVOICE
    MAIN --> TEST
    MAIN --> SETTINGS
    MAIN --> OAUTH
    OAUTH --> SESSION_MGR
    
    %% v2.0新機能接続
    MAIN --> GMAIL_PAGE
    MAIN --> CURRENCY_PAGE
    MAIN --> APPROVAL_PAGE
    MAIN --> FREEE_PAGE
    
    OAUTH --> GMAIL_AUTH
    OAUTH --> FREEE_AUTH
    
    INVOICE --> MULTI_SOURCE
    INVOICE --> CURRENCY_DISPLAY
    INVOICE --> APPROVAL_ACTIONS
    INVOICE --> FREEE_STATUS
    
    %% 認証連携
    GMAIL_PAGE --> GMAIL_AUTH
    FREEE_PAGE --> FREEE_AUTH
    
    %% スタイリング
    style MAIN fill:#87CEEB
    style OAUTH fill:#FFD700
    style GMAIL_PAGE fill:#FF6B6B
    style CURRENCY_PAGE fill:#4ECDC4
    style APPROVAL_PAGE fill:#45B7D1
    style FREEE_PAGE fill:#96CEB4
```

### ビジネスロジック層の詳細構成（v2.0 40カラム新機能対応）

```mermaid
graph TD
    subgraph "🧠 統一ワークフローエンジン（40カラム対応）"
        UWE[UnifiedWorkflowEngine<br/>統一処理エンジン<br/>v2.0拡張]
        PROGRESS[進捗管理システム<br/>新機能対応]
        CALLBACK[コールバック管理<br/>40カラム対応]
    end
    
    subgraph "🔧 コアサービス（v2.0拡張）"
        PROMPT_MGR[UnifiedPromptManager<br/>プロンプト管理<br/>新機能プロンプト5種]
        PROMPT_SEL[PromptSelector<br/>プロンプト選択<br/>40カラム対応]
        VALIDATOR[InvoiceValidator<br/>検証システム<br/>新機能検証]
        DISPLAY[WorkflowDisplayManager<br/>表示管理<br/>新機能UI対応]
    end
    
    subgraph "🎯 新機能サービス（v2.0 NEW）"
        GMAIL_SVC[GmailIntegrationService<br/>Gmail統合サービス]
        CURRENCY_SVC[CurrencyConversionService<br/>通貨換算サービス]
        APPROVAL_SVC[ApprovalControlService<br/>承認制御サービス]
        FREEE_SVC[FreeeIntegrationService<br/>freee連携サービス]
    end
    
    subgraph "📊 データモデル（40カラム対応）"
        WORKFLOW_MODEL[WorkflowModels<br/>ワークフローモデル<br/>基本+新機能]
        RESULT_MODEL[ResultModels<br/>結果モデル<br/>40カラム対応]
        PROGRESS_MODEL[ProgressModels<br/>進捗モデル<br/>新機能進捗]
        GMAIL_MODEL[GmailModels<br/>Gmail連携モデル ★v2.0 NEW★]
        CURRENCY_MODEL[CurrencyModels<br/>外貨換算モデル ★v2.0 NEW★]
        APPROVAL_MODEL[ApprovalModels<br/>承認WFモデル ★v2.0 NEW★]
        FREEE_MODEL[FreeeModels<br/>freee連携モデル ★v2.0 NEW★]
    end
    
    %% 基本接続
    UWE --> PROGRESS
    UWE --> CALLBACK
    UWE --> PROMPT_MGR
    UWE --> PROMPT_SEL
    UWE --> VALIDATOR
    UWE --> DISPLAY
    
    %% v2.0新機能接続
    UWE --> GMAIL_SVC
    UWE --> CURRENCY_SVC
    UWE --> APPROVAL_SVC
    UWE --> FREEE_SVC
    
    %% サービス間連携
    PROMPT_SEL --> PROMPT_MGR
    GMAIL_SVC --> PROMPT_MGR
    CURRENCY_SVC --> PROMPT_MGR
    APPROVAL_SVC --> PROMPT_MGR
    FREEE_SVC --> PROMPT_MGR
    
    %% データモデル接続
    UWE --> WORKFLOW_MODEL
    UWE --> RESULT_MODEL
    PROGRESS --> PROGRESS_MODEL
    GMAIL_SVC --> GMAIL_MODEL
    CURRENCY_SVC --> CURRENCY_MODEL
    APPROVAL_SVC --> APPROVAL_MODEL
    FREEE_SVC --> FREEE_MODEL
    
    %% 新機能間の連携
    GMAIL_SVC --> CURRENCY_SVC
    CURRENCY_SVC --> APPROVAL_SVC
    APPROVAL_SVC --> FREEE_SVC
    
    %% スタイリング
    style UWE fill:#90EE90,stroke:#333,stroke-width:3px
    style GMAIL_SVC fill:#FF6B6B,stroke:#333,stroke-width:2px
    style CURRENCY_SVC fill:#4ECDC4,stroke:#333,stroke-width:2px
    style APPROVAL_SVC fill:#45B7D1,stroke:#333,stroke-width:2px
    style FREEE_SVC fill:#96CEB4,stroke:#333,stroke-width:2px
```

### インフラストラクチャ層の詳細構成（v2.0 40カラム新機能対応）

```mermaid
graph TD
    subgraph "🗄️ データ層（40カラム完全対応）"
        DB_MGR[DatabaseManager<br/>データベース管理<br/>40カラム対応]
        SUPABASE[(Supabase<br/>PostgreSQL<br/>レプリケーション方式)]
    end
    
    subgraph "🤖 AI処理層（新機能プロンプト対応）"
        GEMINI_MGR[GeminiAPIManager<br/>AI処理管理<br/>新機能プロンプト5種]
        GEMINI_API[Google Gemini API<br/>40カラム対応]
        PROMPT_CACHE[プロンプトキャッシュ<br/>新機能プロンプト管理]
    end
    
    subgraph "☁️ ストレージ層（マルチソース対応）"
        DRIVE_MGR[GoogleDriveManager<br/>ファイル管理<br/>統合処理]
        GDRIVE_API[Google Drive API]
        GMAIL_MGR[GmailManager<br/>Gmail API連携 ★v2.0 NEW★]
        GMAIL_API[Gmail API ★v2.0 NEW★]
    end
    
    subgraph "💱 外部API層（v2.0 NEW）"
        EXCHANGE_MGR[ExchangeRateManager<br/>為替レート管理]
        EXCHANGE_API[Exchange Rate API]
        FREEE_MGR[FreeeManager<br/>freee API連携]
        FREEE_API[freee API]
        NOTIFICATION_MGR[NotificationManager<br/>通知API管理]
        NOTIFICATION_API[Slack/Teams/Email API]
    end
    
    subgraph "🎨 UI拡張層（40カラム新機能対応）"
        AGGRID_MGR[AgGridManager<br/>グリッド管理<br/>新機能タブ対応]
        AGGRID_LIB[ag-Grid Library<br/>40カラム表示]
        VALIDATION_UI[ValidationDisplay<br/>検証結果表示<br/>新機能検証対応]
        MULTI_UI[MultiSourceDisplay<br/>マルチソース表示 ★v2.0 NEW★]
        CURRENCY_UI_MGR[CurrencyDisplayManager<br/>外貨表示管理 ★v2.0 NEW★]
        APPROVAL_UI_MGR[ApprovalUIManager<br/>承認UI管理 ★v2.0 NEW★]
        FREEE_UI_MGR[FreeeUIManager<br/>freee UI管理 ★v2.0 NEW★]
    end
    
    %% 基本接続
    DB_MGR --> SUPABASE
    GEMINI_MGR --> GEMINI_API
    GEMINI_MGR --> PROMPT_CACHE
    DRIVE_MGR --> GDRIVE_API
    AGGRID_MGR --> AGGRID_LIB
    
    %% v2.0新機能接続
    GMAIL_MGR --> GMAIL_API
    EXCHANGE_MGR --> EXCHANGE_API
    FREEE_MGR --> FREEE_API
    NOTIFICATION_MGR --> NOTIFICATION_API
    
    %% UI拡張接続
    AGGRID_MGR --> MULTI_UI
    AGGRID_MGR --> CURRENCY_UI_MGR
    AGGRID_MGR --> APPROVAL_UI_MGR
    AGGRID_MGR --> FREEE_UI_MGR
    
    %% データ連携
    GMAIL_MGR --> DB_MGR
    EXCHANGE_MGR --> DB_MGR
    FREEE_MGR --> DB_MGR
    
    %% スタイリング
    style SUPABASE fill:#FFB6C1
    style GEMINI_API fill:#DDA0DD
    style GDRIVE_API fill:#F0E68C
    style AGGRID_LIB fill:#98FB98
    style GMAIL_API fill:#FF6B6B
    style EXCHANGE_API fill:#4ECDC4
    style FREEE_API fill:#96CEB4
    style NOTIFICATION_API fill:#45B7D1
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