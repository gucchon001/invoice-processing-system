# Pythonプロジェクト構造テンプレート

## 📋 概要

Clean Architecture原則に基づく、スケーラブルで保守性の高いPythonプロジェクト構造のテンプレートです。

## 🏗️ 基本ディレクトリ構造

```
project-name/
├── src/                          # メインソースコード
│   ├── app/                      # アプリケーション層 (UI/UX)
│   │   ├── main.py              # エントリーポイント
│   │   ├── pages/               # ページ別コンポーネント
│   │   ├── components/          # 再利用可能UIコンポーネント
│   │   └── __init__.py
│   ├── core/                     # コアビジネスロジック層
│   │   ├── models/              # ドメインモデル
│   │   │   ├── entities.py      # エンティティ
│   │   │   ├── value_objects.py # 値オブジェクト
│   │   │   └── __init__.py
│   │   ├── services/            # ビジネスサービス
│   │   │   ├── domain_service.py
│   │   │   └── __init__.py
│   │   ├── workflows/           # ワークフロー・ユースケース
│   │   │   ├── use_cases.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── infrastructure/          # インフラストラクチャ層
│   │   ├── database/            # データベース関連
│   │   │   ├── repositories.py  # リポジトリ実装
│   │   │   ├── models.py        # データベースモデル
│   │   │   └── __init__.py
│   │   ├── external/            # 外部API・サービス
│   │   │   ├── api_clients.py
│   │   │   └── __init__.py
│   │   ├── auth/                # 認証・認可
│   │   │   ├── handlers.py
│   │   │   └── __init__.py
│   │   ├── storage/             # ファイル・ストレージ
│   │   │   ├── file_handlers.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── utils/                   # ユーティリティ
│   │   ├── helpers.py           # ヘルパー関数
│   │   ├── constants.py         # 定数
│   │   ├── exceptions.py        # カスタム例外
│   │   └── __init__.py
│   └── __init__.py
├── tests/                       # テストコード
│   ├── unit/                    # 単体テスト
│   │   ├── core/
│   │   ├── infrastructure/
│   │   └── __init__.py
│   ├── integration/             # 統合テスト
│   │   └── __init__.py
│   ├── e2e/                     # E2Eテスト
│   │   └── __init__.py
│   ├── fixtures/                # テストデータ
│   └── conftest.py              # pytest設定
├── scripts/                     # 運用・デプロイスクリプト
│   ├── setup.ps1               # 環境セットアップ
│   ├── run.ps1                 # アプリケーション実行
│   └── deploy.ps1              # デプロイスクリプト
├── sql/                         # データベーススクリプト
│   ├── migrations/              # マイグレーション
│   ├── seeds/                   # 初期データ
│   └── create_tables.sql
├── docs/                        # ドキュメント
│   ├── architecture/            # アーキテクチャ図
│   ├── api/                     # API仕様
│   └── setup/                   # セットアップガイド
├── config/                      # 設定ファイル
│   ├── development.yml
│   ├── production.yml
│   └── secrets.example.yml
├── .streamlit/                  # Streamlit設定（該当する場合）
│   └── secrets.toml
├── requirements.txt             # Python依存関係
├── requirements-dev.txt         # 開発用依存関係
├── Dockerfile                   # コンテナ定義
├── docker-compose.yml          # 開発環境定義
├── .gitignore                  # Git除外設定
├── .env.example                # 環境変数テンプレート
├── README.md                   # プロジェクト説明
└── main.py                     # エントリーポイント
```

## 🎯 各層の責務

### 1. アプリケーション層 (`src/app/`)
- **責務**: ユーザーインターフェース、プレゼンテーション
- **含むもの**: 
  - UIコンポーネント
  - ページ構成
  - ユーザー入力処理
  - 表示ロジック

### 2. コア層 (`src/core/`)
- **責務**: ビジネスロジック、ドメインルール
- **含むもの**:
  - ドメインエンティティ
  - ビジネスルール
  - ユースケース
  - ドメインサービス

