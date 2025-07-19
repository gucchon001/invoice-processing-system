# Clean Architecture設計ガイドライン

## 📋 概要

Robert C. Martin（Uncle Bob）のClean Architecture原則に基づく、Pythonプロジェクトの設計ガイドラインです。

## 🏛️ Clean Architectureの基本原則

### 1. 独立性の原則
- **フレームワーク独立**: 特定のフレームワークに依存しない
- **テスト可能**: UIやデータベースなしでビジネスルールをテスト可能
- **UI独立**: UIを容易に変更可能（Web → CLI → API）
- **データベース独立**: データベースを入れ替え可能
- **外部エージェント独立**: ビジネスルールが外部サービスを知らない

### 2. 依存関係のルール
```
外側の層 → 内側の層（一方向のみ）

🔴 禁止: 内側の層が外側の層を知ること
✅ 推奨: 外側の層が内側の層を使用すること
```

## 🎯 層構造と責務

### 1. エンティティ層（最内層）
```python
# src/core/models/entities.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Invoice:
    """請求書エンティティ - ビジネスルールの核心"""
    id: Optional[int]
    company_name: str
    amount: float
    issue_date: datetime
    due_date: datetime
    
    def is_overdue(self) -> bool:
        """支払期限を過ぎているかチェック"""
        return datetime.now() > self.due_date
    
    def calculate_tax(self, tax_rate: float) -> float:
        """税額計算"""
        return self.amount * tax_rate
```

**責務**:
- エンタープライズ全体のビジネスルール
- 最も一般的で高レベルなルール
- 外部の変更による影響を最も受けにくい

### 2. ユースケース層
```python
# src/core/workflows/use_cases.py
from abc import ABC, abstractmethod
from ..models.entities import Invoice

class InvoiceRepository(ABC):
    """抽象リポジトリ - 依存関係逆転の要"""
    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice:
        pass
    
    @abstractmethod
    def find_by_id(self, invoice_id: int) -> Optional[Invoice]:
        pass

class ProcessInvoiceUseCase:
    """請求書処理ユースケース"""
    def __init__(self, repository: InvoiceRepository):
        self.repository = repository
    
    def execute(self, invoice_data: dict) -> Invoice:
        # ビジネスロジックの実行
        invoice = Invoice(**invoice_data)
        
        # バリデーション
        if invoice.amount <= 0:
            raise ValueError("金額は正の値である必要があります")
        
        # 保存
        return self.repository.save(invoice)
```

**責務**:
- アプリケーション固有のビジネスルール
- エンティティの流れを調整
- 外部の変更がエンティティに影響しないよう保護

### 3. インターフェースアダプター層
```python
# src/infrastructure/database/repositories.py
from typing import Optional
from ...core.models.entities import Invoice
from ...core.workflows.use_cases import InvoiceRepository

class SQLInvoiceRepository(InvoiceRepository):
    """具象リポジトリ - 抽象インターフェースの実装"""
    def __init__(self, db_connection):
        self.db = db_connection
    
    def save(self, invoice: Invoice) -> Invoice:
        query = """
        INSERT INTO invoices (company_name, amount, issue_date, due_date)
        VALUES (?, ?, ?, ?)
        """
        cursor = self.db.execute(query, (
            invoice.company_name,
            invoice.amount,
            invoice.issue_date,
            invoice.due_date
        ))
        invoice.id = cursor.lastrowid
        return invoice
    
    def find_by_id(self, invoice_id: int) -> Optional[Invoice]:
        query = "SELECT * FROM invoices WHERE id = ?"
        row = self.db.execute(query, (invoice_id,)).fetchone()
        if row:
            return Invoice(
                id=row['id'],
                company_name=row['company_name'],
                amount=row['amount'],
                issue_date=row['issue_date'],
                due_date=row['due_date']
            )
        return None
```

**責務**:
- データフォーマットの変換
- ユースケースとフレームワーク間の橋渡し
- 外部システムの詳細を隠蔽

### 4. フレームワーク・ドライバー層（最外層）
```python
# src/app/main.py
import streamlit as st
from ...core.workflows.use_cases import ProcessInvoiceUseCase
from ...infrastructure.database.repositories import SQLInvoiceRepository

def invoice_processing_page():
    """請求書処理ページ"""
    st.title("請求書処理")
    
    # 依存関係の注入
    db_connection = get_database_connection()
    repository = SQLInvoiceRepository(db_connection)
    use_case = ProcessInvoiceUseCase(repository)
    
    # UI入力
    company_name = st.text_input("会社名")
    amount = st.number_input("金額", min_value=0.0)
    
    if st.button("処理実行"):
        try:
            invoice_data = {
                "company_name": company_name,
                "amount": amount,
                "issue_date": datetime.now(),
                "due_date": datetime.now() + timedelta(days=30)
            }
            result = use_case.execute(invoice_data)
            st.success(f"請求書が作成されました: ID {result.id}")
        except ValueError as e:
            st.error(f"エラー: {e}")
```

**責務**:
- フレームワーク固有の実装
- UI/Web/データベースの詳細
- 最も変更される可能性が高い

## 🔄 依存関係逆転の実装

### 1. 抽象インターフェースの定義
```python
# src/core/workflows/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.entities import Invoice

class InvoiceService(ABC):
    """請求書サービスの抽象インターフェース"""
    @abstractmethod
    def process_pdf(self, pdf_data: bytes) -> dict:
        pass

class EmailService(ABC):
    """メールサービスの抽象インターフェース"""
    @abstractmethod
    def send_notification(self, to: str, subject: str, body: str) -> bool:
        pass
```

