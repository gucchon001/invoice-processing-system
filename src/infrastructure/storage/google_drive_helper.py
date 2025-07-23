"""
請求書処理自動化システム - Google Drive APIヘルパー

このモジュールはGoogle Drive APIとの連携、ファイルアップロード、
フォルダ管理機能を提供します。
"""

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import logging
from typing import Dict, Any, Optional, List
import io
import json
from pathlib import Path

# ロガー設定
logger = logging.getLogger(__name__)


class GoogleDriveManager:
    """Google Drive API管理クラス"""
    
    def __init__(self):
        """Google Drive API接続を初期化"""
        try:
            # サービスアカウント認証情報を取得
            service_account_info = {
                "type": st.secrets["google_drive"]["type"],
                "project_id": st.secrets["google_drive"]["project_id"],
                "private_key_id": st.secrets["google_drive"]["private_key_id"],
                "private_key": st.secrets["google_drive"]["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["google_drive"]["client_email"],
                "client_id": st.secrets["google_drive"]["client_id"],
                "auth_uri": st.secrets["google_drive"]["auth_uri"],
                "token_uri": st.secrets["google_drive"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["google_drive"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"]
            }
            
            # スコープ設定
            scopes = ['https://www.googleapis.com/auth/drive']
            
            # 認証情報作成
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            
            # Drive APIサービス作成
            self.service = build('drive', 'v3', credentials=credentials)
            
            # デフォルトフォルダID（設定から取得、なければNone）
            self.default_folder_id = st.secrets.get("google_drive", {}).get("default_folder_id")
            
            logger.info("Google Drive API接続初期化完了")
            
        except KeyError as e:
            logger.error(f"Google Drive API設定が不完全です: {e}")
            st.error(f"Google Drive API設定エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"Google Drive API接続でエラー: {e}")
            st.error(f"Google Drive API接続エラー: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Google Drive API接続をテストする"""
        try:
            # 簡単な権限テスト - aboutを取得
            about = self.service.about().get(fields="user, storageQuota").execute()
            
            if about and 'user' in about:
                logger.info(f"Google Drive API接続テスト成功: {about['user']['emailAddress']}")
                return True
            else:
                logger.error("Google Drive APIから適切な応答がありません")
                return False
                
        except Exception as e:
            logger.error(f"Google Drive API接続テストでエラー: {e}")
            return False
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """フォルダを作成する（共有ドライブ対応）
        
        Args:
            folder_name: 作成するフォルダ名
            parent_folder_id: 親フォルダID（Noneの場合はルート）
            
        Returns:
            作成されたフォルダのID、失敗時はNone
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            # 共有ドライブ対応: supportsAllDrives=true を追加
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"フォルダ作成成功（共有ドライブ）: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"フォルダ作成でエラー: {e}")
            return None
    
    def upload_file(self, file_content: bytes, filename: str, 
                   folder_id: Optional[str] = None, mime_type: str = 'application/pdf') -> Optional[Dict[str, str]]:
        """ファイルをGoogle Drive（共有ドライブ対応）にアップロードする
        
        Args:
            file_content: ファイルの内容（バイト）
            filename: ファイル名
            folder_id: アップロード先フォルダID（Noneの場合はdefault_folder_id使用）
            mime_type: ファイルのMIMEタイプ
            
        Returns:
            アップロード結果辞書 {'file_id': str, 'file_url': str} または None
        """
        import time
        import signal
        from contextlib import contextmanager
        
        @contextmanager
        def timeout_handler(seconds):
            """タイムアウトハンドラー"""
            def timeout_signal(signum, frame):
                raise TimeoutError(f"Google Drive APIがタイムアウトしました ({seconds}秒)")
            
            # Windowsではsignalが制限されているため、try-except使用
            try:
                if hasattr(signal, 'SIGALRM'):
                    old_handler = signal.signal(signal.SIGALRM, timeout_signal)
                    signal.alarm(seconds)
                yield
            except Exception:
                # Windows環境ではタイムアウト制御なしで続行
                yield
            finally:
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
        
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Google Driveアップロード開始: {filename} ({len(file_content)} bytes)")
            
            # フォルダIDの決定
            target_folder_id = folder_id or self.default_folder_id
            logger.info(f"📁 アップロード先フォルダID: {target_folder_id}")
            
            # ファイルメタデータ
            file_metadata = {'name': filename}
            if target_folder_id:
                file_metadata['parents'] = [target_folder_id]
            
            logger.info(f"📋 ファイルメタデータ: {file_metadata}")
            
            # ファイルコンテンツ
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type,
                resumable=True
            )
            
            logger.info(f"📤 メディアアップロード準備完了: {mime_type}")
            
            # タイムアウト制御付きでAPI呼び出し
            with timeout_handler(30):  # 30秒タイムアウト
                logger.info("🌐 Google Drive API呼び出し開始...")
                
                # 共有ドライブ対応: supportsAllDrives=true を追加
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                
                logger.info("🌐 Google Drive API呼び出し完了")
            
            file_id = file.get('id')
            
            if not file_id:
                raise Exception("Google Drive APIからファイルIDが取得できませんでした")
            
            # ファイルURLを生成
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ ファイルアップロード成功（共有ドライブ）: {filename}")
            logger.info(f"📊 アップロード詳細: ID={file_id}, 時間={elapsed_time:.2f}秒")
            
            return {
                'file_id': file_id,
                'file_url': file_url,
                'filename': filename
            }
            
        except TimeoutError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Google Drive APIタイムアウト: {e} (経過時間: {elapsed_time:.2f}秒)"
            logger.error(f"⏰ {error_msg}")
            raise Exception(error_msg)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"ファイルアップロードでエラー: {e} (経過時間: {elapsed_time:.2f}秒)"
            logger.error(f"❌ {error_msg}")
            logger.error(f"🔍 デバッグ情報: ファイル名={filename}, サイズ={len(file_content)}bytes, MIME={mime_type}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """ファイル情報を取得する（共有ドライブ対応）
        
        Args:
            file_id: ファイルID
            
        Returns:
            ファイル情報辞書またはNone
        """
        try:
            # 共有ドライブ対応: supportsAllDrives=true を追加
            file_info = self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,size,createdTime,modifiedTime,webViewLink',
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"ファイル情報取得成功（共有ドライブ）: {file_info.get('name')}")
            return file_info
            
        except Exception as e:
            logger.error(f"ファイル情報取得でエラー: {e}")
            return None
    
    def list_files(self, folder_id: Optional[str] = None, 
                  file_type: Optional[str] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """ファイル一覧を取得する（共有ドライブ対応）
        
        Args:
            folder_id: 検索対象フォルダID（Noneの場合は全体）
            file_type: ファイルタイプフィルタ（例: 'application/pdf'）
            max_results: 最大取得件数
            
        Returns:
            ファイル情報のリスト
        """
        try:
            # クエリ構築
            query_parts = []
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            if file_type:
                query_parts.append(f"mimeType='{file_type}'")
            
            # ゴミ箱以外
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts) if query_parts else "trashed=false"
            
            # 共有ドライブ対応: includeItemsFromAllDrives=true, supportsAllDrives=true を追加
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id,name,mimeType,size,createdTime,webViewLink)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"ファイル一覧取得成功（共有ドライブ）: {len(files)}件")
            return files
            
        except Exception as e:
            logger.error(f"ファイル一覧取得でエラー: {e}")
            return []
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """ファイルをダウンロードする（共有ドライブ対応）
        
        Args:
            file_id: ダウンロードするファイルID
            
        Returns:
            ファイルの内容（バイト）またはNone
        """
        try:
            import googleapiclient.http
            
            # ファイルのメディアコンテンツを取得
            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
            
            file_content = io.BytesIO()
            downloader = googleapiclient.http.MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            file_content.seek(0)
            content = file_content.read()
            
            logger.info(f"ファイルダウンロード成功（共有ドライブ）: {file_id} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"ファイルダウンロードでエラー: {e}")
            return None

    def delete_file(self, file_id: str) -> bool:
        """ファイルを削除する（共有ドライブ対応）
        
        Args:
            file_id: 削除するファイルID
            
        Returns:
            削除成功時True、失敗時False
        """
        try:
            # 共有ドライブ対応: supportsAllDrives=true を追加
            self.service.files().delete(
                fileId=file_id,
                supportsAllDrives=True
            ).execute()
            logger.info(f"ファイル削除成功（共有ドライブ）: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"ファイル削除でエラー: {e}")
            return False


# グローバル関数（Streamlitアプリから使用）
@st.cache_resource
def get_google_drive():
    """Google Drive APIマネージャーを取得（キャッシュ付き）"""
    return GoogleDriveManager()


def test_google_drive_connection() -> bool:
    """Google Drive API接続テスト"""
    try:
        drive_manager = get_google_drive()
        return drive_manager.test_connection()
    except Exception as e:
        st.error(f"Google Drive接続テスト中にエラー: {e}")
        return False


def upload_pdf_to_drive(file_content: bytes, filename: str) -> Optional[Dict[str, str]]:
    """PDFファイルをGoogle Driveにアップロード
    
    Args:
        file_content: PDFファイルの内容
        filename: ファイル名
        
    Returns:
        アップロード結果またはNone
    """
    try:
        drive_manager = get_google_drive()
        return drive_manager.upload_file(
            file_content=file_content,
            filename=filename,
            mime_type='application/pdf'
        )
    except Exception as e:
        st.error(f"PDFアップロード中にエラー: {e}")
        return None


def get_drive_files_list(folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Google Driveのファイル一覧を取得
    
    Args:
        folder_id: 対象フォルダID
        
    Returns:
        ファイル一覧
    """
    try:
        drive_manager = get_google_drive()
        return drive_manager.list_files(folder_id=folder_id, file_type='application/pdf')
    except Exception as e:
        st.error(f"ファイル一覧取得中にエラー: {e}")
        return [] 