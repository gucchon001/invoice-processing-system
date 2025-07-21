import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import time

st.set_page_config(page_title="ag-grid + Session State テスト", layout="wide")

st.title("🔧 ag-grid + Session State 組み合わせテスト")

# Session State初期化
if 'complex_data' not in st.session_state:
    st.session_state.complex_data = None

if 'grid_selection_history' not in st.session_state:
    st.session_state.grid_selection_history = []

if 'test_counter' not in st.session_state:
    st.session_state.test_counter = 0

st.markdown("### 📋 STEP 2: Session State + ag-grid 統合テスト")

# 複雑なテストデータ生成
col1, col2 = st.columns([1, 1])

with col1:
    data_size = st.slider("データ件数", min_value=10, max_value=500, value=50)
    
    if st.button("🎲 複雑なテストデータ生成"):
        st.session_state.test_counter += 1
        
        # OCRテスト結果のような複雑なデータを模擬
        np.random.seed(42)  # 再現性のため
        
        complex_data = []
        for i in range(data_size):
            complex_data.append({
                'ID': i + 1,
                'ファイル名': f'請求書_{i+1:03d}.pdf',
                '請求元': np.random.choice(['株式会社A', '有限会社B', 'C商事', 'D工業', '（株）E']),
                '請求書番号': f'INV-{2024}-{i+1:04d}',
                '税込金額': np.random.randint(10000, 1000000),
                '通貨': np.random.choice(['JPY', 'USD', 'EUR'], p=[0.8, 0.15, 0.05]),
                '発行日': pd.date_range('2024-01-01', periods=data_size, freq='D')[i].strftime('%Y-%m-%d'),
                '検証状況': np.random.choice(['✅ 正常', '❌ エラー', '⚠️ 警告'], p=[0.7, 0.2, 0.1]),
                '完全性スコア': round(np.random.uniform(60.0, 99.9), 1),
                'エラー数': np.random.randint(0, 5),
                '警告数': np.random.randint(0, 3),
                'ファイルサイズ': f"{np.random.randint(100, 5000):,} bytes",
                '処理時間': round(np.random.uniform(1.2, 8.7), 1),
                # 複雑なネストしたデータ
                'メタデータ': {
                    'confidence': round(np.random.uniform(0.7, 0.99), 2),
                    'model_version': '2.0-flash',
                    'extraction_method': 'gemini'
                }
            })
        
        # DataFrameに変換してSession Stateに保存
        st.session_state.complex_data = pd.DataFrame(complex_data)
        st.success(f"✅ {data_size}件の複雑なテストデータを生成しました（テスト#{st.session_state.test_counter}）")

with col2:
    st.write("**Session State情報:**")
    st.write(f"テスト実行回数: {st.session_state.test_counter}")
    st.write(f"データ件数: {len(st.session_state.complex_data) if st.session_state.complex_data is not None else 0}")
    st.write(f"選択履歴件数: {len(st.session_state.grid_selection_history)}")

