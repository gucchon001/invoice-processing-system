"""
ローカルファイル入力アダプター

Streamlitのfile_uploaderからのファイル処理を統一インターフェースで提供します。
"""

from typing import Dict, Any, List
import logging

from .base_adapters import BaseInputAdapter, FileData

logger = logging.getLogger(__name__)

class LocalFileAdapter(BaseInputAdapter):
    """ローカルファイルアダプター"""
    
    async def get_files(self, config: Dict[str, Any]) -> List[FileData]:
        """
        Streamlit uploaded_filesから統一FileDataに変換
        
        Args:
            config: {'uploaded_files': StreamlitUploadedFiles}
            
        Returns:
            統一FileDataリスト
        """
        uploaded_files = config.get('uploaded_files', [])
        file_data_list = []
        
        for uploaded_file in uploaded_files:
            try:
                # ファイル内容読み取り
                file_content = uploaded_file.read()
                
                # 統一FileData形式に変換
                file_data = FileData(
                    content=file_content,
                    filename=uploaded_file.name,
                    source="local_upload",
                    metadata={
                        "size": uploaded_file.size,
                        "type": uploaded_file.type,
                        "upload_method": "streamlit_file_uploader"
                    }
                )
                
                file_data_list.append(file_data)
                logger.info(f"ローカルファイル変換完了: {uploaded_file.name}")
                
            except Exception as e:
                logger.error(f"ローカルファイル処理エラー {uploaded_file.name}: {e}")
                continue
        
        logger.info(f"ローカルファイル一括変換完了: {len(file_data_list)}件")
        return file_data_list
    
    def validate_input(self, config: Dict[str, Any]) -> bool:
        """
        入力検証
        
        Args:
            config: 検証設定
            
        Returns:
            検証結果
        """
        uploaded_files = config.get('uploaded_files', [])
        
        if not uploaded_files:
            logger.warning("アップロードファイルが存在しません")
            return False
        
        # ファイル形式チェック
        supported_types = config.get('supported_types', ['application/pdf'])
        max_file_size = config.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        
        for uploaded_file in uploaded_files:
            # MIME type チェック
            if uploaded_file.type not in supported_types:
                logger.error(f"サポートされていないファイル形式: {uploaded_file.type}")
                return False
            
            # ファイルサイズチェック
            if uploaded_file.size > max_file_size:
                logger.error(f"ファイルサイズが制限を超過: {uploaded_file.size} > {max_file_size}")
                return False
        
        logger.info(f"入力検証成功: {len(uploaded_files)}件")
        return True 