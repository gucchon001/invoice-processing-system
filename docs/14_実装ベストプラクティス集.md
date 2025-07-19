# Python実装ベストプラクティス集

## 📋 概要

Clean Architectureに基づくPythonプロジェクトの実装において、品質と保守性を向上させるベストプラクティス集です。

## 🏗️ プロジェクト構造のベストプラクティス

### 1. ファイルとモジュールの組織化

#### ✅ 推奨パターン
```python
# 機能別でファイルを分割
src/core/models/
├── user.py          # ユーザー関連のみ
├── invoice.py       # 請求書関連のみ
└── payment.py       # 支払い関連のみ

# 責務の明確な分離
src/infrastructure/database/
├── connection.py    # DB接続管理
├── repositories.py  # データアクセス
└── migrations.py    # スキーマ変更
```

#### ❌ 避けるべきパターン
```python
# 巨大なファイル
src/models.py        # 全てのモデルが1ファイル（NG）
src/utils.py         # 何でも入れ物（NG）
```

### 2. __init__.pyの活用

#### 公開APIの明確化
```python
# src/core/models/__init__.py
from .user import User, UserService
from .invoice import Invoice, InvoiceService

# 外部に公開するもののみエクスポート
__all__ = [
    'User',
    'UserService', 
    'Invoice',
    'InvoiceService'
]
```

#### バージョン管理
```python
# src/__init__.py
__version__ = "1.2.3"
__author__ = "Your Team"
__email__ = "team@company.com"
```

## 🎯 コーディングスタンダード

### 1. 型ヒントの活用

#### 完全な型ヒント
```python
from typing import List, Optional, Dict, Any
from datetime import datetime

class Invoice:
    def __init__(self, 
                 id: Optional[int],
                 amount: float,
                 created_at: datetime) -> None:
        self.id = id
        self.amount = amount
        self.created_at = created_at
    
    def calculate_tax(self, rate: float) -> float:
        return self.amount * rate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'amount': self.amount,
            'created_at': self.created_at.isoformat()
        }
```

#### Union型と Generic型
```python
from typing import Union, Generic, TypeVar, Protocol

T = TypeVar('T')

class Repository(Protocol, Generic[T]):
    def save(self, entity: T) -> T: ...
    def find_by_id(self, id: Union[int, str]) -> Optional[T]: ...
```

### 2. データクラスの活用

#### dataclass基本パターン
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)  # イミュータブル
class User:
    id: Optional[int]
    email: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not self.email or '@' not in self.email:
            raise ValueError("Invalid email format")
```

#### ビジネスロジック付きdataclass
```python
@dataclass
class Invoice:
    amount: float
    tax_rate: float = 0.1
    
    @property
    def total_amount(self) -> float:
        return self.amount * (1 + self.tax_rate)
    
    def is_large_invoice(self) -> bool:
        return self.amount > 100000
```

### 3. 例外処理のベストプラクティス

#### カスタム例外の定義
```python
# src/utils/exceptions.py
class InvoiceProcessingError(Exception):
    """請求書処理関連のエラー基底クラス"""
    pass

class InvoiceValidationError(InvoiceProcessingError):
    """請求書バリデーションエラー"""
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        super().__init__(f"Validation error for {field}: {message}")

class InvoiceNotFoundError(InvoiceProcessingError):
    """請求書が見つからないエラー"""
    def __init__(self, invoice_id: int):
        self.invoice_id = invoice_id
        super().__init__(f"Invoice not found: {invoice_id}")
```

#### 適切な例外処理
```python
class InvoiceService:
    def process_invoice(self, data: dict) -> Invoice:
        try:
            # バリデーション
            if not data.get('amount') or data['amount'] <= 0:
                raise InvoiceValidationError('amount', data.get('amount'), 'Must be positive')
            
            # 処理実行
            invoice = self._create_invoice(data)
            return self._save_invoice(invoice)
            
        except InvoiceValidationError:
            # 具体的な例外は再発生
            raise
        except Exception as e:
            # 予期しないエラーはラップ
            raise InvoiceProcessingError(f"Unexpected error: {e}") from e
```

## 🔧 パフォーマンス最適化

### 1. データベースアクセス最適化

#### N+1問題の回避
```python
# ❌ 悪い例：N+1問題
def get_invoices_with_users_bad() -> List[Invoice]:
    invoices = db.query("SELECT * FROM invoices")
    for invoice in invoices:
        # 各請求書ごとにクエリが発生（N+1問題）
        user = db.query("SELECT * FROM users WHERE id = ?", invoice.user_id)
        invoice.user = user
    return invoices

# ✅ 良い例：JOINを使用
def get_invoices_with_users_good() -> List[Invoice]:
    query = """
    SELECT i.*, u.name as user_name, u.email as user_email
    FROM invoices i
    JOIN users u ON i.user_id = u.id
    """
    rows = db.query(query)
    return [self._build_invoice_with_user(row) for row in rows]
```

#### バッチ処理
```python
class InvoiceRepository:
    def save_multiple(self, invoices: List[Invoice]) -> List[Invoice]:
        """バッチでの保存処理"""
        query = """
        INSERT INTO invoices (user_id, amount, created_at)
        VALUES (?, ?, ?)
        """
        data = [(inv.user_id, inv.amount, inv.created_at) for inv in invoices]
        self.db.executemany(query, data)
        return invoices
