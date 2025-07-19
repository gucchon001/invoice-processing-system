# プロジェクトテンプレート集 - INDEX

## 📋 概要

Clean Architecture原則に基づくPythonプロジェクトの構造テンプレートと設計ガイドライン集です。
このテンプレート集を使用することで、他のプロジェクトでも同様の高品質な構造を素早く構築できます。

## 📚 ドキュメント一覧

### 🏗️ 基本構造テンプレート
1. **[12_Pythonプロジェクト構造テンプレート.md](./12_Pythonプロジェクト構造テンプレート.md)**
   - Clean Architectureディレクトリ構造
   - 各層の責務と実装例
   - 使用方法とセットアップ手順

### 🎯 設計ガイドライン
2. **[13_Clean Architecture設計ガイドライン.md](./13_Clean%20Architecture設計ガイドライン.md)**
   - Clean Architectureの基本原則
   - 依存関係逆転の実装方法
   - 各層の詳細な責務と実装パターン

### 💎 実装ベストプラクティス
3. **[14_実装ベストプラクティス集.md](./14_実装ベストプラクティス集.md)**
   - コーディングスタンダード
   - パフォーマンス最適化
   - テスト戦略とセキュリティ

### ⚙️ 自動化スクリプト
4. **[PowerShellテンプレート_プロジェクト初期化版.ps1](./PowerShellテンプレート_プロジェクト初期化版.ps1)**
   - プロジェクト構造の自動生成
   - 複数プロジェクトタイプ対応
   - Docker・テスト環境の自動セットアップ

## 🚀 クイックスタート

### 1. 新規プロジェクトの作成

#### PowerShellスクリプトを使用（推奨）
```powershell
# Streamlitプロジェクトの作成
.\PowerShellテンプレート_プロジェクト初期化版.ps1 -ProjectName "my-invoice-app" -ProjectType "streamlit" -WithDocker -WithTests

# FastAPIプロジェクトの作成
.\PowerShellテンプレート_プロジェクト初期化版.ps1 -ProjectName "my-api-service" -ProjectType "fastapi" -WithDocker -WithTests

# 基本Pythonプロジェクトの作成
.\PowerShellテンプレート_プロジェクト初期化版.ps1 -ProjectName "my-python-project" -ProjectType "basic" -WithTests
```

#### 手動作成
```bash
# プロジェクトディレクトリの作成
mkdir my-new-project
cd my-new-project

# ディレクトリ構造の作成
mkdir -p src/{app/{pages,components},core/{models,services,workflows},infrastructure/{database,external,auth,storage},utils}
mkdir -p tests/{unit/{core,infrastructure},integration,e2e,fixtures}
mkdir -p scripts sql/{migrations,seeds} docs/{architecture,api,setup} config

# __init__.pyファイルの作成
find src -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;
```

### 2. プロジェクトのカスタマイズ

作成されたプロジェクトを要件に応じてカスタマイズ：

1. **ビジネスロジックの実装** - `src/core/` ディレクトリ
2. **外部サービス連携** - `src/infrastructure/` ディレクトリ  
3. **UI実装** - `src/app/` ディレクトリ
4. **テスト追加** - `tests/` ディレクトリ

### 3. 開発環境のセットアップ

```bash
# 仮想環境の作成
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 依存関係のインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 開発用

# 環境変数の設定
cp .env.example .env
# .envファイルを編集

# アプリケーションの実行
python main.py
```

## 🎯 適用可能なプロジェクトタイプ

### 1. Webアプリケーション
- **Streamlit**: データ分析・可視化アプリ
- **FastAPI**: REST API・マイクロサービス
- **Django**: 大規模Webアプリケーション

### 2. データ処理アプリケーション
- **ETL/ELT**: データ変換・統合
- **機械学習**: モデル訓練・推論
- **バッチ処理**: 定期処理・レポート生成

### 3. エンタープライズアプリケーション
- **業務システム**: 請求書処理・在庫管理
- **統合システム**: API連携・データ統合
- **自動化ツール**: ワークフロー・プロセス自動化

## 📏 品質保証

### コード品質指標
- **テストカバレッジ**: 80%以上
- **型ヒント**: 全関数・クラスに適用
- **ドキュメンテーション**: Google スタイル docstring
- **リンター**: flake8, black, mypy 対応

### アーキテクチャ品質
- **依存関係**: 一方向性の維持
- **結合度**: 疎結合の実現
- **凝集度**: 高凝集の維持
- **拡張性**: 機能追加の容易さ

## 🔧 カスタマイズガイド

### 1. プロジェクト固有の調整

#### エンティティの追加
```python
# src/core/models/entities.py
@dataclass
class CustomEntity:
    id: Optional[int]
    name: str
    created_at: datetime
    
    def custom_business_rule(self) -> bool:
        # プロジェクト固有のビジネスルール
        return True
```

#### 新しいサービスの追加
```python
# src/infrastructure/external/custom_service.py
class CustomAPIService:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def call_external_api(self, data: dict) -> dict:
        # 外部API呼び出し
        pass
```

### 2. フレームワーク固有の拡張

#### Streamlit拡張
- セッション状態管理
- カスタムコンポーネント
- レスポンシブデザイン

#### FastAPI拡張
- 認証・認可ミドルウェア
- OpenAPI仕様生成
- 非同期処理

### 3. インフラストラクチャの拡張

#### データベース対応
- PostgreSQL, MySQL, SQLite
- NoSQL（MongoDB, Redis）
- ORM統合（SQLAlchemy, Tortoise）

#### クラウドサービス統合
- AWS, GCP, Azure
- コンテナオーケストレーション
- CI/CDパイプライン

## 📈 進化と保守

### バージョン管理
- **セマンティックバージョニング**: major.minor.patch
- **変更ログ**: CHANGELOG.md の維持
- **後方互換性**: APIインターフェースの安定性

### 継続的改善
- **コードレビュー**: プルリクエストベース
- **リファクタリング**: 定期的な構造見直し
- **パフォーマンス監視**: メトリクス収集・分析

## 🤝 コミュニティ

### コントリビューション
1. **Issue報告**: バグ・改善提案
2. **プルリクエスト**: 機能追加・修正
3. **ドキュメント**: 使用例・ベストプラクティス

### ライセンス
MIT License - 商用・非商用問わず自由に使用可能

## 📞 サポート

### 技術サポート
- **ドキュメント**: 各種ガイドライン参照
- **サンプルコード**: 実装例の提供
- **トラブルシューティング**: よくある問題と解決方法

### 学習リソース
- **Clean Architecture書籍**: Robert C. Martin著
- **Pythonベストプラクティス**: PEP規約
- **テスト駆動開発**: TDD/BDD手法

---

このテンプレート集を活用して、高品質で保守性の高いPythonプロジェクトを効率的に開発してください。

**最終更新日**: 2025年1月20日
**バージョン**: 1.0.0
**作成者**: Invoice Processing Team 