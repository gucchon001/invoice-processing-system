"""
統一ワークフロー アダプターシステム

入力・出力の統一インターフェースを提供します。
注意: LocalFileAdapterは削除済み（UnifiedWorkflowEngineに統合）
"""

from .base_adapters import BaseInputAdapter, BaseOutputAdapter, FileData

__all__ = [
    'BaseInputAdapter',
    'BaseOutputAdapter', 
    'FileData'
] 