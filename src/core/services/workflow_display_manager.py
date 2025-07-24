"""
ワークフロー表示管理システム
統合ワークフローの結果表示を統一的に管理
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.log_config import get_logger

logger = get_logger(__name__)

class WorkflowDisplayManager:
    """ワークフロー表示管理クラス"""
    
    def __init__(self, workflow):
        """
        Args:
            workflow: UnifiedWorkflowEngineインスタンス
        """
        self.workflow = workflow
    
    def display_single_result(self, result: Dict[str, Any]):
        """
        単一ファイル処理結果の表示
        
        Args:
            result: 処理結果データ
        """
        try:
            if result.get('success', False):
                self._display_success_result(result)
            else:
                self._display_error_result(result)
                
        except Exception as e:
            logger.error(f"単一結果表示エラー: {e}")
            st.error(f"結果表示エラー: {e}")
    
    def display_batch_results(self, batch_result: Dict[str, Any]):
        """
        バッチ処理結果の表示
        
        Args:
            batch_result: バッチ処理結果データ
        """
        try:
            st.markdown("### 📊 バッチ処理結果")
            
            # サマリー表示
            total_files = batch_result.get('total_files', 0)
            successful_files = batch_result.get('successful_files', 0)
            failed_files = total_files - successful_files
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 総ファイル数", total_files)
            
            with col2:
                st.metric("✅ 成功", successful_files)
            
            with col3:
                st.metric("❌ 失敗", failed_files)
            
            with col4:
                processing_time = batch_result.get('total_processing_time', 0)
                st.metric("⏱️ 処理時間", f"{processing_time:.2f}秒")
            
            # 成功率表示
            if total_files > 0:
                success_rate = (successful_files / total_files) * 100
                if success_rate >= 90:
                    st.success(f"🎉 成功率: {success_rate:.1f}%")
                elif success_rate >= 70:
                    st.warning(f"⚠️ 成功率: {success_rate:.1f}%")
                else:
                    st.error(f"⚠️ 成功率: {success_rate:.1f}%")
            
            # 詳細結果表示
            results = batch_result.get('results', [])
            if results:
                self._display_detailed_results(results)
                
        except Exception as e:
            logger.error(f"バッチ結果表示エラー: {e}")
            st.error(f"バッチ結果表示エラー: {e}")
    
    def _display_success_result(self, result: Dict[str, Any]):
        """成功結果の表示"""
        st.success("✅ 処理成功")
        
        filename = result.get('filename', 'N/A')
        st.write(f"**ファイル名:** {filename}")
        
        processing_time = result.get('processing_time', 0)
        st.write(f"**処理時間:** {processing_time:.2f}秒")
        
        # 抽出データ表示
        extracted_data = result.get('extracted_data', {})
        if extracted_data:
            self._display_extracted_data(extracted_data)
        
        # 検証結果表示
        validation_result = result.get('validation_result')
        if validation_result:
            self._display_validation_result(validation_result)
    
    def _display_error_result(self, result: Dict[str, Any]):
        """エラー結果の表示"""
        st.error("❌ 処理失敗")
        
        filename = result.get('filename', 'N/A')
        st.write(f"**ファイル名:** {filename}")
        
        # 複数の可能性があるエラーメッセージキーをチェック
        error_message = (result.get('error_message') or 
                        result.get('error') or 
                        result.get('error_details') or 
                        '詳細不明')
        st.error(f"エラー内容: {error_message}")
        
        # エラー詳細がある場合
        error_details = result.get('error_details')
        if error_details:
            with st.expander("エラー詳細"):
                st.code(str(error_details))
    
    def _display_detailed_results(self, results: List[Dict[str, Any]]):
        """詳細結果の表示"""
        st.markdown("### 📋 ファイル別詳細結果")
        
        for i, result in enumerate(results, 1):
            filename = result.get('filename', f'ファイル{i}')
            success = result.get('success', False)
            
            if success:
                with st.expander(f"✅ {filename} - 処理成功", expanded=False):
                    self._display_success_result(result)
            else:
                with st.expander(f"❌ {filename} - 処理失敗", expanded=False):
                    self._display_error_result(result)
    
    def _display_extracted_data(self, extracted_data: Dict[str, Any]):
        """抽出データの表示"""
        st.markdown("**📄 抽出された主要情報:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"• 供給者名: {extracted_data.get('issuer', 'N/A')}")
            st.write(f"• 請求書番号: {extracted_data.get('main_invoice_number', 'N/A')}")
            st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
        
        with col2:
            amount_inclusive = extracted_data.get('amount_inclusive_tax', 0)
            amount_exclusive = extracted_data.get('amount_exclusive_tax', 0)
            
            try:
                amount_inclusive = float(amount_inclusive) if amount_inclusive else 0
                amount_exclusive = float(amount_exclusive) if amount_exclusive else 0
                tax_amount = amount_inclusive - amount_exclusive
                
                st.write(f"• 合計金額: ¥{amount_inclusive:,.0f}")
                st.write(f"• 税額: ¥{tax_amount:,.0f}")
            except (ValueError, TypeError):
                st.write(f"• 合計金額: {amount_inclusive}")
                st.write(f"• 税額: 計算不可")
            
            st.write(f"• 請求日: {extracted_data.get('issue_date', 'N/A')}")
        
        # 詳細データがある場合
        if len(extracted_data) > 6:  # 基本項目以外にデータがある場合
            with st.expander("🔍 詳細データ"):
                for key, value in extracted_data.items():
                    if key not in ['issuer', 'main_invoice_number', 'currency', 
                                 'amount_inclusive_tax', 'amount_exclusive_tax', 'issue_date']:
                        st.write(f"**{key}:** {value}")
    
    def _display_validation_result(self, validation_result: Dict[str, Any]):
        """検証結果の表示"""
        st.markdown("**🔍 検証結果:**")
        
        is_valid = validation_result.get('is_valid', False)
        
        if is_valid:
            st.success("✅ 検証: 合格")
        else:
            st.warning("⚠️ 検証: 注意が必要")
        
        # 警告・エラー表示
        warnings = validation_result.get('warnings', [])
        errors = validation_result.get('errors', [])
        
        if warnings:
            st.markdown("**⚠️ 警告:**")
            for warning in warnings:
                st.warning(f"• {warning}")
        
        if errors:
            st.markdown("**❌ エラー:**")
            for error in errors:
                st.error(f"• {error}")
        
        # スコア表示
        score = validation_result.get('score', 0)
        if score > 0:
            st.write(f"**📊 品質スコア:** {score:.1f}/100")
    
    def display_progress_info(self, progress_info: Dict[str, Any]):
        """進行状況情報の表示"""
        try:
            current_step = progress_info.get('current_step', '')
            progress_percentage = progress_info.get('progress_percentage', 0)
            message = progress_info.get('message', '')
            
            # プログレスバー
            progress_bar = st.progress(progress_percentage / 100)
            
            # 現在のステップ表示
            st.info(f"🔄 {current_step}: {message}")
            
            # 詳細情報がある場合
            details = progress_info.get('details')
            if details:
                with st.expander("詳細情報"):
                    st.json(details)
                    
        except Exception as e:
            logger.error(f"進行状況表示エラー: {e}")
            st.error(f"進行状況表示エラー: {e}")
    
    def display_processing_summary(self, summary: Dict[str, Any]):
        """処理概要の表示"""
        try:
            st.markdown("### 📈 処理概要")
            
            # 基本統計
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_files = summary.get('total_files', 0)
                st.metric("処理ファイル数", total_files)
            
            with col2:
                total_time = summary.get('total_time', 0)
                st.metric("総処理時間", f"{total_time:.2f}秒")
            
            with col3:
                avg_time = summary.get('average_time', 0)
                st.metric("平均処理時間", f"{avg_time:.2f}秒/件")
            
            # エラー分析
            error_summary = summary.get('error_summary')
            if error_summary:
                st.markdown("**🔍 エラー分析:**")
                for error_type, count in error_summary.items():
                    st.write(f"• {error_type}: {count}件")
                    
        except Exception as e:
            logger.error(f"処理概要表示エラー: {e}")
            st.error(f"処理概要表示エラー: {e}") 