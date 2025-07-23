"""
統一プロンプト管理システム

OCRテスト機能とアップロード機能で共通利用可能な
プロンプト管理・選択システムを提供します。
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from core.models.workflow_models import ProcessingMode

logger = logging.getLogger(__name__)

class UnifiedPromptManager:
    """統一プロンプト管理システム"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        プロンプト管理システムの初期化
        
        Args:
            prompts_dir: プロンプトファイルディレクトリ
        """
        self.prompts_dir = Path(prompts_dir)
        self.available_prompts = {}
        self.default_prompt = None
        self._load_available_prompts()
    
    def _load_available_prompts(self) -> None:
        """利用可能なプロンプトファイルを読み込み"""
        try:
            if not self.prompts_dir.exists():
                logger.warning(f"プロンプトディレクトリが存在しません: {self.prompts_dir}")
                return
            
            # JSON形式のプロンプトファイルを検索
            for prompt_file in self.prompts_dir.glob("*.json"):
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                    
                    # プロンプトメタデータの検証
                    if self._validate_prompt_structure(prompt_data):
                        # 既存形式の場合はメタデータを変換
                        if 'prompt_template' in prompt_data:
                            metadata = {
                                'name': prompt_data.get('name', prompt_file.stem),
                                'description': prompt_data.get('description', ''),
                                'version': prompt_data.get('version', '1.0'),
                                'type': 'invoice',  # 既存プロンプトは請求書用とみなす
                                'last_modified': '',
                                'is_default': False,
                                'supported_operations': ['upload', 'ocr_test', 'batch']
                            }
                        else:
                            metadata = prompt_data.get('metadata', {})
                        
                        self.available_prompts[prompt_file.stem] = {
                            'file_path': str(prompt_file),
                            'data': prompt_data,
                            'metadata': metadata
                        }
                        
                        # デフォルトプロンプトの設定
                        if metadata.get('is_default', False):
                            self.default_prompt = prompt_file.stem
                        
                        # 請求書抽出プロンプトを優先的にデフォルトに設定
                        if prompt_file.stem == 'invoice_extractor_prompt':
                            self.default_prompt = prompt_file.stem
                            logger.info(f"請求書抽出プロンプトをデフォルトに設定: {prompt_file.stem}")
                    
                except Exception as e:
                    logger.error(f"プロンプトファイル読み込みエラー {prompt_file}: {e}")
            
            logger.info(f"プロンプト読み込み完了: {len(self.available_prompts)}個")
            
        except Exception as e:
            logger.error(f"プロンプト初期化エラー: {e}")
    
    def _validate_prompt_structure(self, prompt_data: Dict[str, Any]) -> bool:
        """プロンプト構造の検証（既存形式対応）"""
        # 新形式の検証
        if 'system_prompt' in prompt_data and 'user_prompt' in prompt_data and 'metadata' in prompt_data:
            metadata = prompt_data.get('metadata', {})
            if 'name' not in metadata or 'description' not in metadata:
                logger.warning("メタデータにnameまたはdescriptionが不足")
                return False
            return True
        
        # 既存形式の検証（legacy support）
        if 'prompt_template' in prompt_data and 'name' in prompt_data and 'description' in prompt_data:
            logger.info(f"既存形式のプロンプトファイルを検出: {prompt_data.get('name', '')}")
            return True
        
        logger.warning("必須フィールドが不足: system_prompt/user_prompt/metadata または prompt_template/name/description")
        return False
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """利用可能なプロンプトリストを取得"""
        return {
            key: {
                'name': data['metadata'].get('name', key),
                'description': data['metadata'].get('description', ''),
                'version': data['metadata'].get('version', '1.0'),
                'type': data['metadata'].get('type', 'general'),
                'last_modified': data['metadata'].get('last_modified', ''),
                'is_default': data['metadata'].get('is_default', False)
            }
            for key, data in self.available_prompts.items()
        }
    
    def has_prompt(self, prompt_key: str) -> bool:
        """
        指定されたプロンプトキーが存在するかチェック
        
        Args:
            prompt_key: チェックするプロンプトキー
            
        Returns:
            存在する場合True、存在しない場合False
        """
        return prompt_key in self.available_prompts
    
    def get_prompt_by_key(self, prompt_key: str) -> Optional[Dict[str, Any]]:
        """プロンプトキーによる取得"""
        if prompt_key in self.available_prompts:
            return self.available_prompts[prompt_key]['data']
        return None
    
    def get_default_prompt(self) -> Optional[Dict[str, Any]]:
        """デフォルトプロンプトの取得"""
        if self.default_prompt and self.default_prompt in self.available_prompts:
            return self.available_prompts[self.default_prompt]['data']
        
        # デフォルトが設定されていない場合、最初のプロンプトを返す
        if self.available_prompts:
            first_key = next(iter(self.available_prompts))
            # 最初のプロンプトをデフォルトに設定
            if not self.default_prompt:
                self.default_prompt = first_key
                logger.info(f"デフォルトプロンプトを自動設定: {first_key}")
            return self.available_prompts[first_key]['data']
        
        return None
    
    def get_prompts_by_type(self, prompt_type: str) -> Dict[str, Dict[str, Any]]:
        """タイプ別プロンプト取得"""
        filtered_prompts = {}
        
        for key, data in self.available_prompts.items():
            if data['metadata'].get('type') == prompt_type:
                filtered_prompts[key] = data['data']
        
        return filtered_prompts
    
    def format_prompt_for_gemini(self, prompt_key: str, 
                               context_data: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        Gemini用にプロンプトをフォーマット（既存形式対応）
        
        Args:
            prompt_key: プロンプトキー
            context_data: 動的コンテキストデータ
            
        Returns:
            (system_prompt, user_prompt) のタプル
        """
        prompt_data = self.get_prompt_by_key(prompt_key)
        if not prompt_data:
            logger.error(f"プロンプトが見つかりません: {prompt_key}")
            return "", ""
        
        try:
            # 新形式の場合
            if 'system_prompt' in prompt_data and 'user_prompt' in prompt_data:
                system_prompt = prompt_data['system_prompt']
                user_prompt = prompt_data['user_prompt']
            
            # 既存形式の場合はprompt_templateを使用
            elif 'prompt_template' in prompt_data:
                prompt_template = prompt_data['prompt_template']
                
                # 動的コンテキストの置換
                if context_data:
                    prompt_template = self._replace_placeholders(prompt_template, context_data)
                
                # 既存形式では全体をuser_promptとして扱い、system_promptは基本的な指示
                system_prompt = "あなたは請求書処理の専門家です。提供されたPDFファイルから正確に情報を抽出してください。"
                user_prompt = prompt_template
            
            else:
                logger.error(f"プロンプト形式が不正です: {prompt_key}")
                return "", ""
            
            # 動的コンテキストの置換（新形式の場合）
            if context_data and 'system_prompt' in prompt_data:
                system_prompt = self._replace_placeholders(system_prompt, context_data)
                user_prompt = self._replace_placeholders(user_prompt, context_data)
            
            return system_prompt, user_prompt
            
        except Exception as e:
            logger.error(f"プロンプトフォーマットエラー: {e}")
            return "", ""
    
    def _replace_placeholders(self, text: str, context_data: Dict[str, Any]) -> str:
        """プレースホルダーの置換"""
        for key, value in context_data.items():
            placeholder = f"{{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        
        return text
    
    def validate_prompt_compatibility(self, prompt_key: str, 
                                    operation_type: str) -> Tuple[bool, List[str]]:
        """
        プロンプトの互換性検証
        
        Args:
            prompt_key: プロンプトキー
            operation_type: 操作タイプ（'ocr_test', 'upload', 'batch'）
            
        Returns:
            (is_compatible, warnings) のタプル
        """
        prompt_data = self.get_prompt_by_key(prompt_key)
        if not prompt_data:
            return False, [f"プロンプトが見つかりません: {prompt_key}"]
        
        warnings = []
        metadata = prompt_data.get('metadata', {})
        
        # 対応操作タイプのチェック
        supported_operations = metadata.get('supported_operations', [])
        if supported_operations and operation_type not in supported_operations:
            warnings.append(f"操作タイプ '{operation_type}' は推奨されていません")
        
        # バージョン互換性チェック
        min_version = metadata.get('min_system_version')
        if min_version:
            warnings.append(f"システムバージョン {min_version} 以上が必要です")
        
        # 警告があっても基本的には使用可能
        return True, warnings
    
    def get_prompt_statistics(self) -> Dict[str, Any]:
        """プロンプト統計情報の取得"""
        stats = {
            'total_prompts': len(self.available_prompts),
            'default_prompt': self.default_prompt,
            'types': {},
            'versions': {},
            'last_loaded': None
        }
        
        for key, data in self.available_prompts.items():
            metadata = data['metadata']
            
            # タイプ別統計
            prompt_type = metadata.get('type', 'unknown')
            stats['types'][prompt_type] = stats['types'].get(prompt_type, 0) + 1
            
            # バージョン別統計
            version = metadata.get('version', 'unknown')
            stats['versions'][version] = stats['versions'].get(version, 0) + 1
        
        return stats

