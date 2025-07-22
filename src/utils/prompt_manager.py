"""
プロンプト管理システム - JSONベースプロンプトローダー

JSON形式のプロンプトファイルを動的に読み込み、
変数置換、バリデーション、エラーハンドリングを提供する
統一プロンプト管理システム
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptValidationError(Exception):
    """プロンプト入力検証エラー"""
    pass

class PromptLoadError(Exception):
    """プロンプトファイル読み込みエラー"""
    pass

class PromptManager:
    """JSONプロンプトの動的ロード・管理クラス"""
    
    def __init__(self, prompts_dir: str = "./prompts"):
        """
        プロンプト管理インスタンスを初期化
        
        Args:
            prompts_dir: プロンプトJSONファイルのディレクトリパス
        """
        self.prompts_dir = Path(prompts_dir)
        self.loaded_prompts = {}
        self._prompt_cache = {}
        
        logger.info(f"PromptManager初期化: {self.prompts_dir}")
        
        # プロンプトディレクトリの存在確認
        if not self.prompts_dir.exists():
            logger.error(f"プロンプトディレクトリが存在しません: {self.prompts_dir}")
            raise PromptLoadError(f"プロンプトディレクトリが見つかりません: {self.prompts_dir}")
    
    def load_prompt(self, prompt_name: str, use_cache: bool = True) -> dict:
        """
        指定されたプロンプトJSONを読み込み
        
        Args:
            prompt_name: プロンプト名（.json拡張子なし）
            use_cache: キャッシュを使用するか
            
        Returns:
            プロンプトデータ辞書
            
        Raises:
            PromptLoadError: ファイルが見つからない、またはJSON形式が不正
        """
        # キャッシュチェック
        if use_cache and prompt_name in self._prompt_cache:
            logger.debug(f"キャッシュからプロンプト読み込み: {prompt_name}")
            return self._prompt_cache[prompt_name]
        
        file_path = self.prompts_dir / f"{prompt_name}.json"
        
        try:
            if not file_path.exists():
                raise PromptLoadError(f"プロンプトファイルが見つかりません: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)
            
            # 基本構造の検証
            self._validate_prompt_structure(prompt_data, prompt_name)
            
            # キャッシュに保存
            if use_cache:
                self._prompt_cache[prompt_name] = prompt_data
            
            logger.info(f"プロンプト読み込み成功: {prompt_name}")
            return prompt_data
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON形式エラー ({prompt_name}): {e}"
            logger.error(error_msg)
            raise PromptLoadError(error_msg)
        except Exception as e:
            error_msg = f"プロンプト読み込みエラー ({prompt_name}): {e}"
            logger.error(error_msg)
            raise PromptLoadError(error_msg)
    
    def render_prompt(self, prompt_name: str, variables: Dict[str, Any] = None) -> str:
        """
        変数を置換してプロンプト文字列を生成
        
        Args:
            prompt_name: プロンプト名
            variables: 置換変数の辞書
            
        Returns:
            変数置換済みプロンプト文字列
            
        Raises:
            PromptValidationError: 必須変数不足
            PromptLoadError: プロンプト読み込み失敗
        """
        if variables is None:
            variables = {}
        
        # プロンプトデータ読み込み
        prompt_data = self.load_prompt(prompt_name)
        
        # 入力変数の妥当性検証
        self.validate_inputs(prompt_name, variables)
        
        # プロンプトテンプレート取得
        template = prompt_data.get("prompt_template", "")
        
        if not template:
            raise PromptLoadError(f"prompt_templateが空です: {prompt_name}")
        
        # 変数置換処理
        rendered_prompt = self._substitute_variables(template, variables, prompt_data)
        
        logger.debug(f"プロンプト生成完了: {prompt_name}")
        return rendered_prompt
    
    def validate_inputs(self, prompt_name: str, inputs: Dict[str, Any]) -> bool:
        """
        入力変数の妥当性検証
        
        Args:
            prompt_name: プロンプト名
            inputs: 入力変数辞書
            
        Returns:
            検証成功の場合True
            
        Raises:
            PromptValidationError: 必須変数不足または形式不正
        """
        prompt_data = self.load_prompt(prompt_name)
        variables_spec = prompt_data.get("variables", {})
        
        # 必須変数チェック
        for var_name, var_spec in variables_spec.items():
            if var_spec.get("required", False):
                if var_name not in inputs:
                    error_msg = f"必須変数 '{var_name}' が未提供: {prompt_name}"
                    logger.error(error_msg)
                    raise PromptValidationError(error_msg)
                
                # 値の存在チェック
                value = inputs[var_name]
                if value is None or (isinstance(value, str) and not value.strip()):
                    error_msg = f"必須変数 '{var_name}' の値が空です: {prompt_name}"
                    logger.error(error_msg)
                    raise PromptValidationError(error_msg)
        
        # 型チェック（基本的な検証）
        for var_name, value in inputs.items():
            if var_name in variables_spec:
                expected_type = variables_spec[var_name].get("type", "string")
                if not self._validate_variable_type(value, expected_type):
                    error_msg = f"変数 '{var_name}' の型が不正です。期待型: {expected_type}, 実際の型: {type(value).__name__}"
                    logger.debug(error_msg)  # WARNING → DEBUG に変更（非致命的エラー）
        
        logger.debug(f"入力検証成功: {prompt_name}")
        return True
    
    def get_prompt_info(self, prompt_name: str) -> Dict[str, Any]:
        """
        プロンプトの基本情報を取得
        
        Args:
            prompt_name: プロンプト名
            
        Returns:
            プロンプト情報辞書
        """
        prompt_data = self.load_prompt(prompt_name)
        
        return {
            "name": prompt_data.get("name", prompt_name),
            "version": prompt_data.get("version", "1.0"),
            "description": prompt_data.get("description", ""),
            "confidence_threshold": prompt_data.get("confidence_threshold", 0.80),
            "priority": prompt_data.get("priority", "medium"),
            "variables": prompt_data.get("variables", {}),
            "test_cases_count": len(prompt_data.get("test_cases", []))
        }
    
    def list_available_prompts(self) -> List[str]:
        """
        利用可能なプロンプトファイル一覧を取得
        
        Returns:
            プロンプト名のリスト
        """
        try:
            prompt_files = list(self.prompts_dir.glob("*.json"))
            prompt_names = [f.stem for f in prompt_files]
            logger.info(f"利用可能プロンプト: {prompt_names}")
            return sorted(prompt_names)
        except Exception as e:
            logger.error(f"プロンプト一覧取得エラー: {e}")
            return []
    
    def run_test_case(self, prompt_name: str, test_case_index: int = 0) -> Dict[str, Any]:
        """
        プロンプトのテストケースを実行
        
        Args:
            prompt_name: プロンプト名
            test_case_index: テストケース番号
            
        Returns:
            テスト実行結果
        """
        prompt_data = self.load_prompt(prompt_name)
        test_cases = prompt_data.get("test_cases", [])
        
        if test_case_index >= len(test_cases):
            raise PromptValidationError(f"テストケース {test_case_index} が存在しません")
        
        test_case = test_cases[test_case_index]
        test_input = test_case.get("input", {})
        
        try:
            # テスト用プロンプト生成
            rendered_prompt = self.render_prompt(prompt_name, test_input)
            
            return {
                "success": True,
                "test_name": test_case.get("name", f"Test {test_case_index}"),
                "rendered_prompt": rendered_prompt,
                "input_data": test_input,
                "expected_output": test_case.get("expected_output", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "test_name": test_case.get("name", f"Test {test_case_index}"),
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_cache(self):
        """プロンプトキャッシュをクリア"""
        self._prompt_cache.clear()
        logger.info("プロンプトキャッシュをクリアしました")
    
    def _validate_prompt_structure(self, prompt_data: dict, prompt_name: str):
        """プロンプトデータの基本構造を検証"""
        required_fields = ["name", "prompt_template"]
        
        for field in required_fields:
            if field not in prompt_data:
                raise PromptLoadError(f"必須フィールド '{field}' が見つかりません: {prompt_name}")
    
    def _substitute_variables(self, template: str, variables: Dict[str, Any], prompt_data: dict) -> str:
        """変数置換処理"""
        import json
        result = template
        variables_spec = prompt_data.get("variables", {})
        
        # 基本変数置換（{variable_name} 形式）
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in result:
                # 変数仕様を確認して適切な形式に変換
                var_spec = variables_spec.get(var_name, {})
                expected_type = var_spec.get("type", "string")
                
                if expected_type == "string" and isinstance(var_value, (list, dict)):
                    # 配列や辞書の場合は JSON 文字列に変換
                    formatted_value = json.dumps(var_value, ensure_ascii=False)
                else:
                    formatted_value = str(var_value)
                
                result = result.replace(placeholder, formatted_value)
        
        # デフォルト値の適用
        for var_name, var_spec in variables_spec.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in result and var_name not in variables:
                default_value = var_spec.get("default", "")
                result = result.replace(placeholder, str(default_value))
        
        return result
    
    def _validate_variable_type(self, value: Any, expected_type: str) -> bool:
        """変数の型を検証"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "image":
            return isinstance(value, (str, bytes))  # Base64文字列またはバイナリ
        else:
            return True  # 不明な型は通す


# グローバルプロンプトマネージャーインスタンス
_global_prompt_manager = None

def get_prompt_manager(prompts_dir: str = "./prompts") -> PromptManager:
    """
    グローバルプロンプトマネージャーインスタンスを取得
    
    Args:
        prompts_dir: プロンプトディレクトリ（初回のみ使用）
        
    Returns:
        PromptManagerインスタンス
    """
    global _global_prompt_manager
    
    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager(prompts_dir)
    
    return _global_prompt_manager

def render_prompt_simple(prompt_name: str, variables: Dict[str, Any] = None) -> str:
    """
    シンプルなプロンプト生成関数
    
    Args:
        prompt_name: プロンプト名
        variables: 置換変数
        
    Returns:
        生成されたプロンプト文字列
    """
    manager = get_prompt_manager()
    return manager.render_prompt(prompt_name, variables or {}) 