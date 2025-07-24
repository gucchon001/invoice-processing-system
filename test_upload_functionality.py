#!/usr/bin/env python3
"""
ファイルアップロード機能診断テスト

Streamlitアプリ内でのファイルアップロード機能を診断
"""

import streamlit as st
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

def main():
    st.title("🔍 ファイルアップロード機能診断")
    st.markdown("---")
    
    st.markdown("## 📤 複数ファイルアップロードテスト")
    
    # 複数ファイルアップローダー
    uploaded_files = st.file_uploader(
        "PDFファイルを選択してください（複数選択対応テスト）",
        type=['pdf'],
        accept_multiple_files=True,
        key="diagnosis_upload_files",
        help="Ctrlキーを押しながらクリックまたはShift+クリックで複数選択"
    )
    
    # 診断結果表示
    st.markdown("## 📊 診断結果")
    
    if uploaded_files:
        # 基本情報
        st.success(f"✅ ファイル検出: **{len(uploaded_files)}件**")
        
        # 詳細情報表示
        for i, file in enumerate(uploaded_files, 1):
            with st.expander(f"ファイル {i}: {file.name}"):
                st.write(f"**ファイル名**: {file.name}")
                st.write(f"**ファイルサイズ**: {len(file.getvalue()):,} bytes")
                st.write(f"**ファイルタイプ**: {file.type}")
        
        # バッチ処理テスト
        st.markdown("### 🔧 バッチ処理テスト")
        
        if st.button("バッチ処理シミュレーション実行", type="primary"):
            with st.spinner("バッチ処理テスト中..."):
                try:
                    # files_data形式に変換（実際の処理と同じ）
                    files_data = []
                    for uploaded_file in uploaded_files:
                        pdf_data = uploaded_file.read()
                        files_data.append({
                            'filename': uploaded_file.name,
                            'data': pdf_data,
                            'size': len(pdf_data)
                        })
                    
                    st.success("✅ バッチ処理データ変換成功")
                    
                    # 変換結果表示
                    for i, file_data in enumerate(files_data, 1):
                        st.write(f"**{i}.** {file_data['filename']} ({file_data['size']:,} bytes)")
                    
                    # 統一ワークフローエンジンテスト
                    st.markdown("### ⚙️ 統一ワークフローエンジン接続テスト")
                    
                    try:
                        from infrastructure.ai.gemini_helper import get_gemini_api
                        from infrastructure.storage.google_drive_helper import get_google_drive
                        from infrastructure.database.database import get_database
                        from core.workflows.unified_workflow_engine import UnifiedWorkflowEngine
                        
                        # サービス初期化
                        ai_service = get_gemini_api()
                        storage_service = get_google_drive()
                        database_service = get_database()
                        
                        # 統一ワークフローエンジン作成
                        engine = UnifiedWorkflowEngine(
                            ai_service=ai_service,
                            storage_service=storage_service,
                            database_service=database_service
                        )
                        
                        st.success("✅ 統一ワークフローエンジン初期化成功")
                        
                        # バッチ処理メソッド確認
                        if hasattr(engine, 'process_batch_files'):
                            st.success("✅ process_batch_files メソッド存在確認")
                        else:
                            st.error("❌ process_batch_files メソッドが見つかりません")
                        
                    except Exception as e:
                        st.error(f"❌ 統一ワークフローエンジンエラー: {e}")
                    
                except Exception as e:
                    st.error(f"❌ バッチ処理テストエラー: {e}")
    
    else:
        st.info("📁 ファイルを選択してください")
        
        # ヘルプ情報
        st.markdown("### 💡 複数ファイル選択方法")
        st.markdown("""
        **複数ファイルを選択する方法**:
        1. **Windowsの場合**: Ctrlキーを押しながらファイルをクリック
        2. **Macの場合**: Cmdキーを押しながらファイルをクリック
        3. **連続選択**: 最初のファイルをクリック → Shiftキーを押しながら最後のファイルをクリック
        """)
    
    # システム情報
    st.markdown("---")
    st.markdown("## 🔧 システム情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Streamlitバージョン**")
        st.code(st.__version__)
        
    with col2:
        st.markdown("**複数ファイル対応**")
        st.code("accept_multiple_files=True")

if __name__ == "__main__":
    main() 