### 3. インフラストラクチャ層 (`src/infrastructure/`)
- **責務**: 外部システムとの連携
- **含むもの**:
  - データベースアクセス
  - 外部API呼び出し
  - ファイルシステム操作
  - 認証・認可処理

### 4. ユーティリティ層 (`src/utils/`)
- **責務**: 共通機能、ヘルパー
- **含むもの**:
  - 共通関数
  - 定数定義
  - カスタム例外
  - 設定管理

## 🚀 使用方法

### 1. プロジェクト作成
```bash
# 新規プロジェクト作成
mkdir my-project
cd my-project

# ディレクトリ構造作成
mkdir -p src/{app/{pages,components},core/{models,services,workflows},infrastructure/{database,external,auth,storage},utils}
mkdir -p tests/{unit/{core,infrastructure},integration,e2e,fixtures}
mkdir -p scripts sql/{migrations,seeds} docs/{architecture,api,setup} config

# __init__.pyファイル作成
find src -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;
```

### 2. 基本ファイル作成
```bash
# エントリーポイント
touch main.py
touch src/app/main.py

# 設定ファイル
touch requirements.txt requirements-dev.txt
touch .env.example .gitignore
touch README.md

# Docker設定
touch Dockerfile docker-compose.yml

# テスト設定
touch tests/conftest.py
```

## 📝 実装例

### エンティティ例 (`src/core/models/entities.py`)
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: Optional[int]
    email: str
    name: str
    created_at: Optional[datetime] = None
    
    def is_valid_email(self) -> bool:
        return "@" in self.email and "." in self.email
```

### ユースケース例 (`src/core/workflows/use_cases.py`)
```python
from abc import ABC, abstractmethod
from ..models.entities import User

class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User:
        pass

class CreateUserUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def execute(self, email: str, name: str) -> User:
        user = User(id=None, email=email, name=name)
        if not user.is_valid_email():
            raise ValueError("Invalid email format")
        return self.user_repo.save(user)
```

### リポジトリ実装例 (`src/infrastructure/database/repositories.py`)
```python
from ...core.models.entities import User
from ...core.workflows.use_cases import UserRepository

class SQLUserRepository(UserRepository):
    def __init__(self, db_connection):
        self.db = db_connection
    
    def save(self, user: User) -> User:
        # データベース保存ロジック
        query = "INSERT INTO users (email, name) VALUES (?, ?)"
        cursor = self.db.execute(query, (user.email, user.name))
        user.id = cursor.lastrowid
        return user
```

## 🔄 依存関係のルール

### 依存方向
```
App Layer → Core Layer ← Infrastructure Layer
              ↑
        Utils Layer
```

### 依存関係の原則
1. **外側の層は内側の層に依存可能**
2. **内側の層は外側の層に依存禁止**
3. **同じ層内での依存は最小限に**
4. **インターフェースを使用した依存関係逆転**

## 📏 命名規則

### ディレクトリ
- 小文字 + アンダースコア: `my_module`
- 複数形を使用: `models`, `services`

### ファイル
- 小文字 + アンダースコア: `user_service.py`
- 機能を表す名前: `create_user.py`

### クラス
- PascalCase: `UserService`
- 責務を表す名前: `CreateUserUseCase`

### 関数・変数
- snake_case: `create_user()`
- 動詞 + 名詞: `get_user_by_id()`

## 🧪 テスト戦略

### 単体テスト
- 各層の個別テスト
- モックを使用した外部依存の分離

### 統合テスト
- 層間の連携テスト
- データベース統合テスト

### E2Eテスト
- エンドツーエンドシナリオ
- ユーザージャーニーテスト

## 📦 パッケージ管理

### requirements.txt（本番用）
```txt
streamlit>=1.28.0
pandas>=2.0.0
requests>=2.31.0
```

### requirements-dev.txt（開発用）
```txt
-r requirements.txt
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

## 🚀 次のステップ

1. **プロジェクト固有の調整**
2. **CI/CDパイプライン設定**
3. **監視・ログ設定**
4. **セキュリティ設定**
5. **パフォーマンス最適化**

このテンプレートを基に、プロジェクトの要件に応じてカスタマイズしてください。 