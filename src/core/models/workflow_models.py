"""
ワークフローモデル定義
請求書処理統合ワークフローで使用するデータモデルを統一管理
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union


class ProcessingMode:
    """処理モードの定義"""
    SINGLE = "single"           # 単一ファイル処理
    BATCH = "batch"            # バッチ処理
    OCR_TEST = "ocr_test"      # OCRテスト
    UPLOAD = "upload"          # アップロード
    VALIDATION = "validation"   # 検証モード
    TEST = "test"              # テストモード


class ProcessingStatus:
    """処理ステータスの定義"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """ワークフロー実行ステータス"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowProgress:
    """ワークフロー進捗情報"""
    status: WorkflowStatus
    step: str
    progress_percent: int
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowResult:
    """ワークフロー処理結果"""
    success: bool
    invoice_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None
    file_info: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    progress_history: Optional[List[WorkflowProgress]] = None


@dataclass
class ProcessingConfig:
    """処理設定"""
    mode: str = ProcessingMode.SINGLE
    include_validation: bool = True
    auto_save: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    prompt_key: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None


@dataclass
class BatchProcessingResult:
    """バッチ処理結果"""
    total_files: int
    successful_files: int
    failed_files: int
    processing_time: float
    results: List[WorkflowResult]
    summary: Dict[str, Any]
    errors: List[Dict[str, str]]


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    score: float
    warnings: List[str]
    errors: List[str]
    details: Dict[str, Any]


# 互換性のためのエイリアス
ProcessingModes = ProcessingMode
WorkflowStatuses = ProcessingStatus 