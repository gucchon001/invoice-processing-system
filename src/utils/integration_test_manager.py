#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合テスト管理クラス - JSONプロンプトシステム精度検証

実際のPDFファイルを使った統合テスト、精度測定、
ベースライン策定機能を提供します。
"""

import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time
import statistics

logger = logging.getLogger(__name__)


class IntegrationTestManager:
    """統合テスト管理クラス"""
    
    def __init__(self, drive_manager, gemini_manager, database_manager=None):
        """初期化"""
        self.drive_manager = drive_manager
        self.gemini_manager = gemini_manager
        self.database_manager = database_manager
        self.test_results = []
        
    def run_comprehensive_test(self, test_folder_id: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        包括的統合テスト実行
        
        Args:
            test_folder_id: テスト用PDFが格納されたGoogle DriveフォルダID
            sample_size: テストするPDFファイルの数
            
        Returns:
            統合テスト結果
        """
        logger.info(f"統合テスト開始: フォルダID={test_folder_id}, サンプル数={sample_size}")
        
        test_session = {
            "session_id": f"integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now().isoformat(),
            "folder_id": test_folder_id,
            "target_sample_size": sample_size,
            "tests": {
                "pdf_extraction": {"results": [], "success_rate": 0, "avg_time": 0},
                "key_info_extraction": {"results": [], "accuracy_rate": 0},
                "company_matching": {"results": [], "precision": 0, "recall": 0},
                "integrated_matching": {"results": [], "success_rate": 0},
                "performance": {"avg_processing_time": 0, "total_time": 0}
            },
            "baseline_metrics": {},
            "errors": []
        }
        
        try:
            # PDFファイル一覧取得
            pdf_files = self._get_test_pdf_files(test_folder_id, sample_size)
            
            if not pdf_files:
                test_session["errors"].append("テスト用PDFファイルが見つかりません")
                return test_session
            
            logger.info(f"{len(pdf_files)}個のPDFファイルでテスト実行")
            
            # 各PDFファイルをテスト
            for i, file_info in enumerate(pdf_files):
                logger.info(f"テスト進行中: {i+1}/{len(pdf_files)} - {file_info['name']}")
                
                file_result = self._test_single_pdf(file_info)
                
                if file_result:
                    # 各テスト結果に追加
                    test_session["tests"]["pdf_extraction"]["results"].append(file_result["extraction"])
                    test_session["tests"]["key_info_extraction"]["results"].append(file_result["key_info"])
                    test_session["tests"]["company_matching"]["results"].append(file_result["company_match"])
                    test_session["tests"]["integrated_matching"]["results"].append(file_result["integrated"])
                    
                else:
                    test_session["errors"].append(f"ファイル処理失敗: {file_info['name']}")
            
            # 統計計算
            test_session = self._calculate_test_statistics(test_session)
            
            # ベースライン策定
            test_session["baseline_metrics"] = self._establish_baseline_metrics(test_session)
            
            test_session["completed_at"] = datetime.now().isoformat()
            
            logger.info("統合テスト完了")
            return test_session
            
        except Exception as e:
            error_msg = f"統合テストエラー: {e}"
            logger.error(error_msg)
            test_session["errors"].append(error_msg)
            return test_session
    
    def _get_test_pdf_files(self, folder_id: str, sample_size: int) -> List[Dict[str, Any]]:
        """テスト用PDFファイル一覧を取得"""
        try:
            # フォルダ内のPDFファイルを検索
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = self.drive_manager.service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            # サンプル数に制限
            if len(files) > sample_size:
                files = files[:sample_size]
            
            logger.info(f"{len(files)}個のテスト用PDFファイルを取得")
            return files
            
        except Exception as e:
            logger.error(f"テスト用PDFファイル取得エラー: {e}")
            return []
    
    def _test_single_pdf(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """単一PDFファイルの統合テスト"""
        try:
            file_id = file_info["id"]
            filename = file_info["name"]
            start_time = time.time()
            
            # PDFダウンロード
            pdf_content = self._download_pdf_content(file_id)
            if not pdf_content:
                return None
            
            # 1. PDF情報抽出テスト
            extraction_result = self._test_pdf_extraction(pdf_content, filename)
            
            # 2. キー情報抽出精度テスト
            key_info_result = self._test_key_info_extraction(extraction_result.get("extracted_data"))
            
            # 3. 企業名照合テスト
            company_match_result = self._test_company_matching(extraction_result.get("extracted_data"))
            
            # 4. 統合照合テスト
            integrated_result = self._test_integrated_matching(extraction_result.get("extracted_data"))
            
            processing_time = time.time() - start_time
            
            return {
                "file_info": file_info,
                "processing_time": processing_time,
                "extraction": extraction_result,
                "key_info": key_info_result,
                "company_match": company_match_result,
                "integrated": integrated_result
            }
            
        except Exception as e:
            logger.error(f"単一PDFテストエラー ({file_info.get('name', 'unknown')}): {e}")
            return None
    
    def _download_pdf_content(self, file_id: str) -> Optional[bytes]:
        """PDFコンテンツをダウンロード"""
        try:
            return self.drive_manager.download_file_content(file_id)
        except Exception as e:
            logger.error(f"PDFダウンロードエラー: {e}")
            return None
    
    def _test_pdf_extraction(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """PDF情報抽出テスト"""
        try:
            start_time = time.time()
            
            # JSONプロンプトを使用した抽出
            extracted_data = self.gemini_manager.extract_invoice_data(pdf_content)
            
            extraction_time = time.time() - start_time
            
            # 抽出成功判定
            success = self._evaluate_extraction_success(extracted_data)
            
            return {
                "success": success,
                "extraction_time": extraction_time,
                "extracted_data": extracted_data,
                "filename": filename,
                "data_completeness": self._calculate_data_completeness(extracted_data)
            }
            
        except Exception as e:
            logger.error(f"PDF抽出テストエラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }
    
    def _test_key_info_extraction(self, extracted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """キー情報抽出精度テスト"""
        if not extracted_data:
            return {"accuracy": 0, "key_count": 0, "score": 0}
        
        key_info = extracted_data.get("key_info", {})
        
        # キー情報の品質評価
        priority_keys = ["アカウントID", "利用期間", "契約番号", "サービス名", "請求種別"]
        found_priority_keys = sum(1 for key in priority_keys if key in key_info)
        
        accuracy = found_priority_keys / len(priority_keys) if priority_keys else 0
        
        return {
            "accuracy": accuracy,
            "key_count": len(key_info),
            "priority_keys_found": found_priority_keys,
            "total_priority_keys": len(priority_keys),
            "score": accuracy * 100
        }
    
    def _test_company_matching(self, extracted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """企業名照合テスト"""
        if not extracted_data:
            return {"success": False, "confidence": 0}
        
        issuer_name = extracted_data.get("issuer")
        if not issuer_name:
            return {"success": False, "confidence": 0, "error": "企業名なし"}
        
        try:
            # サンプル企業名リストでテスト
            sample_companies = [
                "Google合同会社", "Amazon Japan合同会社", "マイクロソフト株式会社",
                "Apple Japan合同会社", "Meta Platforms Ireland Limited"
            ]
            
            # 企業名照合実行
            match_result = self.gemini_manager.match_company_name(issuer_name, sample_companies)
            
            if match_result and match_result.get("matched_company_name"):
                return {
                    "success": True,
                    "confidence": match_result.get("confidence_score", 0),
                    "matched_company": match_result.get("matched_company_name"),
                    "original_name": issuer_name
                }
            else:
                return {"success": False, "confidence": 0, "original_name": issuer_name}
                
        except Exception as e:
            return {"success": False, "error": str(e), "original_name": issuer_name}
    
    def _test_integrated_matching(self, extracted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """統合照合テスト"""
        if not extracted_data:
            return {"success": False, "confidence": 0}
        
        try:
            # サンプル支払マスタレコード
            sample_records = [
                {
                    "id": "entry_001",
                    "company_name": "Google合同会社",
                    "content": "Google Ads広告費",
                    "account_item": "広告宣伝費",
                    "amount": 50000,
                    "additional_condition": "月次請求"
                }
            ]
            
            # 統合照合実行
            integrated_result = self.gemini_manager.match_integrated_invoice(extracted_data, sample_records)
            
            if integrated_result and integrated_result.get("matched_entry_id"):
                return {
                    "success": True,
                    "confidence": integrated_result.get("confidence_score", 0),
                    "matched_entry": integrated_result.get("matched_entry_id"),
                    "details": integrated_result
                }
            else:
                return {"success": False, "confidence": 0}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _evaluate_extraction_success(self, extracted_data: Optional[Dict[str, Any]]) -> bool:
        """抽出成功の評価"""
        if not extracted_data:
            return False
        
        # 必須フィールドの確認
        required_fields = ["issuer", "amount_inclusive_tax"]
        return all(extracted_data.get(field) is not None for field in required_fields)
    
    def _calculate_data_completeness(self, extracted_data: Optional[Dict[str, Any]]) -> float:
        """データ完全性の計算"""
        if not extracted_data:
            return 0.0
        
        all_fields = [
            "issuer", "payer", "issue_date", "due_date", "main_invoice_number",
            "amount_inclusive_tax", "amount_exclusive_tax", "currency", "key_info", "line_items"
        ]
        
        filled_fields = sum(1 for field in all_fields if extracted_data.get(field) is not None)
        return filled_fields / len(all_fields)
    
    def _calculate_test_statistics(self, test_session: Dict[str, Any]) -> Dict[str, Any]:
        """テスト統計を計算"""
        try:
            # PDF抽出成功率
            extraction_results = test_session["tests"]["pdf_extraction"]["results"]
            extraction_success_count = sum(1 for r in extraction_results if r.get("success"))
            test_session["tests"]["pdf_extraction"]["success_rate"] = (
                extraction_success_count / len(extraction_results) if extraction_results else 0
            )
            
            # 平均処理時間
            processing_times = [r.get("extraction_time", 0) for r in extraction_results]
            test_session["tests"]["pdf_extraction"]["avg_time"] = (
                statistics.mean(processing_times) if processing_times else 0
            )
            
            # キー情報抽出精度
            key_info_results = test_session["tests"]["key_info_extraction"]["results"]
            key_accuracies = [r.get("accuracy", 0) for r in key_info_results]
            test_session["tests"]["key_info_extraction"]["accuracy_rate"] = (
                statistics.mean(key_accuracies) if key_accuracies else 0
            )
            
            # 企業名照合精度
            company_results = test_session["tests"]["company_matching"]["results"]
            company_success_count = sum(1 for r in company_results if r.get("success"))
            test_session["tests"]["company_matching"]["precision"] = (
                company_success_count / len(company_results) if company_results else 0
            )
            
            # 統合照合成功率
            integrated_results = test_session["tests"]["integrated_matching"]["results"]
            integrated_success_count = sum(1 for r in integrated_results if r.get("success"))
            test_session["tests"]["integrated_matching"]["success_rate"] = (
                integrated_success_count / len(integrated_results) if integrated_results else 0
            )
            
        except Exception as e:
            logger.error(f"統計計算エラー: {e}")
            test_session["errors"].append(f"統計計算エラー: {e}")
        
        return test_session
    
    def _establish_baseline_metrics(self, test_session: Dict[str, Any]) -> Dict[str, Any]:
        """ベースライン指標を策定"""
        baseline = {
            "established_at": datetime.now().isoformat(),
            "test_sample_size": len(test_session["tests"]["pdf_extraction"]["results"]),
            "metrics": {
                "pdf_extraction_success_rate": {
                    "current": test_session["tests"]["pdf_extraction"]["success_rate"],
                    "target": 0.85,  # 目標85%
                    "minimum": 0.70  # 最低70%
                },
                "key_info_accuracy": {
                    "current": test_session["tests"]["key_info_extraction"]["accuracy_rate"],
                    "target": 0.75,  # 目標75%
                    "minimum": 0.60  # 最低60%
                },
                "company_matching_precision": {
                    "current": test_session["tests"]["company_matching"]["precision"],
                    "target": 0.80,  # 目標80%
                    "minimum": 0.65  # 最低65%
                },
                "integrated_matching_success": {
                    "current": test_session["tests"]["integrated_matching"]["success_rate"],
                    "target": 0.70,  # 目標70%
                    "minimum": 0.55  # 最低55%
                },
                "avg_processing_time": {
                    "current": test_session["tests"]["pdf_extraction"]["avg_time"],
                    "target": 10.0,  # 目標10秒以内
                    "maximum": 20.0  # 最大20秒
                }
            },
            "quality_assessment": self._assess_quality_level(test_session)
        }
        
        return baseline
    
    def _assess_quality_level(self, test_session: Dict[str, Any]) -> str:
        """品質レベルの評価"""
        tests = test_session["tests"]
        
        extraction_rate = tests["pdf_extraction"]["success_rate"]
        key_info_rate = tests["key_info_extraction"]["accuracy_rate"]
        company_rate = tests["company_matching"]["precision"]
        integrated_rate = tests["integrated_matching"]["success_rate"]
        
        avg_performance = (extraction_rate + key_info_rate + company_rate + integrated_rate) / 4
        
        if avg_performance >= 0.80:
            return "優良（Excellent）"
        elif avg_performance >= 0.70:
            return "良好（Good）"
        elif avg_performance >= 0.60:
            return "標準（Standard）"
        else:
            return "要改善（Needs Improvement）"
    
    def generate_test_report(self, test_session: Dict[str, Any]) -> Dict[str, Any]:
        """テストレポートを生成"""
        report = {
            "report_id": f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "test_session_id": test_session.get("session_id"),
            "summary": {
                "total_pdfs_tested": len(test_session["tests"]["pdf_extraction"]["results"]),
                "overall_success_rate": self._calculate_overall_success_rate(test_session),
                "quality_level": test_session["baseline_metrics"]["quality_assessment"],
                "performance_status": self._evaluate_performance_status(test_session)
            },
            "detailed_metrics": test_session["tests"],
            "baseline_comparison": self._compare_with_baseline(test_session),
            "recommendations": self._generate_recommendations(test_session),
            "next_steps": self._suggest_next_steps(test_session)
        }
        
        return report
    
    def _calculate_overall_success_rate(self, test_session: Dict[str, Any]) -> float:
        """総合成功率を計算"""
        tests = test_session["tests"]
        rates = [
            tests["pdf_extraction"]["success_rate"],
            tests["key_info_extraction"]["accuracy_rate"],
            tests["company_matching"]["precision"],
            tests["integrated_matching"]["success_rate"]
        ]
        return statistics.mean(rates) if rates else 0
    
    def _evaluate_performance_status(self, test_session: Dict[str, Any]) -> str:
        """パフォーマンス状況を評価"""
        avg_time = test_session["tests"]["pdf_extraction"]["avg_time"]
        
        if avg_time <= 10:
            return "高速（Fast）"
        elif avg_time <= 20:
            return "標準（Normal）"
        else:
            return "要最適化（Slow）"
    
    def _compare_with_baseline(self, test_session: Dict[str, Any]) -> Dict[str, Any]:
        """ベースラインとの比較"""
        baseline = test_session["baseline_metrics"]["metrics"]
        comparison = {}
        
        for metric_name, metric_data in baseline.items():
            current = metric_data["current"]
            target = metric_data.get("target", 0)
            
            comparison[metric_name] = {
                "current": current,
                "target": target,
                "achievement_rate": current / target if target > 0 else 0,
                "status": "達成" if current >= target else "未達成"
            }
        
        return comparison
    
    def _generate_recommendations(self, test_session: Dict[str, Any]) -> List[str]:
        """改善提案を生成"""
        recommendations = []
        tests = test_session["tests"]
        
        # PDF抽出成功率が低い場合
        if tests["pdf_extraction"]["success_rate"] < 0.85:
            recommendations.append("📄 PDF抽出精度向上: プロンプトの改善やエラーハンドリング強化を検討")
        
        # キー情報抽出精度が低い場合
        if tests["key_info_extraction"]["accuracy_rate"] < 0.75:
            recommendations.append("🔑 キー情報抽出強化: 重要項目の抽出ロジック見直しとプロンプト調整")
        
        # 企業名照合精度が低い場合
        if tests["company_matching"]["precision"] < 0.80:
            recommendations.append("🏢 企業名照合改善: 表記揺れ辞書の拡充と類似度計算アルゴリズム強化")
        
        # 統合照合成功率が低い場合
        if tests["integrated_matching"]["success_rate"] < 0.70:
            recommendations.append("🔄 統合照合最適化: 照合ロジックの改善と確信度計算の調整")
        
        # 処理時間が長い場合
        if tests["pdf_extraction"]["avg_time"] > 20:
            recommendations.append("⚡ パフォーマンス改善: API呼び出し最適化とキャッシュ機能追加")
        
        return recommendations
    
    def _suggest_next_steps(self, test_session: Dict[str, Any]) -> List[str]:
        """次のステップを提案"""
        next_steps = []
        overall_rate = self._calculate_overall_success_rate(test_session)
        
        if overall_rate >= 0.80:
            next_steps.append("✅ 本格運用開始の準備")
            next_steps.append("📊 定期的な精度監視体制の構築")
        elif overall_rate >= 0.70:
            next_steps.append("🔧 特定課題への集中改善")
            next_steps.append("🧪 追加テストケースでの検証")
        else:
            next_steps.append("🚨 根本的なアルゴリズム見直し")
            next_steps.append("📝 プロンプトエンジニアリングの強化")
        
        next_steps.append("📈 継続的な改善サイクルの確立")
        
        return next_steps


# グローバルインスタンス管理
_global_integration_test_manager = None

def get_integration_test_manager(drive_manager=None, gemini_manager=None, database_manager=None):
    """グローバル統合テストマネージャーを取得"""
    global _global_integration_test_manager
    
    if _global_integration_test_manager is None and drive_manager and gemini_manager:
        _global_integration_test_manager = IntegrationTestManager(
            drive_manager, gemini_manager, database_manager
        )
    
    return _global_integration_test_manager 