#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企業名表記正規化・マッチング強化クラス

カタカナ・英字変換、法人格正規化、表記揺れ辞書による
企業名照合精度の向上を実現します。
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
import unicodedata
import difflib

logger = logging.getLogger(__name__)


class CompanyNameNormalizer:
    """企業名表記正規化クラス"""
    
    def __init__(self):
        """初期化"""
        # 企業名表記辞書（よくある表記揺れパターン）
        self.company_name_dictionary = self._build_company_dictionary()
        
        # 法人格正規化マッピング
        self.corporate_suffix_mappings = self._build_corporate_mappings()
        
        # カタカナ・英字変換辞書
        self.katakana_english_mappings = self._build_katakana_english_mappings()
        
        logger.info("CompanyNameNormalizer初期化完了")
    
    def _build_company_dictionary(self) -> Dict[str, str]:
        """企業名表記辞書を構築"""
        return {
            # よくある表記揺れパターン（請求書記載名 → 正式企業名）
            "Google": "Google合同会社",
            "グーグル": "Google合同会社",
            "グーグル合同会社": "Google合同会社",
            "Google LLC": "Google合同会社",
            "Google Japan": "Google合同会社",
            
            "Amazon": "Amazon Japan合同会社",
            "アマゾン": "Amazon Japan合同会社",
            "Amazon Web Services": "アマゾン ウェブ サービス ジャパン合同会社",
            "AWS": "アマゾン ウェブ サービス ジャパン合同会社",
            "Amazon Japan": "Amazon Japan合同会社",
            
            "Microsoft": "マイクロソフト株式会社",
            "マイクロソフト": "マイクロソフト株式会社",
            "Microsoft Corporation": "マイクロソフト株式会社",
            "Microsoft Japan": "マイクロソフト株式会社",
            
            "Apple": "Apple Japan合同会社",
            "アップル": "Apple Japan合同会社",
            "Apple Inc.": "Apple Japan合同会社",
            "Apple Japan": "Apple Japan合同会社",
            
            "Meta": "Meta Platforms Ireland Limited",
            "メタ": "Meta Platforms Ireland Limited",
            "Facebook": "Meta Platforms Ireland Limited",
            "フェイスブック": "Meta Platforms Ireland Limited",
            
            "Yahoo": "LINEヤフー株式会社",
            "ヤフー": "LINEヤフー株式会社",
            "Yahoo! JAPAN": "LINEヤフー株式会社",
            "Yahoo Japan": "LINEヤフー株式会社",
            
            "Salesforce": "株式会社セールスフォース・ジャパン",
            "セールスフォース": "株式会社セールスフォース・ジャパン",
            "Salesforce.com": "株式会社セールスフォース・ジャパン",
            
            "Oracle": "日本オラクル株式会社",
            "オラクル": "日本オラクル株式会社",
            "Oracle Corporation": "日本オラクル株式会社",
            
            "Adobe": "アドビ株式会社",
            "アドビ": "アドビ株式会社",
            "Adobe Systems": "アドビ株式会社",
            "Adobe Inc.": "アドビ株式会社",
            
            "Zoom": "Zoom Video Communications, Inc.",
            "ズーム": "Zoom Video Communications, Inc.",
            "Zoom Video": "Zoom Video Communications, Inc.",
            
            "Slack": "株式会社セールスフォース・ジャパン",
            "スラック": "株式会社セールスフォース・ジャパン",
            "Slack Technologies": "株式会社セールスフォース・ジャパン",
            
            "Dropbox": "Dropbox Japan株式会社",
            "ドロップボックス": "Dropbox Japan株式会社",
            "Dropbox, Inc.": "Dropbox Japan株式会社",
            
            "Canva": "Canva Pty Ltd",
            "キャンバ": "Canva Pty Ltd",
            "Canva Pty Ltd": "Canva Pty Ltd",
            
            "ChatGPT": "OpenAI L.L.C.",
            "OpenAI": "OpenAI L.L.C.",
            "チャットGPT": "OpenAI L.L.C.",
            
            "Notion": "Notion Labs, Inc.",
            "ノーション": "Notion Labs, Inc.",
            "Notion Labs": "Notion Labs, Inc.",
            
            "GitHub": "GitHub, Inc.",
            "ギットハブ": "GitHub, Inc.",
            "Git Hub": "GitHub, Inc.",
            
            "Figma": "Figma, Inc.",
            "フィグマ": "Figma, Inc.",
            
            "Asana": "Asana, Inc.",
            "アサナ": "Asana, Inc.",
            
            "Trello": "Atlassian Corporation Plc",
            "トレロ": "Atlassian Corporation Plc",
            
            "Atlassian": "Atlassian Corporation Plc",
            "アトラシアン": "Atlassian Corporation Plc",
            
            "Stripe": "Stripe, Inc.",
            "ストライプ": "Stripe, Inc.",
            
            "PayPal": "PayPal Pte. Ltd.",
            "ペイパル": "PayPal Pte. Ltd.",
        }
    
    def _build_corporate_mappings(self) -> Dict[str, List[str]]:
        """法人格正規化マッピングを構築"""
        return {
            "株式会社": ["(株)", "㈱", "Co., Ltd.", "Inc.", "Corporation", "Corp."],
            "有限会社": ["(有)", "㈲", "Ltd.", "Limited"],
            "合同会社": ["(合)", "㈾", "LLC", "L.L.C."],
            "合資会社": ["(資)", "㈿"],
            "合名会社": ["(名)", "㈴"],
            "一般社団法人": ["(一社)", "㈳"],
            "公益社団法人": ["(公社)"],
            "一般財団法人": ["(一財)", "㈶"],
            "公益財団法人": ["(公財)"],
            "特定非営利活動法人": ["NPO法人", "NPO"],
        }
    
    def _build_katakana_english_mappings(self) -> Dict[str, str]:
        """カタカナ・英字変換辞書を構築"""
        return {
            # IT・テクノロジー企業
            "グーグル": "Google",
            "アマゾン": "Amazon",
            "マイクロソフト": "Microsoft",
            "アップル": "Apple",
            "メタ": "Meta",
            "フェイスブック": "Facebook",
            "ヤフー": "Yahoo",
            "セールスフォース": "Salesforce",
            "オラクル": "Oracle",
            "アドビ": "Adobe",
            "ズーム": "Zoom",
            "スラック": "Slack",
            "ドロップボックス": "Dropbox",
            "キャンバ": "Canva",
            "チャットGPT": "ChatGPT",
            "ノーション": "Notion",
            "ギットハブ": "GitHub",
            "フィグマ": "Figma",
            "アサナ": "Asana",
            "トレロ": "Trello",
            "アトラシアン": "Atlassian",
            "ストライプ": "Stripe",
            "ペイパル": "PayPal",
            
            # 逆方向（英字→カタカナ）
            "Google": "グーグル",
            "Amazon": "アマゾン",
            "Microsoft": "マイクロソフト",
            "Apple": "アップル",
            "Meta": "メタ",
            "Facebook": "フェイスブック",
            "Yahoo": "ヤフー",
            "Salesforce": "セールスフォース",
            "Oracle": "オラクル",
            "Adobe": "アドビ",
            "Zoom": "ズーム",
            "Slack": "スラック",
            "Dropbox": "ドロップボックス",
            "Canva": "キャンバ",
            "ChatGPT": "チャットGPT",
            "Notion": "ノーション",
            "GitHub": "ギットハブ",
            "Figma": "フィグマ",
            "Asana": "アサナ",
            "Trello": "トレロ",
            "Atlassian": "アトラシアン",
            "Stripe": "ストライプ",
            "PayPal": "ペイパル",
        }
    
    def normalize_company_name(self, company_name: str) -> str:
        """企業名を正規化"""
        if not company_name:
            return ""
        
        # 1. 基本的な正規化
        normalized = self._basic_normalize(company_name)
        
        # 2. 辞書による直接マッピング
        direct_match = self._direct_dictionary_lookup(normalized)
        if direct_match:
            return direct_match
        
        # 3. 法人格正規化
        normalized = self._normalize_corporate_suffix(normalized)
        
        # 4. カタカナ・英字変換
        normalized = self._convert_katakana_english(normalized)
        
        # 5. 再度辞書チェック
        direct_match = self._direct_dictionary_lookup(normalized)
        if direct_match:
            return direct_match
        
        return normalized
    
    def _basic_normalize(self, text: str) -> str:
        """基本的な正規化処理"""
        # Unicode正規化
        text = unicodedata.normalize('NFKC', text)
        
        # 全角・半角統一
        text = text.replace('　', ' ')  # 全角スペース→半角スペース
        
        # 不要な記号・空白の除去
        text = re.sub(r'[!！?？。．、，]', '', text)
        text = re.sub(r'\s+', ' ', text)  # 複数空白を単一空白に
        text = text.strip()
        
        return text
    
    def _direct_dictionary_lookup(self, company_name: str) -> Optional[str]:
        """辞書による直接マッピング"""
        # 完全一致
        if company_name in self.company_name_dictionary:
            return self.company_name_dictionary[company_name]
        
        # 大文字小文字を無視した一致
        for key, value in self.company_name_dictionary.items():
            if company_name.lower() == key.lower():
                return value
        
        # 部分一致（企業名が辞書キーに含まれる場合）
        for key, value in self.company_name_dictionary.items():
            if key in company_name or company_name in key:
                return value
        
        return None
    
    def _normalize_corporate_suffix(self, company_name: str) -> str:
        """法人格の正規化"""
        for standard_form, variants in self.corporate_suffix_mappings.items():
            for variant in variants:
                if variant in company_name:
                    company_name = company_name.replace(variant, standard_form)
                    break
        
        return company_name
    
    def _convert_katakana_english(self, company_name: str) -> str:
        """カタカナ・英字変換"""
        for katakana, english in self.katakana_english_mappings.items():
            if katakana in company_name:
                company_name = company_name.replace(katakana, english)
            elif english in company_name:
                # 英字からカタカナへの変換も試行
                company_name = company_name.replace(english, katakana)
        
        return company_name
    
    def enhanced_company_matching(self, issuer_name: str, master_company_list: List[str]) -> Optional[Dict[str, any]]:
        """
        強化版企業名照合
        
        Args:
            issuer_name: 請求書の請求元名
            master_company_list: 支払マスタの企業名リスト
            
        Returns:
            照合結果辞書またはNone
        """
        if not issuer_name or not master_company_list:
            return None
        
        logger.info(f"強化版企業名照合開始: {issuer_name} vs {len(master_company_list)}件")
        
        # 1. 正規化
        normalized_issuer = self.normalize_company_name(issuer_name)
        normalized_masters = [self.normalize_company_name(name) for name in master_company_list]
        
        # 2. 段階的マッチング
        result = self._staged_matching(
            issuer_name, normalized_issuer, 
            master_company_list, normalized_masters
        )
        
        if result:
            logger.info(f"照合成功: {result['matched_company_name']} (確信度: {result['confidence_score']:.2f})")
        else:
            logger.warning(f"照合失敗: {issuer_name}")
        
        return result
    
    def _staged_matching(self, original_issuer: str, normalized_issuer: str, 
                        original_masters: List[str], normalized_masters: List[str]) -> Optional[Dict[str, any]]:
        """段階的マッチング処理"""
        
        # Stage 1: 完全一致（正規化前）
        for i, master in enumerate(original_masters):
            if original_issuer == master:
                return self._create_match_result(
                    master, 0.95, "完全一致", original_issuer, master, "なし"
                )
        
        # Stage 2: 完全一致（正規化後）
        for i, master in enumerate(normalized_masters):
            if normalized_issuer == master:
                return self._create_match_result(
                    original_masters[i], 0.90, "正規化後完全一致", 
                    normalized_issuer, master, "正規化"
                )
        
        # Stage 3: 辞書マッピング
        for i, master in enumerate(original_masters):
            if self._is_dictionary_match(normalized_issuer, master):
                return self._create_match_result(
                    master, 0.88, "辞書マッピング一致", 
                    normalized_issuer, master, "辞書変換"
                )
        
        # Stage 4: 部分一致
        for i, master in enumerate(normalized_masters):
            similarity = self._calculate_similarity(normalized_issuer, master)
            if similarity >= 0.85:
                return self._create_match_result(
                    original_masters[i], similarity, "高類似度一致", 
                    normalized_issuer, master, f"類似度{similarity:.2f}"
                )
        
        # Stage 5: 緩い類似度一致
        best_match = None
        best_similarity = 0
        
        for i, master in enumerate(normalized_masters):
            similarity = self._calculate_similarity(normalized_issuer, master)
            if similarity > best_similarity and similarity >= 0.70:
                best_similarity = similarity
                best_match = (original_masters[i], master, i)
        
        if best_match and best_similarity >= 0.70:
            return self._create_match_result(
                best_match[0], best_similarity, "類似度一致", 
                normalized_issuer, best_match[1], f"類似度{best_similarity:.2f}"
            )
        
        return None
    
    def _is_dictionary_match(self, issuer_name: str, master_name: str) -> bool:
        """辞書による照合判定"""
        # 企業名辞書での変換後の一致確認
        converted_issuer = self._direct_dictionary_lookup(issuer_name)
        if converted_issuer and converted_issuer == master_name:
            return True
        
        converted_master = self._direct_dictionary_lookup(master_name)
        if converted_master and converted_master == issuer_name:
            return True
        
        return False
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """類似度計算"""
        if not name1 or not name2:
            return 0.0
        
        # 複数の類似度指標を組み合わせ
        sequence_similarity = difflib.SequenceMatcher(None, name1, name2).ratio()
        
        # 共通部分文字列の比率
        common_substring = self._longest_common_substring(name1, name2)
        substring_ratio = len(common_substring) / max(len(name1), len(name2))
        
        # 重み付き平均
        combined_similarity = (sequence_similarity * 0.7) + (substring_ratio * 0.3)
        
        return combined_similarity
    
    def _longest_common_substring(self, str1: str, str2: str) -> str:
        """最長共通部分文字列を取得"""
        m = len(str1)
        n = len(str2)
        
        # DPテーブル
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        max_length = 0
        ending_pos_i = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    if dp[i][j] > max_length:
                        max_length = dp[i][j]
                        ending_pos_i = i
                else:
                    dp[i][j] = 0
        
        return str1[ending_pos_i - max_length:ending_pos_i]
    
    def _create_match_result(self, matched_name: str, confidence: float, reason: str,
                           normalized_original: str, normalized_matched: str, 
                           transformation: str) -> Dict[str, any]:
        """照合結果を作成"""
        return {
            "matched_company_name": matched_name,
            "confidence_score": confidence,
            "matching_reason": reason,
            "matching_details": {
                "normalized_original": normalized_original,
                "normalized_matched": normalized_matched,
                "transformation_applied": transformation
            },
            "processing_notes": f"強化版照合により{reason}で特定",
            "enhanced_matching": True
        }


# グローバルインスタンス管理
_global_company_normalizer = None

def get_company_normalizer() -> CompanyNameNormalizer:
    """グローバル企業名正規化インスタンスを取得"""
    global _global_company_normalizer
    
    if _global_company_normalizer is None:
        _global_company_normalizer = CompanyNameNormalizer()
    
    return _global_company_normalizer 