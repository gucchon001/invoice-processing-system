"""
統合ファイル選択コンポーネント
ローカルアップロード + Google Drive選択を統合
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from infrastructure.storage.google_drive_helper import get_google_drive
    from utils.log_config import get_logger
    
    logger = get_logger(__name__)
    
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")


class UnifiedFileSelector:
    """統合ファイル選択コンポーネント"""
    
    def __init__(self, prefix_key: str):
        """
        Args:
            prefix_key: セッション状態のキープレフィックス（production/ocr_test等）
        """
        self.prefix_key = prefix_key
        self.logger = logger
    
    def render_file_selection_ui(self) -> Tuple[List[Any], str, Dict[str, Any]]:
        """
        統合ファイル選択UIをレンダリング
        
        Returns:
            Tuple[files, source_type, metadata]:
                - files: 選択されたファイル（ローカルまたはGoogle Drive）
                - source_type: "local" または "google_drive"
                - metadata: 追加のメタデータ
        """
        
        st.markdown("### 📤 ファイル選択")
        
        # ファイル選択方法のタブ
        tab1, tab2 = st.tabs(["💻 ローカルファイル", "☁️ Google Drive"])
        
        files = []
        source_type = "local"
        metadata = {}
        
        with tab1:
            files, metadata = self._render_local_upload()
            if files:
                source_type = "local"
        
        with tab2:
            gdrive_files, gdrive_metadata = self._render_google_drive_selection()
            if gdrive_files:
                files = gdrive_files
                source_type = "google_drive"
                metadata = gdrive_metadata
        
        return files, source_type, metadata
    
    def _render_local_upload(self) -> Tuple[List[Any], Dict[str, Any]]:
        """ローカルファイルアップロードUI"""
        st.markdown("#### 📁 ローカルPDFファイルを選択")
        
        uploaded_files = st.file_uploader(
            "請求書PDFファイルを選択してください（複数選択可）",
            type=['pdf'],
            accept_multiple_files=True,
            key=f"{self.prefix_key}_local_upload"
        )
        
        metadata = {}
        if uploaded_files:
            st.success(f"📄 {len(uploaded_files)}件のファイルを選択しました")
            metadata = {
                "file_count": len(uploaded_files),
                "file_names": [f.name for f in uploaded_files]
            }
        
        return uploaded_files or [], metadata
    
    def _render_google_drive_selection(self) -> Tuple[List[Any], Dict[str, Any]]:
        """Google Drive選択UI"""
        st.markdown("#### ☁️ Google Driveフォルダからファイルを選択")
        
        # Google Drive API チェック
        google_drive = None
        try:
            google_drive = get_google_drive()
            if google_drive:
                st.success("✅ Google Drive API 接続済み")
            else:
                st.warning("⚠️ Google Drive API が利用できません")
                st.info("📝 Google Drive機能を使用するには、認証設定が必要です")
                return [], {}
        except Exception as e:
            st.error(f"❌ Google Drive API エラー: {e}")
            return [], {}
        
        # フォルダID入力
        col1, col2 = st.columns([3, 1])
        
        with col1:
            default_folder_id = "1ZCJsI9j8A9VJcmiY79BcP1jgzsD51X6E"
            folder_id = st.text_input(
                "Google DriveフォルダID",
                value=default_folder_id,
                help="PDFファイルが格納されたGoogle DriveフォルダのID",
                key=f"{self.prefix_key}_gdrive_folder_id"
            )
        
        with col2:
            max_files = st.selectbox(
                "最大ファイル数",
                [5, 10, 20, 50, -1],
                format_func=lambda x: "全て" if x == -1 else f"{x}件",
                index=0,
                key=f"{self.prefix_key}_gdrive_max_files"
            )
        
        files = []
        metadata = {}
        
        if folder_id and st.button(
            "📁 フォルダからファイル取得", 
            key=f"{self.prefix_key}_gdrive_fetch",
            use_container_width=True
        ):
            try:
                with st.spinner("Google Driveからファイルリストを取得中..."):
                    # Google Driveからファイル取得のロジック
                    # （実際の実装は既存のOCRTestManagerから移植）
                    files_data = self._fetch_gdrive_files(google_drive, folder_id, max_files)
                    files = files_data.get('files', [])
                    metadata = {
                        "folder_id": folder_id,
                        "max_files": max_files,
                        "file_count": len(files),
                        "folder_name": files_data.get('folder_name', ''),
                        "file_names": [f.get('name', '') for f in files]
                    }
                
                if files:
                    st.success(f"✅ {len(files)}件のPDFファイルを取得しました")
                    
                    # ファイル一覧表示
                    with st.expander("📋 取得ファイル一覧", expanded=False):
                        for i, file_info in enumerate(files[:10], 1):  # 最初の10件のみ表示
                            st.text(f"{i}. {file_info.get('name', 'Unknown')}")
                        if len(files) > 10:
                            st.text(f"... 他 {len(files) - 10} 件")
                else:
                    st.warning("📭 指定フォルダにPDFファイルが見つかりませんでした")
                    
            except Exception as e:
                st.error(f"❌ Google Driveからのファイル取得に失敗: {e}")
                self.logger.error(f"Google Drive file fetch error: {e}")
        
        return files, metadata
    
    def _fetch_gdrive_files(self, google_drive, folder_id: str, max_files: int) -> Dict[str, Any]:
        """
        Google Driveからファイルを取得（OCRTestManagerから移植）
        """
        try:
            self.logger.info(f"フォルダID {folder_id} からPDFファイル一覧を取得中...")
            
            # フォルダ内のPDFファイルを検索（共有ドライブ対応）
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = google_drive.service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            all_files = results.get('files', [])
            self.logger.info(f"{len(all_files)}個のPDFファイルが見つかりました")
            
            # ファイル数制限適用
            if max_files != -1 and len(all_files) > max_files:
                files = all_files[:max_files]
                self.logger.info(f"最大ファイル数制限により{len(files)}件に絞り込み")
            else:
                files = all_files
            
            # フォルダ名を取得
            folder_name = self._get_folder_name(google_drive, folder_id)
            
            return {
                "files": files,
                "folder_name": folder_name,
                "total_found": len(all_files),
                "limited_to": len(files),
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Google Drive files fetch error: {e}")
            return {
                "files": [],
                "folder_name": "",
                "total_found": 0,
                "limited_to": 0,
                "error": str(e)
            }
    
    def _get_folder_name(self, google_drive, folder_id: str) -> str:
        """フォルダ名を取得"""
        try:
            folder_metadata = google_drive.service.files().get(
                fileId=folder_id,
                fields="name",
                supportsAllDrives=True
            ).execute()
            return folder_metadata.get('name', 'Unknown Folder')
        except Exception as e:
            self.logger.warning(f"フォルダ名取得エラー: {e}")
            return 'Unknown Folder'


def render_unified_file_selector(prefix_key: str) -> Tuple[List[Any], str, Dict[str, Any]]:
    """
    統合ファイル選択UIをレンダリング（関数インターフェース）
    
    Args:
        prefix_key: セッション状態のキープレフィックス
        
    Returns:
        Tuple[files, source_type, metadata]
    """
    selector = UnifiedFileSelector(prefix_key)
    return selector.render_file_selection_ui()