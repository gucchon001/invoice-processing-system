import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.set_page_config(page_title="ag-grid基本動作テスト", layout="wide")

st.title("🔧 ag-grid単体技術検証")

st.markdown("### 📋 STEP 1: 最小限DataFrameテスト")

# 最小限のテストデータ
test_data = {
    'ID': [1, 2, 3],
    'ファイル名': ['test1.pdf', 'test2.pdf', 'test3.pdf'],
    'ステータス': ['成功', '失敗', '成功']
}

df = pd.DataFrame(test_data)
st.write("**テストデータ:**")
st.dataframe(df)

st.markdown("### 🔧 ag-grid基本表示テスト")

try:
    # 基本的なGridOptionsBuilder設定
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection('single', use_checkbox=True)
    gridOptions = gb.build()
    
    # ag-grid表示
    st.write("**ag-grid表示:**")
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        height=200
    )
    
    st.success("✅ ag-grid基本表示成功！")
    
    # レスポンス構造の詳細分析
    st.markdown("### 🔍 ag-gridレスポンス構造分析")
    
    st.write("**grid_responseの型:**", type(grid_response))
    st.write("**grid_responseの属性:**", dir(grid_response))
    
    # 各属性の詳細確認
    if hasattr(grid_response, 'data'):
        st.write("**data属性の型:**", type(grid_response.data))
        st.write("**data属性の内容:**")
        st.dataframe(grid_response.data)
        
        # DataFrame条件判定テスト
        st.markdown("### ⚠️ DataFrame条件判定安全性テスト")
        
        data = grid_response.data
        
        # 危険なテスト（エラーが発生するかテスト）
        try:
            st.write("**len(data)での判定:**", len(data))
            if len(data) > 0:
                st.success("✅ len(data) > 0 は安全")
        except Exception as e:
            st.error(f"❌ len(data)でエラー: {e}")
        
        try:
            st.write("**data.empty での判定:**", data.empty)
            if not data.empty:
                st.success("✅ not data.empty は安全")
        except Exception as e:
            st.error(f"❌ data.emptyでエラー: {e}")
        
        # 危険なテスト（これがエラーの原因）
        st.markdown("#### 🚨 危険な条件判定テスト")
        try:
            # これがエラーの原因かもしれない
            if data:
                st.error("🚨 if data: は実行された（エラーになるはず）")
            else:
                st.error("🚨 if data: がFalseになった")
        except Exception as e:
            st.error(f"❌ if data: でエラー発生: {e}")
        
        try:
            if not data:
                st.error("🚨 if not data: がTrueになった")
            else:
                st.error("🚨 if not data: は実行された（エラーになるはず）")
        except Exception as e:
            st.error(f"❌ if not data: でエラー発生: {e}")
    
    # 選択行処理テスト
    if hasattr(grid_response, 'selected_rows'):
        st.write("**selected_rows属性の型:**", type(grid_response.selected_rows))
        st.write("**selected_rows属性の内容:**")
        if grid_response.selected_rows is not None:
            st.write(grid_response.selected_rows)
            
            # 選択行の安全な処理テスト
            selected_rows = grid_response.selected_rows
            if isinstance(selected_rows, list) and len(selected_rows) > 0:
                st.success(f"✅ 選択行処理成功: {len(selected_rows)}行選択")
            elif isinstance(selected_rows, pd.DataFrame) and len(selected_rows) > 0:
                st.success(f"✅ 選択行処理成功: {len(selected_rows)}行選択（DataFrame）")
            else:
                st.info("📋 行が選択されていません")
        else:
            st.info("📋 selected_rowsがNone")
    
except Exception as e:
    st.error(f"❌ ag-grid表示エラー: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("### 📋 次のステップ")
st.info("""
✅ **STEP 1完了後の次のステップ:**
1. Session Stateとの組み合わせテスト
2. より複雑なDataFrameでのテスト
3. OCRテスト結果との統合テスト
4. 選択行処理の安全な実装
""") 