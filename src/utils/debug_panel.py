"""
デバッグパネル - Streamlitアプリ内でログとデバッグ設定を管理

設定ファイルの内容を表示し、一時的な設定変更も可能にする。
"""

import streamlit as st
import configparser
import os
from pathlib import Path
import tempfile
from .log_config import get_log_config, setup_logging


def render_debug_panel():
    """デバッグパネルをレンダリング"""
    if 'show_debug_panel' not in st.session_state:
        st.session_state.show_debug_panel = False
        
    # デバッグパネルの表示切り替え
    with st.sidebar:
        if st.button("🔧 デバッグパネル" + (" 🔽" if st.session_state.show_debug_panel else " ▶️")):
            st.session_state.show_debug_panel = not st.session_state.show_debug_panel
            
    if st.session_state.show_debug_panel:
        render_debug_content()


def render_debug_content():
    """デバッグパネルの内容をレンダリング"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔧 デバッグ設定")
        
        try:
            log_config = get_log_config()
            
            # 現在の設定表示
            with st.expander("📊 現在の設定", expanded=True):
                st.markdown("**ログレベル:**")
                current_level = log_config.config.get('logging', 'log_level', fallback='INFO')
                st.code(current_level)
                
                st.markdown("**デバッグモード:**")
                debug_mode = log_config.is_debug_mode()
                st.code(str(debug_mode))
                
                st.markdown("**環境:**")
                environment = log_config.get_environment()
                st.code(environment)
                
                st.markdown("**ログファイル出力:**")
                file_logging = log_config.config.getboolean('logging', 'enable_file_logging', fallback=True)
                st.code(str(file_logging))
                
            # 一時的な設定変更
            with st.expander("⚙️ 一時設定変更"):
                st.markdown("**注意:** この変更は現在のセッションのみ有効です")
                
                # ログレベル変更
                new_log_level = st.selectbox(
                    "ログレベル",
                    options=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    index=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].index(current_level),
                    key="temp_log_level"
                )
                
                # デバッグモード切り替え
                new_debug_mode = st.checkbox(
                    "デバッグモード",
                    value=debug_mode,
                    key="temp_debug_mode"
                )
                
                # デバッグカテゴリ
                st.markdown("**デバッグカテゴリ:**")
                categories = ['database', 'ai', 'gdrive', 'streamlit']
                debug_categories = {}
                
                for category in categories:
                    current_value = log_config.is_debug_enabled(category)
                    debug_categories[category] = st.checkbox(
                        f"{category.upper()} デバッグ",
                        value=current_value,
                        key=f"temp_{category}_debug"
                    )
                
                # 設定適用ボタン
                if st.button("🔄 一時設定を適用", key="apply_temp_settings"):
                    apply_temp_settings(new_log_level, new_debug_mode, debug_categories)
                    st.success("一時設定が適用されました")
                    st.experimental_rerun()
                    
            # ログファイル表示
            with st.expander("📋 ログファイル"):
                display_log_files(log_config)
                
            # 設定ファイル表示
            with st.expander("📄 設定ファイル内容"):
                display_config_file(log_config)
                
        except Exception as e:
            st.error(f"デバッグパネルでエラー: {e}")


def apply_temp_settings(log_level: str, debug_mode: bool, debug_categories: dict):
    """一時的な設定変更を適用"""
    try:
        log_config = get_log_config()
        
        # 設定を一時的に変更
        log_config.config.set('logging', 'log_level', log_level)
        log_config.config.set('debug', 'debug_mode', str(debug_mode).lower())
        
        for category, enabled in debug_categories.items():
            log_config.config.set('debug', f'{category}_debug', str(enabled).lower())
            
        # ログ設定を再セットアップ
        log_config._setup_logging()
        
        # セッション状態に保存
        st.session_state.temp_settings_applied = True
        
    except Exception as e:
        st.error(f"設定適用エラー: {e}")


def display_log_files(log_config):
    """ログファイルの内容を表示"""
    try:
        log_file_path = log_config.config.get('logging', 'log_file_path', fallback='logs/app.log')
        
        if os.path.exists(log_file_path):
            # ファイルサイズ表示
            file_size = os.path.getsize(log_file_path)
            st.markdown(f"**ファイルサイズ:** {file_size:,} bytes")
            
            # 最新のログを表示
            lines_to_show = st.slider("表示行数", 10, 200, 50, key="log_lines")
            
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-lines_to_show:] if len(lines) > lines_to_show else lines
                    
                if recent_lines:
                    st.code(''.join(recent_lines), language='text')
                else:
                    st.info("ログファイルは空です")
                    
            except UnicodeDecodeError:
                # UTF-8で読めない場合はshift_jisで試行
                with open(log_file_path, 'r', encoding='shift_jis') as f:
                    lines = f.readlines()
                    recent_lines = lines[-lines_to_show:] if len(lines) > lines_to_show else lines
                    st.code(''.join(recent_lines), language='text')
                    
            # ログクリアボタン
            if st.button("🗑️ ログファイルをクリア", key="clear_log"):
                try:
                    open(log_file_path, 'w').close()
                    st.success("ログファイルがクリアされました")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"ログクリアエラー: {e}")
        else:
            st.info("ログファイルが見つかりません")
            
    except Exception as e:
        st.error(f"ログファイル表示エラー: {e}")


def display_config_file(log_config):
    """設定ファイルの内容を表示"""
    try:
        if os.path.exists(log_config.config_path):
            with open(log_config.config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            st.code(config_content, language='ini')
            
            # 設定ファイル編集
            if st.button("📝 設定ファイルを編集", key="edit_config"):
                st.session_state.show_config_editor = True
                
            if st.session_state.get('show_config_editor', False):
                render_config_editor(log_config.config_path)
        else:
            st.warning("設定ファイルが見つかりません")
            
    except Exception as e:
        st.error(f"設定ファイル表示エラー: {e}")


def render_config_editor(config_path: str):
    """設定ファイルエディター"""
    st.markdown("### 📝 設定ファイル編集")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
            
        # テキストエリアで編集
        new_content = st.text_area(
            "設定内容",
            value=current_content,
            height=300,
            key="config_editor"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 保存", key="save_config"):
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    st.success("設定ファイルが保存されました")
                    st.session_state.show_config_editor = False
                    # ログ設定を再読み込み
                    setup_logging()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"保存エラー: {e}")
                    
        with col2:
            if st.button("❌ キャンセル", key="cancel_edit"):
                st.session_state.show_config_editor = False
                st.experimental_rerun()
                
        with col3:
            if st.button("🔄 リロード", key="reload_config"):
                try:
                    setup_logging()
                    st.success("設定が再読み込みされました")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"リロードエラー: {e}")
                    
    except Exception as e:
        st.error(f"エディターエラー: {e}")


# デバッグ情報の表示
def show_debug_info():
    """デバッグ情報を表示"""
    try:
        log_config = get_log_config()
        
        if log_config.is_debug_mode():
            with st.expander("🐛 デバッグ情報", expanded=False):
                st.markdown("**セッション状態:**")
                st.json(dict(st.session_state))
                
                st.markdown("**環境変数:**")
                env_vars = {k: v for k, v in os.environ.items() if not k.startswith('_')}
                st.json(env_vars)
                
                st.markdown("**設定情報:**")
                config_dict = {}
                for section in log_config.config.sections():
                    config_dict[section] = dict(log_config.config[section])
                st.json(config_dict)
                
    except Exception as e:
        st.error(f"デバッグ情報表示エラー: {e}") 