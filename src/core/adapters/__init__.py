"""
統一ワークフロー アダプターシステム

入力・出力の統一インターフェースを提供します。
"""

from .base_adapters import BaseInputAdapter, BaseOutputAdapter, FileData
from .local_file_adapter import LocalFileAdapter

__all__ = [
    'BaseInputAdapter',
    'BaseOutputAdapter', 
    'FileData',
    'LocalFileAdapter'
] 