class PromptSelector:
    """プロンプト選択UI支援クラス"""
    
    def __init__(self, prompt_manager: UnifiedPromptManager):
        self.prompt_manager = prompt_manager
    
    def create_selection_options(self, filter_type: str = None) -> List[Tuple[str, str]]:
        """
        選択肢のオプション作成
        
        Args:
            filter_type: フィルタータイプ
            
        Returns:
            [(display_name, prompt_key), ...] のリスト
        """
        options = []
        available_prompts = self.prompt_manager.get_available_prompts()
        
        for key, metadata in available_prompts.items():
            # タイプフィルタリング
            if filter_type and metadata.get('type') != filter_type:
                continue
            
            # 表示名の作成
            display_name = f"{metadata['name']}"
            if metadata.get('is_default'):
                display_name += " (デフォルト)"
            
            description = metadata.get('description', '')
            if description:
                display_name += f" - {description[:50]}"
                if len(description) > 50:
                    display_name += "..."
            
            options.append((display_name, key))
        
        # デフォルトプロンプトを先頭に
        options.sort(key=lambda x: (not self._is_default_prompt(x[1]), x[0]))
        
        return options
    
    def _is_default_prompt(self, prompt_key: str) -> bool:
        """デフォルトプロンプトかどうかの判定"""
        prompt_data = self.prompt_manager.get_prompt_by_key(prompt_key)
        if prompt_data:
            return prompt_data.get('metadata', {}).get('is_default', False)
        return False
    
    def get_recommended_prompt(self, operation_type: str) -> Optional[str]:
        """
        操作タイプに基づく推奨プロンプトの取得
        
        Args:
            operation_type: 操作タイプ
            
        Returns:
            推奨プロンプトキー
        """
        # フロー別の特定プロンプト選択
        if operation_type in [ProcessingMode.UPLOAD, ProcessingMode.BATCH, ProcessingMode.OCR_TEST]:
            # 請求書データ抽出の場合は必ずinvoice_extractor_promptを使用
            if 'invoice_extractor_prompt' in self.prompt_manager.available_prompts:
                logger.info(f"フロー別自動選択: {operation_type} -> invoice_extractor_prompt")
                return 'invoice_extractor_prompt'
        
        # 企業名照合の場合
        if operation_type == 'company_matching':
            if 'master_matcher_prompt' in self.prompt_manager.available_prompts:
                logger.info(f"フロー別自動選択: {operation_type} -> master_matcher_prompt")
                return 'master_matcher_prompt'
        
        # 統合照合の場合
        if operation_type == 'integrated_matching':
            if 'integrated_matcher_prompt' in self.prompt_manager.available_prompts:
                logger.info(f"フロー別自動選択: {operation_type} -> integrated_matcher_prompt")
                return 'integrated_matcher_prompt'
        
        available_prompts = self.prompt_manager.get_available_prompts()
        
        # 対応操作タイプが明示されているプロンプトを優先
        for key, metadata in available_prompts.items():
            prompt_data = self.prompt_manager.get_prompt_by_key(key)
            if prompt_data:
                supported_ops = prompt_data.get('metadata', {}).get('supported_operations', [])
                if operation_type in supported_ops:
                    logger.info(f"メタデータベース選択: {operation_type} -> {key}")
                    return key
        
        # デフォルトプロンプトを返す（最後の手段）
        logger.warning(f"デフォルトプロンプトを使用: {operation_type} -> {self.prompt_manager.default_prompt}")
        return self.prompt_manager.default_prompt 