### 2. 具象実装
```python
# src/infrastructure/external/ai_service.py
from ...core.workflows.interfaces import InvoiceService

class GeminiInvoiceService(InvoiceService):
    """Gemini APIを使った請求書処理サービス"""
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def process_pdf(self, pdf_data: bytes) -> dict:
        # Gemini API呼び出し
        return {"company_name": "extracted", "amount": 1000.0}
```

### 3. 依存関係注入
```python
# src/app/di_container.py
from ..core.workflows.use_cases import ProcessInvoiceUseCase
from ..infrastructure.database.repositories import SQLInvoiceRepository
from ..infrastructure.external.ai_service import GeminiInvoiceService

class DIContainer:
    """依存関係注入コンテナ"""
    def __init__(self):
        self._db_connection = None
        self._invoice_repository = None
        self._ai_service = None
    
    def get_invoice_use_case(self) -> ProcessInvoiceUseCase:
        repository = self._get_invoice_repository()
        return ProcessInvoiceUseCase(repository)
    
    def _get_invoice_repository(self) -> SQLInvoiceRepository:
        if not self._invoice_repository:
            self._invoice_repository = SQLInvoiceRepository(
                self._get_db_connection()
            )
        return self._invoice_repository
```

## 🧪 テスト戦略

### 1. 単体テスト（コア層）
```python
# tests/unit/core/test_use_cases.py
import pytest
from unittest.mock import Mock
from src.core.workflows.use_cases import ProcessInvoiceUseCase, InvoiceRepository

class TestProcessInvoiceUseCase:
    def test_process_valid_invoice(self):
        # Arrange
        mock_repository = Mock(spec=InvoiceRepository)
        use_case = ProcessInvoiceUseCase(mock_repository)
        invoice_data = {
            "company_name": "テスト会社",
            "amount": 1000.0,
            "issue_date": datetime.now(),
            "due_date": datetime.now() + timedelta(days=30)
        }
        
        # Act
        result = use_case.execute(invoice_data)
        
        # Assert
        mock_repository.save.assert_called_once()
        assert result.company_name == "テスト会社"
```

### 2. 統合テスト
```python
# tests/integration/test_invoice_processing.py
import pytest
from src.infrastructure.database.repositories import SQLInvoiceRepository
from src.core.workflows.use_cases import ProcessInvoiceUseCase

class TestInvoiceProcessingIntegration:
    def test_full_invoice_processing(self, test_db):
        # 実際のデータベースを使った統合テスト
        repository = SQLInvoiceRepository(test_db)
        use_case = ProcessInvoiceUseCase(repository)
        
        invoice_data = {...}
        result = use_case.execute(invoice_data)
        
        # データベースに実際に保存されているかチェック
        saved_invoice = repository.find_by_id(result.id)
        assert saved_invoice is not None
```

## 📏 設計ルール

### ✅ Do（推奨）
1. **内側の層は外側の層を知らない**
2. **抽象インターフェースを通じて依存**
3. **ビジネスルールをコア層に集約**
4. **依存関係注入を使用**
5. **各層の責務を明確に分離**

### ❌ Don't（禁止）
1. **内側の層に外側の詳細を漏らさない**
2. **具象クラスに直接依存しない**
3. **フレームワーク固有コードをコア層に書かない**
4. **データベースモデルをエンティティとして使わない**
5. **層を跨いだ複雑な依存関係を作らない**

## 🔧 実装パターン

### 1. リポジトリパターン
```python
# 抽象リポジトリ（コア層）
class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass

# 具象実装（インフラ層）
class SQLUserRepository(UserRepository):
    def find_by_email(self, email: str) -> Optional[User]:
        # SQL実装
        pass
```

### 2. ファクトリーパターン
```python
# src/core/factories/invoice_factory.py
class InvoiceFactory:
    @staticmethod
    def create_from_pdf_data(pdf_data: dict) -> Invoice:
        return Invoice(
            company_name=pdf_data.get('company'),
            amount=float(pdf_data.get('amount', 0)),
            issue_date=parse_date(pdf_data.get('date')),
            due_date=calculate_due_date(pdf_data.get('date'))
        )
```

### 3. ストラテジーパターン
```python
# 支払い方法の戦略
class PaymentStrategy(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> bool:
        pass

class CreditCardPayment(PaymentStrategy):
    def process_payment(self, amount: float) -> bool:
        # クレジットカード処理
        pass

class BankTransferPayment(PaymentStrategy):
    def process_payment(self, amount: float) -> bool:
        # 銀行振込処理
        pass
```

## 🚀 移行戦略

### 1. 段階的リファクタリング
1. **エンティティ抽出**: 既存コードからドメインモデルを特定
2. **ユースケース分離**: ビジネスロジックをユースケースクラスに移動
3. **インターフェース導入**: 抽象インターフェースを定義
4. **依存関係逆転**: 具象実装を分離
5. **テスト追加**: 各層のテストを作成

### 2. 新機能での適用
- 新機能は最初からClean Architectureで実装
- 既存機能への影響を最小限に抑制
- 段階的に全体をリファクタリング

## 📈 効果測定

### 品質指標
- **テストカバレッジ**: 80%以上を目標
- **循環複雑度**: 関数あたり10以下
- **依存関係**: 層間の一方向性維持
- **結合度**: 疎結合の維持

### ビジネス価値
- **開発速度**: 機能追加の高速化
- **品質向上**: バグ減少
- **保守性**: 変更コストの削減
- **柔軟性**: 要件変更への対応力

Clean Architectureは初期投資が必要ですが、長期的にプロジェクトの価値を大幅に向上させます。 