# Session State データの表示とag-grid統合テスト
if st.session_state.complex_data is not None:
    st.markdown("### 🔧 ag-grid + Session State データ表示テスト")
    
    df = st.session_state.complex_data
    st.info(f"📊 Session Stateから{len(df)}件のデータを読み込み")
    
    # DataFrame安全性テスト
    st.markdown("#### ⚠️ DataFrame条件判定安全性テスト")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        try:
            result_len = len(df) > 0
            st.success(f"✅ len(df) > 0: {result_len}")
        except Exception as e:
            st.error(f"❌ len(df)エラー: {e}")
    
    with col_test2:
        try:
            result_empty = not df.empty
            st.success(f"✅ not df.empty: {result_empty}")
        except Exception as e:
            st.error(f"❌ df.emptyエラー: {e}")
    
    with col_test3:
        try:
            # 危険なテスト
            if df:
                st.error("🚨 if df: が実行された（エラーになるはず）")
        except Exception as e:
            st.error(f"❌ if df: エラー発生: {e}")
    
    # ag-gridで表示
    try:
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_column("完全性スコア", type=["numericColumn", "numberColumnFilter"], precision=1)
        gb.configure_column("税込金額", type=["numericColumn", "numberColumnFilter"], valueFormatter="x.toLocaleString()")
        gridOptions = gb.build()
        
        st.markdown("#### 📊 ag-grid複雑データ表示")
        grid_response = AgGrid(
            df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            height=400
        )
        
        st.success("✅ 複雑なデータでag-grid表示成功！")
        
        # 選択行処理テスト
        st.markdown("#### 🔍 選択行処理 + Session State テスト")
        
        if hasattr(grid_response, 'selected_rows') and grid_response.selected_rows is not None:
            selected_rows = grid_response.selected_rows
            
            # 選択行の安全な処理
            if isinstance(selected_rows, list):
                selected_count = len(selected_rows)
            elif isinstance(selected_rows, pd.DataFrame):
                selected_count = len(selected_rows)
            else:
                selected_count = 0
            
            if selected_count > 0:
                st.success(f"✅ {selected_count}行が選択されています")
                
                # Session Stateに選択履歴を保存
                selection_record = {
                    'timestamp': time.strftime('%H:%M:%S'),
                    'test_number': st.session_state.test_counter,
                    'selected_count': selected_count,
                    'data_size': len(df)
                }
                
                # 履歴重複防止
                if not st.session_state.grid_selection_history or st.session_state.grid_selection_history[-1] != selection_record:
                    st.session_state.grid_selection_history.append(selection_record)
                
                # 選択されたデータの詳細表示
                with st.expander(f"📋 選択されたデータ詳細 ({selected_count}件)", expanded=False):
                    if isinstance(selected_rows, pd.DataFrame):
                        st.dataframe(selected_rows)
                    else:
                        st.dataframe(pd.DataFrame(selected_rows))
                
                # データ操作テスト
                col_op1, col_op2, col_op3 = st.columns(3)
                
                with col_op1:
                    if st.button("📊 選択データ統計"):
                        if isinstance(selected_rows, pd.DataFrame):
                            selected_df = selected_rows
                        else:
                            selected_df = pd.DataFrame(selected_rows)
                        
                        avg_score = selected_df['完全性スコア'].mean()
                        total_amount = selected_df['税込金額'].sum()
                        
                        st.metric("平均完全性スコア", f"{avg_score:.1f}%")
                        st.metric("選択データ合計金額", f"¥{total_amount:,}")
                
                with col_op2:
                    if st.button("💾 Session Stateに追加保存"):
                        # 選択されたデータをSession Stateに保存
                        if 'saved_selections' not in st.session_state:
                            st.session_state.saved_selections = []
                        
                        save_data = {
                            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'selection_count': selected_count,
                            'data': selected_rows if isinstance(selected_rows, list) else selected_rows.to_dict('records')
                        }
                        
                        st.session_state.saved_selections.append(save_data)
                        st.success(f"✅ {selected_count}件をSession Stateに保存しました")
                
                with col_op3:
                    if st.button("🔄 選択データ再処理テスト"):
                        # 実際のOCRシステムのような複雑な処理をシミュレート
                        processing_success = True
                        try:
                            if isinstance(selected_rows, pd.DataFrame):
                                test_df = selected_rows.copy()
                            else:
                                test_df = pd.DataFrame(selected_rows)
                            
                            # 複雑な処理のシミュレート
                            test_df['再処理フラグ'] = True
                            test_df['再処理時刻'] = time.strftime('%H:%M:%S')
                            
                            st.success(f"✅ {len(test_df)}件の再処理シミュレート完了")
                            
                        except Exception as e:
                            st.error(f"❌ 再処理中にエラー: {e}")
                            processing_success = False
            else:
                st.info("📋 行を選択してください（チェックボックスをクリック）")
        else:
            st.info("📋 選択機能が利用できません")
    
    except Exception as e:
        st.error(f"❌ ag-grid表示エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

# Session State状態の詳細表示
st.markdown("### 📊 Session State状態監視")

if st.session_state.grid_selection_history:
    st.markdown("#### 🕐 選択履歴")
    history_df = pd.DataFrame(st.session_state.grid_selection_history)
    st.dataframe(history_df, use_container_width=True)

if 'saved_selections' in st.session_state and st.session_state.saved_selections:
    st.markdown("#### 💾 保存された選択データ")
    st.write(f"保存件数: {len(st.session_state.saved_selections)}")
    
    for i, saved in enumerate(st.session_state.saved_selections[-3:]):  # 最新3件表示
        with st.expander(f"💾 保存#{len(st.session_state.saved_selections)-i}: {saved['saved_at']} ({saved['selection_count']}件)"):
            st.json(saved['data'][:2])  # 最初の2件のみ表示

# リセット機能
st.markdown("### 🔄 テストリセット")
col_reset1, col_reset2, col_reset3 = st.columns(3)

with col_reset1:
    if st.button("🗑️ データクリア"):
        st.session_state.complex_data = None
        st.success("✅ テストデータをクリアしました")

with col_reset2:
    if st.button("📝 履歴クリア"):
        st.session_state.grid_selection_history = []
        if 'saved_selections' in st.session_state:
            del st.session_state.saved_selections
        st.success("✅ 選択履歴をクリアしました")

with col_reset3:
    if st.button("🔄 全リセット"):
        st.session_state.clear()
        st.success("✅ 全Session Stateをリセットしました")
        st.rerun()

st.markdown("### 📋 テスト結果評価")
st.info("""
✅ **成功すべき項目:**
- 複雑なDataFrameの生成と表示
- Session Stateでのデータ保持
- ag-gridでの安全な選択行処理
- DataFrame条件判定の安全性
- Session State + ag-gridの組み合わせ動作

❌ **エラーが出たら問題:**
- DataFrame条件判定エラー
- ag-grid表示エラー
- Session State読み書きエラー
- 選択行処理エラー
""") 