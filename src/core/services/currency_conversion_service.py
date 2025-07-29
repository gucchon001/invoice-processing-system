"""
外貨換算サービス

Exchange Rate APIと連携して外貨からJPYへの換算処理を提供する
キャッシュ機能により高速化とAPI呼び出し回数の削減を実現
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
from utils.log_config import get_logger

logger = get_logger(__name__)

class CurrencyConversionService:
    """外貨換算サービス（40カラム新機能対応）"""
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 3600):
        """
        Args:
            api_key: Exchange Rate API キー（デモ用にはFree APIを使用）
            cache_ttl: キャッシュ保持時間（秒）
        """
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self.rate_cache = {}
        self.base_url = "https://api.exchangerate-api.com/v4/latest"
        
        logger.info("CurrencyConversionService initialized.")
    
    def convert_to_jpy(self, amount: float, from_currency: str) -> Dict[str, Any]:
        """外貨からJPYに換算する（メイン機能）
        
        Args:
            amount: 換算対象金額
            from_currency: 元通貨コード（USD, EUR等）
            
        Returns:
            Dict containing:
                - exchange_rate: 為替レート
                - jpy_amount: JPY換算金額
                - conversion_timestamp: 換算日時
                - source: レート取得ソース
        """
        try:
            logger.info(f"🔄 外貨換算開始: {amount} {from_currency} → JPY")
            
            # JPYの場合はそのまま返す
            if from_currency.upper() == 'JPY':
                return {
                    'exchange_rate': 1.0,
                    'jpy_amount': amount,
                    'conversion_timestamp': datetime.now().isoformat(),
                    'source': 'no_conversion_needed'
                }
            
            # 為替レート取得
            rate = self.get_current_rate(from_currency, 'JPY')
            if rate is None:
                raise Exception(f"為替レート取得に失敗: {from_currency}/JPY")
            
            # JPY換算計算
            jpy_amount = amount * rate
            
            result = {
                'exchange_rate': rate,
                'jpy_amount': round(jpy_amount, 2),
                'conversion_timestamp': datetime.now().isoformat(),
                'source': 'exchange_rate_api'
            }
            
            logger.info(f"✅ 外貨換算成功: {amount} {from_currency} → ¥{jpy_amount:,.2f} (レート: {rate})")
            return result
            
        except Exception as e:
            logger.error(f"❌ 外貨換算エラー: {e}")
            raise
    
    def get_current_rate(self, from_currency: str, to_currency: str = 'JPY') -> Optional[float]:
        """現在の為替レートを取得する
        
        Args:
            from_currency: 元通貨コード
            to_currency: 対象通貨コード（デフォルト: JPY）
            
        Returns:
            float: 為替レート（失敗時はNone）
        """
        try:
            # 通貨コード正規化
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()
            
            # キャッシュ確認
            cached_rate = self.get_cached_rate(f"{from_currency}/{to_currency}")
            if cached_rate is not None:
                logger.info(f"💾 キャッシュから為替レート取得: {from_currency}/{to_currency} = {cached_rate}")
                return cached_rate
            
            # API から為替レート取得
            rate = self._fetch_rate_from_api(from_currency, to_currency)
            if rate is not None:
                # キャッシュに保存
                self._cache_rate(f"{from_currency}/{to_currency}", rate, datetime.now())
                
            return rate
            
        except Exception as e:
            logger.error(f"❌ 為替レート取得エラー: {e}")
            return None
    
    def get_cached_rate(self, currency_pair: str) -> Optional[float]:
        """キャッシュから為替レートを取得する
        
        Args:
            currency_pair: 通貨ペア（例: "USD/JPY"）
            
        Returns:
            float: キャッシュされた為替レート（期限切れの場合はNone）
        """
        if currency_pair not in self.rate_cache:
            return None
        
        cache_entry = self.rate_cache[currency_pair]
        if self._is_cache_valid(cache_entry['timestamp']):
            return cache_entry['rate']
        else:
            # 期限切れキャッシュを削除
            del self.rate_cache[currency_pair]
            return None
    
    def validate_currency_code(self, currency: str) -> bool:
        """通貨コードの妥当性を検証する
        
        Args:
            currency: 通貨コード
            
        Returns:
            bool: 有効な通貨コードかどうか
        """
        valid_currencies = {
            'JPY', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'SGD'
        }
        return currency.upper() in valid_currencies
    
    def _fetch_rate_from_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """APIから為替レートを取得する（内部メソッド）
        
        Args:
            from_currency: 元通貨コード
            to_currency: 対象通貨コード
            
        Returns:
            float: 為替レート（失敗時はNone）
        """
        try:
            # Exchange Rate API（フリー版）を使用
            url = f"{self.base_url}/{from_currency}"
            
            logger.info(f"🌐 為替レートAPI呼び出し: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'rates' in data and to_currency in data['rates']:
                rate = data['rates'][to_currency]
                logger.info(f"✅ API為替レート取得成功: {from_currency}/{to_currency} = {rate}")
                return float(rate)
            else:
                logger.warning(f"⚠️ 為替レートが見つかりません: {from_currency}/{to_currency}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"❌ API接続エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 為替レート解析エラー: {e}")
            return None
    
    def _cache_rate(self, currency_pair: str, rate: float, timestamp: datetime):
        """為替レートをキャッシュに保存する（内部メソッド）
        
        Args:
            currency_pair: 通貨ペア
            rate: 為替レート
            timestamp: 取得時刻
        """
        self.rate_cache[currency_pair] = {
            'rate': rate,
            'timestamp': timestamp
        }
        logger.debug(f"💾 為替レートキャッシュ保存: {currency_pair} = {rate}")
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """キャッシュの有効期限を確認する（内部メソッド）
        
        Args:
            timestamp: キャッシュ保存時刻
            
        Returns:
            bool: キャッシュが有効かどうか
        """
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return (datetime.now() - timestamp).seconds < self.cache_ttl 