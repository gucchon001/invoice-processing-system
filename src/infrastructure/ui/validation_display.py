"""
統一された請求書検証結果表示システム

OCRテスト機能のUI表示ロジックをベースに、
請求書アップロード機能でも使用可能な共通UI/UXシステムを提供します。
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ValidationDisplay:
    """検証結果の統一表示システム"""
    
    def __init__(self):
        """表示システムの初期化"""
        self.display_config = {
            'show_details': True,
            'show_categories': True,
            'show_summary': True,
            'color_coding': True
        }
    
    def display_validation_results(self, validation: Dict[str, Any], 
                                 title: str = "検証結果",
                                 expanded: bool = True) -> None:
        """
        検証結果の統合表示
        
        Args:
            validation: 検証結果辞書
            title: 表示タイトル
            expanded: 初期展開状態
        """
        try:
            with st.expander(f"📋 {title}", expanded=expanded):
                # サマリー表示
                self._display_validation_summary(validation)
                
                # エラー・警告の詳細表示
                if validation.get("errors") or validation.get("warnings"):
                    self._display_issues_details(validation)
                
                # カテゴリ別分析表示
                if self.display_config['show_categories']:
                    self._display_category_analysis(validation)
                
                # 検証設定情報
                if self.display_config['show_details']:
                    self._display_validation_config(validation)
                    
        except Exception as e:
            logger.error(f"検証結果表示中にエラーが発生しました: {e}")
            st.error(f"表示エラー: {str(e)}")
    
    def _display_validation_summary(self, validation: Dict[str, Any]) -> None:
        """検証サマリーの表示"""
        summary = validation.get("validation_summary", {})
        is_valid = validation.get("is_valid", False)
        
        # ステータス表示
        if is_valid:
            st.success("✅ 検証完了：データに問題はありません")
        else:
            st.error("❌ 検証エラー：データに問題があります")
        
        # 数値サマリー
        col1, col2, col3 = st.columns(3)
        with col1:
            error_count = summary.get("critical_issues", 0)
            st.metric("エラー", error_count, 
                     delta=None if error_count == 0 else f"-{error_count}")
        
        with col2:
            warning_count = summary.get("warnings", 0)
            st.metric("警告", warning_count,
                     delta=None if warning_count == 0 else f"-{warning_count}")
        
        with col3:
            total_issues = summary.get("total_issues", 0)
            st.metric("総課題数", total_issues)
    
    def _display_issues_details(self, validation: Dict[str, Any]) -> None:
        """エラー・警告の詳細表示"""
        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        
        if errors:
            st.subheader("🚨 エラー詳細")
            for i, error in enumerate(errors, 1):
                st.error(f"{i}. {error}")
        
        if warnings:
            st.subheader("⚠️ 警告詳細")
            for i, warning in enumerate(warnings, 1):
                st.warning(f"{i}. {warning}")
    
    def _display_category_analysis(self, validation: Dict[str, Any]) -> None:
        """カテゴリ別分析の表示"""
        categories = validation.get("error_categories", {})
        
        if not any(categories.values()):
            return
        
        st.subheader("📊 課題カテゴリ別分析")
        
        # カテゴリ別課題数の集計
        category_data = []
        category_names = {
            "required_fields": "必須フィールド",
            "data_format": "データフォーマット",
            "business_logic": "ビジネスロジック"
        }
        
        for category, issues in categories.items():
            if issues:
                category_data.append({
                    "カテゴリ": category_names.get(category, category),
                    "課題数": len(issues),
                    "内容": " / ".join(issues[:3]) + ("..." if len(issues) > 3 else "")
                })
        
        if category_data:
            df = pd.DataFrame(category_data)
            st.dataframe(df, use_container_width=True)
    
    def _display_validation_config(self, validation: Dict[str, Any]) -> None:
        """検証設定情報の表示"""
        with st.expander("🔧 検証設定詳細", expanded=False):
            st.info("""
            **実行された検証項目:**
            - ✅ 必須フィールド検証
            - ✅ データ型・フォーマット検証
            - ✅ 金額検証（外貨取引対応）
            - ✅ 日付検証
            - ✅ 外貨取引チェック
            - ✅ 明細整合性チェック
            """)
    
    def display_progress_indicator(self, current_step: int, total_steps: int, 
                                 step_name: str = "") -> None:
        """進捗インジケーターの表示"""
        progress = current_step / total_steps
        st.progress(progress, text=f"進捗: {current_step}/{total_steps} {step_name}")
    
    def display_file_info(self, file_info: Dict[str, Any]) -> None:
        """ファイル情報の表示"""
        info_text = f"""
        **ファイル情報:**
        - ファイル名: {file_info.get('name', 'N/A')}
        - サイズ: {file_info.get('size', 'N/A')}
        - 処理時刻: {file_info.get('processed_at', 'N/A')}
        """
        
        # 処理時間が提供されている場合は追加
        if file_info.get('processing_time'):
            info_text += f"\n        - 処理時間: {file_info.get('processing_time', 'N/A')}"
        
        st.info(info_text)
    
    def display_comparison_table(self, original_data: Dict[str, Any], 
                               validated_data: Dict[str, Any]) -> None:
        """元データと検証済みデータの比較表示"""
        st.subheader("📋 データ比較")
        
        comparison_data = []
        all_keys = set(original_data.keys()) | set(validated_data.keys())
        
        for key in sorted(all_keys):
            original_val = original_data.get(key, "")
            validated_val = validated_data.get(key, "")
            
            # 値が変更されているかチェック
            is_changed = str(original_val) != str(validated_val)
            status = "🔄 変更" if is_changed else "✅ 同一"
            
            comparison_data.append({
                "フィールド": key,
                "元データ": str(original_val)[:50] + ("..." if len(str(original_val)) > 50 else ""),
                "検証後": str(validated_val)[:50] + ("..." if len(str(validated_val)) > 50 else ""),
                "ステータス": status
            })
        
        if comparison_data:
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True)

class BatchValidationDisplay(ValidationDisplay):
    """バッチ処理用の拡張表示システム"""
    
    def display_batch_summary(self, batch_results: List[Dict[str, Any]]) -> None:
        """バッチ処理結果のサマリー表示"""
        if not batch_results:
            st.warning("処理結果がありません")
            return
        
        st.subheader("📊 バッチ処理サマリー")
        
        # 全体統計
        total_files = len(batch_results)
        successful_files = sum(1 for r in batch_results if r.get("validation", {}).get("is_valid", False))
        failed_files = total_files - successful_files
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総ファイル数", total_files)
        with col2:
            st.metric("成功", successful_files, delta=f"{successful_files/total_files*100:.1f}%")
        with col3:
            st.metric("要確認", failed_files, delta=f"{failed_files/total_files*100:.1f}%" if failed_files > 0 else None)
        
        # 詳細結果テーブル
        self._display_batch_details_table(batch_results)
    
    def _display_batch_details_table(self, batch_results: List[Dict[str, Any]]) -> None:
        """バッチ処理詳細結果テーブル"""
        table_data = []
        
        for i, result in enumerate(batch_results, 1):
            validation = result.get("validation", {})
            summary = validation.get("validation_summary", {})
            
            status = "✅ 成功" if validation.get("is_valid", False) else "❌ 要確認"
            error_count = summary.get("critical_issues", 0)
            warning_count = summary.get("warnings", 0)
            
            table_data.append({
                "No.": i,
                "ファイル名": result.get("file_name", f"ファイル{i}"),
                "ステータス": status,
                "エラー": error_count,
                "警告": warning_count,
                "総課題": summary.get("total_issues", 0)
            })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True) 