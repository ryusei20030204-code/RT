import streamlit as st
import pandas as pd
import datetime
import os
import time

# ==========================================
# 1. アプリ設定 & 初期化
# ==========================================
st.set_page_config(page_title="院試マッチ", page_icon="🎓", layout="wide")

# アップロード保存用フォルダ
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# コメント保存用ファイル
COMMENTS_FILE = "comments.csv"

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = 'search'
if 'selected_lab' not in st.session_state:
    st.session_state.selected_lab = None

# ==========================================
# 2. データ読み書き関数
# ==========================================
@st.cache_data
def load_data():
    try:
        # CSV読み込み (新しい11項目に対応)
        df = pd.read_csv("data.csv", encoding='utf-8_sig')
        return df
    except FileNotFoundError:
        return None

# コメント読み込み
def load_comments():
    if os.path.exists(COMMENTS_FILE):
        return pd.read_csv(COMMENTS_FILE, encoding='utf-8_sig')
    else:
        return pd.DataFrame(columns=["研究室名", "名前", "日付", "内容"])

# コメント保存
def save_comment(lab_name, user_name, text):
    new_data = pd.DataFrame({
        "研究室名": [lab_name],
        "名前": [user_name],
        "日付": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
        "内容": [text]
    })
    if os.path.exists(COMMENTS_FILE):
        new_data.to_csv(COMMENTS_FILE, mode='a', header=False, index=False, encoding='utf-8_sig')
    else:
        new_data.to_csv(COMMENTS_FILE, index=False, encoding='utf-8_sig')

