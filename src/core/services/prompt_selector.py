"""
プロンプト自動選択システム
処理モードに応じて最適なプロンプトを自動選択
"""

from typing import Optional, Dict, Any
from core.models.workflow_models import ProcessingMode
from utils.log_config import get_logger

logger = get_logger(__name__)

class PromptSelector:
    """プロンプト自動選択クラス"""
    
    def __init__(self, prompt_manager):
        """
        Args:
            prompt_manager: UnifiedPromptManagerインスタンス
        """
        self.prompt_manager = prompt_manager
        self.mode_prompt_mapping = {
            ProcessingMode.UPLOAD: "invoice_extractor_prompt",
            ProcessingMode.OCR_TEST: "invoice_extractor_prompt", 
            ProcessingMode.VALIDATION: "invoice_extractor_prompt",
            ProcessingMode.BATCH: "invoice_extractor_prompt"
        }
        
    def get_recommended_prompt(self, mode: ProcessingMode) -> Optional[str]:
        """
        処理モードに基づいて推奨プロンプトを取得
        
        Args:
            mode: 処理モード
            
        Returns:
            推奨プロンプトキー
        """
        try:
            # モードに応じたプロンプト選択
            if mode == ProcessingMode.UPLOAD:
                return self._get_upload_prompt()
            elif mode == ProcessingMode.OCR_TEST:
                return self._get_ocr_test_prompt()
            elif mode == ProcessingMode.VALIDATION:
                return self._get_validation_prompt()
            elif mode == ProcessingMode.BATCH:
                return self._get_batch_prompt()
            else:
                logger.warning(f"未対応の処理モード: {mode}")
                return self._get_default_prompt()
                
        except Exception as e:
            logger.error(f"プロンプト選択エラー: {e}")
            return self._get_default_prompt()
    
    def _get_upload_prompt(self) -> Optional[str]:
        """本番アップロード用プロンプト取得"""
        # 本番処理用の高精度プロンプト
        candidates = [
            "invoice_extractor_prompt",
            "integrated_matcher_prompt"
        ]
        return self._select_best_prompt(candidates)
    
    def _get_ocr_test_prompt(self) -> Optional[str]:
        """OCRテスト用プロンプト取得"""
        # テスト用の標準プロンプト
        candidates = [
            "invoice_extractor_prompt",
            "master_matcher_prompt"
        ]
        return self._select_best_prompt(candidates)
    
    def _get_validation_prompt(self) -> Optional[str]:
        """検証用プロンプト取得"""
        # 検証専用プロンプト
        candidates = [
            "master_matcher_prompt",
            "invoice_extractor_prompt"
        ]
        return self._select_best_prompt(candidates)
    
    def _get_batch_prompt(self) -> Optional[str]:
        """バッチ処理用プロンプト取得"""
        # バッチ処理効率重視プロンプト
        candidates = [
            "invoice_extractor_prompt",
            "integrated_matcher_prompt"
        ]
        return self._select_best_prompt(candidates)
    
    def _get_default_prompt(self) -> Optional[str]:
        """デフォルトプロンプト取得"""
        return "invoice_extractor_prompt"
    
    def _select_best_prompt(self, candidates: list) -> Optional[str]:
        """
        候補から最適なプロンプトを選択
        
        Args:
            candidates: プロンプト候補リスト
            
        Returns:
            選択されたプロンプトキー
        """
        for candidate in candidates:
            if self.prompt_manager.has_prompt(candidate):
                logger.info(f"プロンプト選択: {candidate}")
                return candidate
        
        # 候補がない場合はデフォルト
        logger.warning("候補プロンプトが見つからないため、デフォルトを使用")
        return self._get_default_prompt()
    
    def get_prompt_compatibility_score(self, prompt_key: str, mode: ProcessingMode) -> float:
        """
        プロンプトと処理モードの互換性スコア計算
        
        Args:
            prompt_key: プロンプトキー
            mode: 処理モード
            
        Returns:
            互換性スコア (0.0-1.0)
        """
        try:
            if not self.prompt_manager.has_prompt(prompt_key):
                return 0.0
            
            # モード別スコア計算
            if mode == ProcessingMode.UPLOAD:
                return self._calculate_upload_compatibility(prompt_key)
            elif mode == ProcessingMode.OCR_TEST:
                return self._calculate_test_compatibility(prompt_key)
            elif mode == ProcessingMode.VALIDATION:
                return self._calculate_validation_compatibility(prompt_key)
            elif mode == ProcessingMode.BATCH:
                return self._calculate_batch_compatibility(prompt_key)
            else:
                return 0.5  # 中程度の互換性
                
        except Exception as e:
            logger.error(f"互換性スコア計算エラー: {e}")
            return 0.0
    
    def _calculate_upload_compatibility(self, prompt_key: str) -> float:
        """本番アップロード互換性スコア"""
        score_map = {
            "invoice_extractor_prompt": 1.0,  # 最適
            "integrated_matcher_prompt": 0.9,
            "master_matcher_prompt": 0.7
        }
        return score_map.get(prompt_key, 0.5)
    
    def _calculate_test_compatibility(self, prompt_key: str) -> float:
        """OCRテスト互換性スコア"""
        score_map = {
            "invoice_extractor_prompt": 1.0,  # 最適
            "master_matcher_prompt": 0.8,
            "integrated_matcher_prompt": 0.7
        }
        return score_map.get(prompt_key, 0.5)
    
    def _calculate_validation_compatibility(self, prompt_key: str) -> float:
        """検証処理互換性スコア"""
        score_map = {
            "master_matcher_prompt": 1.0,  # 最適
            "invoice_extractor_prompt": 0.9,
            "integrated_matcher_prompt": 0.8
        }
        return score_map.get(prompt_key, 0.5)
    
    def _calculate_batch_compatibility(self, prompt_key: str) -> float:
        """バッチ処理互換性スコア"""
        score_map = {
            "invoice_extractor_prompt": 1.0,  # 最適
            "integrated_matcher_prompt": 0.9,
            "master_matcher_prompt": 0.7
        }
        return score_map.get(prompt_key, 0.5) 