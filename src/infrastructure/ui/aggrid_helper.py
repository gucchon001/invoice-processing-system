"""
請求書処理自動化システム - ag-grid ヘルパー

ag-gridコンポーネントのテスト・検証機能を提供します。
データベース・スプレッドシート連携テストも含みます。
"""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, date
import json

logger = logging.getLogger(__name__)


class AgGridManager:
    """ag-grid管理クラス"""
    
    def __init__(self):
        """ag-grid管理クラスの初期化"""
        self.default_grid_options = self._get_default_grid_options()
    
    def _get_default_grid_options(self) -> Dict[str, Any]:
        """デフォルトグリッドオプション取得"""
        return {
            'enableSorting': True,
            'enableFilter': True,
            'enableColResize': True,
            'enableRowSelection': True,
            'rowSelection': 'multiple',
            'suppressRowClickSelection': True,
            'domLayout': 'normal',
            'pagination': True,
            'paginationPageSize': 20,
            'enableRangeSelection': True,
            'suppressMenuHide': True,
            'defaultColDef': {
                'resizable': True,
                'sortable': True,
                'filter': True,
                'editable': False,
                'flex': 1,
                'minWidth': 100
            }
        }
    
    def create_sample_invoice_data(self, row_count: int = 50) -> pd.DataFrame:
        """サンプル請求書データ作成"""
        import random
        from datetime import timedelta
        
        # サンプルデータの基本設定
        suppliers = [
            'Google LLC', 'Microsoft Corporation', 'Amazon Web Services',
            '株式会社Example', '有限会社サンプル', 'テスト株式会社',
            'Adobe Inc.', 'Salesforce Inc.', 'Zoom Video Communications'
        ]
        
        statuses = ['AI提案済み', '処理中', '要確認', '承認済み', '転記済み']
        currencies = ['JPY', 'USD', 'EUR']
        account_titles = ['通信費', '広告宣伝費', 'ソフトウェア費', '会議費', '研修費', '外注費']
        items = ['クラウドサービス', 'ソフトウェアライセンス', '広告費', '研修費用', 'コンサルティング']
        
        data = []
        base_date = datetime.now()
        
        for i in range(row_count):
            invoice_date = base_date - timedelta(days=random.randint(1, 90))
            due_date = invoice_date + timedelta(days=random.randint(10, 45))
            
            # 金額の計算
            amount_exclusive = random.randint(10000, 1000000)
            tax_rate = 0.1
            tax_amount = int(amount_exclusive * tax_rate)
            amount_inclusive = amount_exclusive + tax_amount
            
            row = {
                'id': i + 1,
                'file_name': f'invoice_{i+1:03d}.pdf',
                'supplier_name': random.choice(suppliers),
                'invoice_number': f'INV-{random.randint(1000, 9999)}-{i+1:03d}',
                'invoice_date': invoice_date.strftime('%Y-%m-%d'),
                'due_date': due_date.strftime('%Y-%m-%d'),
                'currency': random.choice(currencies),
                'amount_exclusive_tax': amount_exclusive,
                'tax_amount': tax_amount,
                'amount_inclusive_tax': amount_inclusive,
                'account_title': random.choice(account_titles),
                'item': random.choice(items),
                'status': random.choice(statuses),
                'created_by': f'user{random.randint(1, 5)}@example.com',
                'created_at': invoice_date.strftime('%Y-%m-%d %H:%M:%S'),
                'notes': f'請求書{i+1}の備考' if random.random() > 0.7 else ''
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def create_basic_grid(self, data: pd.DataFrame, 
                         editable_columns: List[str] = None,
                         selection_mode: str = 'multiple') -> AgGrid:
        """基本的なag-gridを作成"""
        
        gb = GridOptionsBuilder.from_dataframe(data)
        
        # 基本設定の適用
        gb.configure_default_column(
            resizable=True,
            sortable=True,
            filterable=True,
            flex=1,
            minWidth=100
        )
        
        # 編集可能列の設定
        if editable_columns:
            for col in editable_columns:
                if col in data.columns:
                    gb.configure_column(col, editable=True)
        
        # 選択モードの設定
        if selection_mode == 'multiple':
            gb.configure_selection('multiple', use_checkbox=True)
        elif selection_mode == 'single':
            gb.configure_selection('single')
        
        # ページネーション設定
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        # サイドバー設定は削除（エンタープライズ機能のため）
        # gb.configure_side_bar()
        
        grid_options = gb.build()
        
        return AgGrid(
            data,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False,
            height=400,
            theme='streamlit'
        )
    
    def create_invoice_editing_grid(self, data: pd.DataFrame) -> AgGrid:
        """請求書編集用の高機能ag-grid作成"""
        
        gb = GridOptionsBuilder.from_dataframe(data)
        
        # 基本設定
        gb.configure_default_column(
            resizable=True,
            sortable=True,
            filterable=True,
            flex=1,
            minWidth=100
        )
        
        # ID列 - 編集不可、固定
        gb.configure_column('id', editable=False, width=80, pinned='left')
        
        # ファイル名 - 編集不可
        gb.configure_column('file_name', editable=False, width=150)
        
        # 供給者名 - 編集可能、フィルタ強化
        gb.configure_column('supplier_name', editable=True, width=180, 
                          filter='agTextColumnFilter',
                          filterParams={'buttons': ['reset', 'apply']})
        
        # 請求書番号 - 編集可能
        gb.configure_column('invoice_number', editable=True, width=140)
        
        # 日付列 - 日付フィルタ
        gb.configure_column('invoice_date', editable=True, width=120,
                          filter='agDateColumnFilter')
        gb.configure_column('due_date', editable=True, width=120,
                          filter='agDateColumnFilter')
        
        # 通貨 - ドロップダウン選択
        currency_options = ['JPY', 'USD', 'EUR', 'GBP', 'CNY']
        gb.configure_column('currency', 
                          editable=True, 
                          cellEditor='agSelectCellEditor',
                          cellEditorParams={'values': currency_options},
                          width=80)
        
        # 金額列 - 数値フィルタ、フォーマット
        gb.configure_column('amount_exclusive_tax', 
                          editable=True,
                          type=['numericColumn', 'numberColumnFilter'],
                          valueFormatter="x.toLocaleString()",
                          width=140)
        gb.configure_column('tax_amount',
                          editable=True,
                          type=['numericColumn', 'numberColumnFilter'],
                          valueFormatter="x.toLocaleString()",
                          width=100)
        gb.configure_column('amount_inclusive_tax',
                          editable=True,
                          type=['numericColumn', 'numberColumnFilter'],
                          valueFormatter="x.toLocaleString()",
                          width=140)
        
        # 勘定科目 - ドロップダウン選択
        account_titles = [
            '通信費', '広告宣伝費', 'ソフトウェア費', '会議費', 
            '研修費', '外注費', '交通費', '消耗品費', '水道光熱費'
        ]
        gb.configure_column('account_title',
                          editable=True,
                          cellEditor='agSelectCellEditor',
                          cellEditorParams={'values': account_titles},
                          width=120)
        
        # 品目 - ドロップダウン選択
        items = [
            'クラウドサービス', 'ソフトウェアライセンス', '広告費',
            '研修費用', 'コンサルティング', '交通費', '消耗品'
        ]
        gb.configure_column('item',
                          editable=True,
                          cellEditor='agSelectCellEditor',
                          cellEditorParams={'values': items},
                          width=150)
        
        # ステータス - ドロップダウン選択、色分け
        status_options = ['AI提案済み', '処理中', '要確認', '承認済み', '転記済み']
        
        # ステータス列のセルスタイル設定
        status_cell_style = JsCode("""
        function(params) {
            if (params.value == 'AI提案済み') {
                return {'backgroundColor': '#e3f2fd', 'color': '#1976d2'};
            }
            if (params.value == '処理中') {
                return {'backgroundColor': '#fff3e0', 'color': '#f57c00'};
            }
            if (params.value == '要確認') {
                return {'backgroundColor': '#ffebee', 'color': '#d32f2f'};
            }
            if (params.value == '承認済み') {
                return {'backgroundColor': '#e8f5e8', 'color': '#388e3c'};
            }
            if (params.value == '転記済み') {
                return {'backgroundColor': '#f3e5f5', 'color': '#7b1fa2'};
            }
            return {};
        }
        """)
        
        gb.configure_column('status',
                          editable=True,
                          cellEditor='agSelectCellEditor',
                          cellEditorParams={'values': status_options},
                          cellStyle=status_cell_style,
                          width=100)
        
        # 作成者 - 編集不可
        gb.configure_column('created_by', editable=False, width=180)
        
        # 作成日時 - 編集不可、日時フィルタ
        gb.configure_column('created_at', editable=False, width=140,
                          filter='agDateColumnFilter')
        
        # 備考 - 編集可能、大きなテキストエリア
        gb.configure_column('notes', editable=True, width=200,
                          cellEditor='agLargeTextCellEditor',
                          cellEditorParams={'maxLength': 500})
        
        # 複数選択設定
        gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
        
        # ページネーション
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
        
        # サイドバー（フィルタ・列管理）
        gb.configure_side_bar()
        
        # グリッドオプション構築
        grid_options = gb.build()
        
        return AgGrid(
            data,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            height=500,
            theme='streamlit',
            allow_unsafe_jscode=True
        )
    
    def create_data_grid(self, data: pd.DataFrame, 
                        editable: bool = False,
                        fit_columns_on_grid_load: bool = True,
                        selection_mode: str = 'multiple',
                        use_checkbox: bool = True,
                        height: int = 400) -> AgGrid:
        """汎用データグリッドを作成（OCRテスト履歴表示用）"""
        
        gb = GridOptionsBuilder.from_dataframe(data)
        
        # 基本設定の適用
        gb.configure_default_column(
            resizable=True,
            sortable=True,
            filterable=True,
            flex=1,
            minWidth=100,
            editable=editable
        )
        
        # 選択モードの設定
        if selection_mode == 'multiple':
            gb.configure_selection('multiple', use_checkbox=use_checkbox)
        elif selection_mode == 'single':
            gb.configure_selection('single', use_checkbox=use_checkbox)
        
        # ページネーション設定
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        # サイドバー設定
        gb.configure_side_bar()
        
        grid_options = gb.build()
        
        return AgGrid(
            data,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=fit_columns_on_grid_load,
            enable_enterprise_modules=False,
            height=height,
            theme='streamlit'
        )
    
    def export_to_dataframe(self, grid_response) -> pd.DataFrame:
        """ag-gridの結果をDataFrameに変換"""
        if grid_response and 'data' in grid_response:
            return pd.DataFrame(grid_response['data'])
        return pd.DataFrame()
    
    def get_selected_rows(self, grid_response) -> List[Dict[str, Any]]:
        """選択された行を取得"""
        if grid_response and 'selected_rows' in grid_response:
            return grid_response['selected_rows']
        return []
    
    def test_database_integration(self, df: pd.DataFrame) -> Dict[str, Any]:
        """データベース統合テスト（模擬）"""
        try:
            # 実際の実装ではSupabaseとの連携を行う
            test_result = {
                'success': True,
                'operation': 'database_sync',
                'affected_rows': len(df),
                'timestamp': datetime.now().isoformat(),
                'test_mode': True,
                'message': f'{len(df)}件のデータをデータベースに同期しました（テストモード）'
            }
            
            logger.info(f"Database integration test: {test_result}")
            return test_result
            
        except Exception as e:
            logger.error(f"Database integration test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def test_spreadsheet_export(self, df: pd.DataFrame) -> Dict[str, Any]:
        """スプレッドシートエクスポートテスト（模擬）"""
        try:
            # 実際の実装ではGoogle Sheets APIとの連携を行う
            test_result = {
                'success': True,
                'operation': 'spreadsheet_export',
                'exported_rows': len(df),
                'exported_columns': len(df.columns),
                'timestamp': datetime.now().isoformat(),
                'test_mode': True,
                'file_format': 'Google Sheets',
                'message': f'{len(df)}件のデータをGoogleスプレッドシートに出力しました（テストモード）'
            }
            
            logger.info(f"Spreadsheet export test: {test_result}")
            return test_result
            
        except Exception as e:
            logger.error(f"Spreadsheet export test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


def get_aggrid_manager() -> AgGridManager:
    """ag-gridマネージャーのシングルトン取得"""
    if 'aggrid_manager' not in st.session_state:
        st.session_state.aggrid_manager = AgGridManager()
    return st.session_state.aggrid_manager


def test_aggrid_connection() -> bool:
    """ag-grid動作テスト"""
    try:
        # シンプルなテストデータで動作確認
        test_data = pd.DataFrame({
            'テスト列1': ['値1', '値2', '値3'],
            'テスト列2': [1, 2, 3],
            'テスト列3': [True, False, True]
        })
        
        gb = GridOptionsBuilder.from_dataframe(test_data)
        gb.configure_selection('single')
        grid_options = gb.build()
        
        # ag-gridコンポーネントの作成テスト
        # 実際の表示はしない（テストのみ）
        return True
        
    except Exception as e:
        logger.error(f"ag-grid connection test failed: {e}")
        return False 