# ファイル保存
def save_uploaded_file(uploaded_file, lab_name):
    file_path = os.path.join(UPLOAD_DIR, f"{lab_name}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

df = load_data()

# ==========================================
# 3. 画面定義
# ==========================================

# --- サイドバー: 研究室データの追加機能 ---
def show_sidebar_add_lab():
    with st.sidebar:
        st.header("➕ データの追加")
        st.caption("未登録の研究室を見つけたら、ここから追加してください。")
        
        with st.form(key='add_lab_form'):
            univ = st.selectbox("大学名", ["東京大学", "京都大学", "東京科学大学", "大阪大学", "東北大学", "北海道大学", "九州大学", "名古屋大学", "その他"])
            dept = st.text_input("研究科", placeholder="例: 工学系研究科")
            lab = st.text_input("研究室名", placeholder="例: 佐藤研究室")
            keyword = st.text_input("キーワード", placeholder="例: AI, 制御, 建築")
            book = st.text_input("指定教科書", placeholder="教科書名")
            exam_subj = st.text_input("試験科目", placeholder="例: 数学, 英語")
            
            # その他の項目（簡易入力のため必須にしない）
            english_req = st.text_input("英語要件", placeholder="例: TOEIC 700点")
            
            submit_btn = st.form_submit_button("データベースに登録")
            
            if submit_btn and lab:
                # data.csvの列順序に合わせてデータを作成
                new_row = pd.DataFrame({
                    "大学名": [univ],
                    "研究科": [dept],
                    "研究室名": [lab],
                    "キーワード": [keyword],
                    "指定教科書": [book],
                    "Amazonリンク": ["#"], # ダミー
                    "試験科目": [exam_subj],
                    "公式リンク": ["#"], # ダミー
                    "英語要件": [english_req if english_req else "情報募集中"],
                    "試験日程": ["要確認"],
                    "過去問入手方法": ["掲示板で聞いてみよう"]
                })
                
                # data.csvに追記
                new_row.to_csv("data.csv", mode='a', header=False, index=False, encoding='utf-8_sig')
                
                # キャッシュをクリアしてリロード
                st.cache_data.clear()
                st.success(f"「{lab}」を追加しました！")
                time.sleep(1)
                st.rerun()

# --- 検索画面 ---
def show_search_page():
    st.title("院試マッチ 🎓")
    st.caption("志望大学の院試情報を検索し、過去問・解答を共有しよう！")
    
    if df is None:
        st.error("⚠️ エラー: data.csv が見つかりません。")
        return

    st.divider()

    # 検索フィルター
    col1, col2 = st.columns([1, 2])
    with col1:
        univ_list = df['大学名'].unique()
        selected_univ = st.multiselect("📍 大学で絞り込み", univ_list, default=univ_list)
    with col2:
        keyword = st.text_input("🔍 キーワード検索", placeholder="例: 化学工学, プロセス制御, 熱力学")

    # フィルタリング処理
    filtered_df = df[df['大学名'].isin(selected_univ)]
    if keyword:
        keywords = keyword.split()
        for k in keywords:
            filtered_df = filtered_df[
                filtered_df['キーワード'].str.contains(k, case=False) | 
                filtered_df['研究室名'].str.contains(k, case=False) |
                filtered_df.get('試験科目', pd.Series()).str.contains(k, case=False)
            ]

    st.markdown(f"### 検索結果: {len(filtered_df)} 件")

    # 結果カード表示
    for index, row in filtered_df.iterrows():
        with st.container():
            st.markdown(f"#### 🏫 {row['大学名']} | {row['研究室名']}")
            st.text(f"分野: {row['キーワード']}")
            
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.info(f"📚 **教科書:** {row.get('指定教科書', '-')}")
            with c2:
                st.success(f"📝 **科目:** {row.get('試験科目', '-')}")
            with c3:
                if st.button("詳細・対策へ ➡️", key=f"btn_{index}"):
                    st.session_state.selected_lab = row
                    st.session_state.page = 'detail'
                    st.rerun()
            st.divider()

# --- 詳細画面 ---
def show_detail_page():
    row = st.session_state.selected_lab
    lab_name = row['研究室名']
    
    if st.button("⬅️ 検索に戻る"):
        st.session_state.page = 'search'
        st.session_state.selected_lab = None
        st.rerun()

    st.title(f"{row['研究室名']}")
    st.markdown(f"**{row['大学名']} {row['研究科']}**")

    # タブ構成
    tab1, tab2, tab3 = st.tabs(["📚 受験情報", "💬 掲示板", "📂 ファイル共有"])

    # --- タブ1: 受験情報 ---
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📝 試験概要")
            st.write(f"**試験科目:** {row.get('試験科目', '情報なし')}")
            st.write(f"**英語要件:** {row.get('英語要件', '情報なし')}")
            st.write(f"**試験日程:** {row.get('試験日程', '要確認')}")
            
        with col2:
            st.markdown("### 📚 対策リソース")
            st.warning(f"**指定教科書:** {row.get('指定教科書', '情報なし')}")
            st.markdown(f"👉 [Amazonで探す]({row.get('Amazonリンク', '#')})")
            st.info(f"**過去問入手:** {row.get('過去問入手方法', '情報なし')}")
        
        st.divider()
        if '公式リンク' in row and row['公式リンク'] != "#":
            st.link_button("大学公式サイトへ", row['公式リンク'])

    # --- タブ2: 掲示板 ---
    with tab2:
        st.header("💬 みんなの対策・情報共有")
        st.caption("匿名で書き込めます。")
        
        with st.form(key='comment_form'):
            c1, c2 = st.columns([1, 3])
            with c1:
                user_name = st.text_input("名前", "名無し")
            with c2:
                comment_text = st.text_input("コメント", placeholder="質問や情報をシェアしよう")
            submit_btn = st.form_submit_button("書き込む")

        if submit_btn and comment_text:
            save_comment(lab_name, user_name, comment_text)
            st.success("投稿しました！")
            time.sleep(0.5)
            st.rerun()

        comments_df = load_comments()
        lab_comments = comments_df[comments_df["研究室名"] == lab_name]
        
        if not lab_comments.empty:
            for _, c in lab_comments.iloc[::-1].iterrows():
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <small style="color: grey;">{c['日付']} : {c['名前']}</small><br>
                    {c['内容']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("まだ投稿はありません。")

    # --- タブ3: ファイル共有 ---
    with tab3:
        st.header("📂 過去問・解答ファイルの共有")
        st.markdown("PDFや画像をアップロードして共有できます。")
        
        uploaded_file = st.file_uploader("ファイルをアップロード", type=['pdf', 'png', 'jpg', 'jpeg'])
        
        if uploaded_file is not None:
            if st.button("アップロードする"):
                save_uploaded_file(uploaded_file, lab_name)
                st.toast(f"✅ 保存しました！: {uploaded_file.name}")
                time.sleep(1)
                st.rerun()
        
        st.divider()
        st.subheader("📥 共有ファイル一覧")
        
        if os.path.exists(UPLOAD_DIR):
            files = os.listdir(UPLOAD_DIR)
            lab_files = [f for f in files if f.startswith(lab_name)]

            if lab_files:
                for f in lab_files:
                    file_path = os.path.join(UPLOAD_DIR, f)
                    with open(file_path, "rb") as file:
                        display_name = f.replace(lab_name + '_', '')
                        st.download_button(
                            label=f"📄 {display_name}",
                            data=file,
                            file_name=f,
                            mime="application/octet-stream"
                        )
            else:
                st.caption("まだファイルはありません。")

# ==========================================
# 4. アプリ実行
# ==========================================
if st.session_state.page == 'search':
    show_sidebar_add_lab() # サイドバーを表示
    show_search_page()
elif st.session_state.page == 'detail':
    # 詳細画面ではサイドバーを隠すか、検索に戻るボタンだけにする（今回はシンプルに非表示）
    show_detail_page()