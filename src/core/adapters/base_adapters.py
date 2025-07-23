"""
統一ワークフロー 基底アダプタークラス

入力・出力アダプターの共通インターフェースを定義します。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class FileData:
    """統一ファイルデータクラス"""
    content: bytes
    filename: str
    source: str
    metadata: Dict[str, Any]
    
    @property
    def size(self) -> int:
        """ファイルサイズ取得"""
        return len(self.content)
    
    @property
    def file_extension(self) -> str:
        """ファイル拡張子取得"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''

class BaseInputAdapter(ABC):
    """入力アダプター基底クラス"""
    
    @abstractmethod
    async def get_files(self, config: Dict[str, Any]) -> List[FileData]:
        """
        ファイル取得（統一インターフェース）
        
        Args:
            config: 取得設定
            
        Returns:
            ファイルデータリスト
        """
        pass
    
    @abstractmethod
    def validate_input(self, config: Dict[str, Any]) -> bool:
        """
        入力検証
        
        Args:
            config: 検証設定
            
        Returns:
            検証結果
        """
        pass
    
    def get_metadata(self, file_data: FileData) -> Dict[str, Any]:
        """
        メタデータ取得
        
        Args:
            file_data: ファイルデータ
            
        Returns:
            メタデータ辞書
        """
        return {
            'filename': file_data.filename,
            'size': file_data.size,
            'source': file_data.source,
            'extension': file_data.file_extension,
            **file_data.metadata
        }

class BaseOutputAdapter(ABC):
    """出力アダプター基底クラス"""
    
    @abstractmethod
    async def send_output(self, result: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """
        出力処理（統一インターフェース）
        
        Args:
            result: 処理結果
            config: 出力設定
            
        Returns:
            出力成功可否
        """
        pass
    
    @abstractmethod
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        出力データ検証
        
        Args:
            result: 出力データ
            
        Returns:
            検証結果
        """
        pass 