```

### 2. メモリ使用量の最適化

#### ジェネレーターの活用
```python
# ❌ 悪い例：全てをメモリに読み込み
def process_all_invoices_bad() -> List[ProcessedInvoice]:
    all_invoices = self.repository.get_all()  # 大量データを一度に取得
    return [self.process_invoice(inv) for inv in all_invoices]

# ✅ 良い例：ジェネレーターで逐次処理
def process_all_invoices_good() -> Iterator[ProcessedInvoice]:
    for invoice in self.repository.get_all_as_generator():
        yield self.process_invoice(invoice)
```

#### __slots__の活用
```python
class LightweightUser:
    """メモリ効率の良いユーザークラス"""
    __slots__ = ['id', 'name', 'email']
    
    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email
```

## 🧪 テストのベストプラクティス

### 1. テスト構造化

#### AAA パターン（Arrange-Act-Assert）
```python
import pytest
from unittest.mock import Mock

class TestInvoiceService:
    def test_create_invoice_success(self):
        # Arrange（準備）
        repository = Mock()
        service = InvoiceService(repository)
        invoice_data = {
            'amount': 1000.0,
            'user_id': 1,
            'description': 'テスト請求書'
        }
        expected_invoice = Invoice(id=1, **invoice_data)
        repository.save.return_value = expected_invoice
        
        # Act（実行）
        result = service.create_invoice(invoice_data)
        
        # Assert（検証）
        assert result.id == 1
        assert result.amount == 1000.0
        repository.save.assert_called_once()
```

#### パラメータ化テスト
```python
@pytest.mark.parametrize("amount,expected_tax", [
    (1000, 100),      # 10%税率
    (2000, 200),      # 10%税率
    (0, 0),           # 境界値
])
def test_calculate_tax(amount, expected_tax):
    invoice = Invoice(amount=amount, tax_rate=0.1)
    assert invoice.calculate_tax() == expected_tax
```

### 2. フィクスチャーの活用

#### 再利用可能なフィクスチャー
```python
# tests/conftest.py
@pytest.fixture
def sample_user():
    return User(
        id=1,
        email="test@example.com",
        name="テストユーザー"
    )

@pytest.fixture
def sample_invoice(sample_user):
    return Invoice(
        id=1,
        user_id=sample_user.id,
        amount=1000.0,
        created_at=datetime.now()
    )

# テストで使用
def test_invoice_processing(sample_invoice):
    # sample_invoiceが自動的に注入される
    assert sample_invoice.amount == 1000.0
```

### 3. モックの効果的使用

#### 外部依存のモック化
```python
class TestEmailService:
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        # SMTPライブラリをモック化
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        email_service = EmailService()
        result = email_service.send_notification(
            to="test@example.com",
            subject="テスト",
            body="メッセージ"
        )
        
        assert result is True
        mock_server.sendmail.assert_called_once()
```

## 📝 ドキュメンテーション

### 1. Docstring規則

#### Google スタイル
```python
def calculate_invoice_total(amount: float, tax_rate: float = 0.1) -> float:
    """請求書の合計金額を計算します。

    Args:
        amount: 基本金額（税抜き）
        tax_rate: 税率（デフォルト: 0.1 = 10%）

    Returns:
        税込み合計金額

    Raises:
        ValueError: amountが負の値の場合

    Example:
        >>> calculate_invoice_total(1000, 0.08)
        1080.0
    """
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    return amount * (1 + tax_rate)
```

### 2. 型ヒント付きインターフェース

#### プロトコルクラス
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PaymentProcessor(Protocol):
    """支払い処理のプロトコル"""
    
    def process_payment(self, amount: float, payment_method: str) -> bool:
        """支払いを処理します。
        
        Args:
            amount: 支払い金額
            payment_method: 支払い方法
            
        Returns:
            処理成功時はTrue、失敗時はFalse
        """
        ...
```

## 🔒 セキュリティベストプラクティス

### 1. 入力検証

#### バリデーション関数
```python
import re
from typing import Union

def validate_email(email: str) -> bool:
    """メールアドレスの形式を検証"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_filename(filename: str) -> str:
    """ファイル名をサニタイズ"""
    # 危険な文字を除去
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename[:255]  # 長さ制限
```

### 2. 機密情報の管理

#### 環境変数の使用
```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    """設定管理クラス"""
    database_url: str = os.getenv('DATABASE_URL', '')
    api_key: str = os.getenv('API_KEY', '')
    debug_mode: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    def __post_init__(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        if not self.api_key:
            raise ValueError("API_KEY is required")
```

## 🚀 デプロイメント準備

### 1. 設定ファイルテンプレート

#### requirements.txt管理
```txt
# requirements.txt（本番用）
streamlit>=1.28.0
pandas>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0

# requirements-dev.txt（開発用）
-r requirements.txt
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
coverage>=7.3.0
```

#### .env.example
```bash
# データベース設定
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# API設定
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_DRIVE_CREDENTIALS=path/to/credentials.json

# アプリケーション設定
DEBUG=False
LOG_LEVEL=INFO
```

### 2. Docker化

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# ポート公開
EXPOSE 8501

# アプリケーション実行
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

このベストプラクティス集を参考に、品質の高いPythonアプリケーションを開発してください。 