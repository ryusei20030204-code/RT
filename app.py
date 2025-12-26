import streamlit as st
import pandas as pd
import datetime
import os
import time
import gspread
from google.oauth2.service_account import Credentials # 新しい認証方法

# ==========================================
# 1. アプリ設定 & 初期化
# ==========================================
st.set_page_config(page_title="院試マッチ", page_icon="🎓", layout="wide")

# 定数
UPLOAD_DIR = "uploads"
SHEET_NAME = "inshi_database"  # スプレッドシートの名前

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if 'page' not in st.session_state:
    st.session_state.page = 'search'
if 'selected_lab' not in st.session_state:
    st.session_state.selected_lab = None

# ==========================================
# 2. Google Sheets 接続関数 (修正版)
# ==========================================
def connect_to_gsheet():
    try:
        # スコープ（権限）の設定
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # パターンA: ローカル環境 (service_account.jsonがある場合)
        if os.path.exists("service_account.json"):
            gc = gspread.service_account(filename="service_account.json")
        
        # パターンB: Streamlit Cloud環境 (後で設定します)
        elif "gcp_service_account" in st.secrets:
            key_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
            gc = gspread.authorize(creds)
        else:
            return None

        # スプレッドシートを開く
        spreadsheet = gc.open(SHEET_NAME)
        return spreadsheet
        
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        return None

# ==========================================
# 3. データ読み書き関数
# ==========================================
# 研究室データの読み込み
@st.cache_data(ttl=60)
def load_data():
    sh = connect_to_gsheet()
    if sh:
        try:
            worksheet = sh.worksheet("data")
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except:
            return pd.DataFrame()
    return pd.DataFrame() # 接続失敗時などは空データ

# コメントの読み込み
def load_comments():
    sh = connect_to_gsheet()
    if sh:
        try:
            worksheet = sh.worksheet("comments")
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except:
            pass
    return pd.DataFrame(columns=["研究室名", "名前", "日付", "内容"])

# コメント保存
def save_comment(lab_name, user_name, text):
    sh = connect_to_gsheet()
    if sh:
        worksheet = sh.worksheet("comments")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        worksheet.append_row([lab_name, user_name, current_time, text])

# 研究室データの追加
def add_new_lab(data_dict):
    sh = connect_to_gsheet()
    if sh:
        worksheet = sh.worksheet("data")
        row = [
            data_dict.get("大学名"), data_dict.get("研究科"), data_dict.get("研究室名"),
            data_dict.get("キーワード"), data_dict.get("指定教科書"), data_dict.get("Amazonリンク"),
            data_dict.get("試験科目"), data_dict.get("公式リンク"), data_dict.get("英語要件"),
            data_dict.get("試験日程"), data_dict.get("過去問入手方法")
        ]
        worksheet.append_row(row)

# ファイル保存 (一時保存)
def save_uploaded_file(uploaded_file, lab_name):
    file_path = os.path.join(UPLOAD_DIR, f"{lab_name}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

df = load_data()

# ==========================================
# 4. 画面定義
# ==========================================
# サイドバー: データの追加
def show_sidebar_add_lab():
    with st.sidebar:
        st.header("➕ データの追加")
        st.caption("Googleスプレッドシートに保存されます！")
        
        with st.form(key='add_lab_form'):
            univ = st.selectbox("大学名", ["東京大学", "京都大学", "東京科学大学", "大阪大学", "東北大学", "北海道大学", "九州大学", "名古屋大学", "その他"])
            dept = st.text_input("研究科", placeholder="例: 工学系研究科")
            lab = st.text_input("研究室名", placeholder="例: 佐藤研究室")
            keyword = st.text_input("キーワード", placeholder="例: AI, 制御")
            book = st.text_input("指定教科書")
            exam_subj = st.text_input("試験科目")
            english_req = st.text_input("英語要件")
            
            submit_btn = st.form_submit_button("データベースに登録")
            
            if submit_btn and lab:
                new_data = {
                    "大学名": univ, "研究科": dept, "研究室名": lab,
                    "キーワード": keyword, "指定教科書": book,
                    "Amazonリンク": "#", "試験科目": exam_subj,
                    "公式リンク": "#", "英語要件": english_req if english_req else "募集中",
                    "試験日程": "要確認", "過去問入手方法": "掲示板へ"
                }
                add_new_lab(new_data)
                st.cache_data.clear()
                st.success(f"「{lab}」を追加しました！")
                time.sleep(1)
                st.rerun()

# 検索画面
def show_search_page():
    st.title("院試マッチ 🎓 (DB連携版)")
    
    if df.empty:
        st.warning("⚠️ データが見つかりません。「service_account.json」があるか、シート名「inshi_database」が正しいか確認してください。")
    else:
        # 検索フィルター
        col1, col2 = st.columns([1, 2])
        with col1:
            univ_list = df['大学名'].unique()
            selected_univ = st.multiselect("📍 大学で絞り込み", univ_list, default=univ_list)
        with col2:
            keyword = st.text_input("🔍 キーワード検索")

        filtered_df = df[df['大学名'].isin(selected_univ)]
        if keyword:
            for k in keyword.split():
                filtered_df = filtered_df[
                    filtered_df['キーワード'].astype(str).str.contains(k, case=False) | 
                    filtered_df['研究室名'].astype(str).str.contains(k, case=False)
                ]

        st.markdown(f"### 検索結果: {len(filtered_df)} 件")
        for index, row in filtered_df.iterrows():
            with st.container():
                st.markdown(f"#### 🏫 {row['大学名']} | {row['研究室名']}")
                st.text(f"分野: {row['キーワード']}")
                if st.button("詳細・対策へ ➡️", key=f"btn_{index}"):
                    st.session_state.selected_lab = row
                    st.session_state.page = 'detail'
                    st.rerun()
                st.divider()

# 詳細画面
def show_detail_page():
    row = st.session_state.selected_lab
    lab_name = row['研究室名']
    
    if st.button("⬅️ 検索に戻る"):
        st.session_state.page = 'search'
        st.session_state.selected_lab = None
        st.rerun()

    st.title(f"{row['研究室名']}")
    st.markdown(f"**{row['大学名']} {row['研究科']}**")

    tab1, tab2, tab3 = st.tabs(["📚 受験情報", "💬 掲示板", "📂 ファイル"])

    with tab1:
        st.write(f"**試験科目:** {row.get('試験科目')}")
        st.write(f"**英語要件:** {row.get('英語要件')}")
        st.write(f"**指定教科書:** {row.get('指定教科書')}")
        st.markdown(f"👉 [Amazonリンク]({row.get('Amazonリンク')})")

    with tab2:
        st.header("💬 掲示板")
        with st.form(key='comment_form'):
            user_name = st.text_input("名前", "名無し")
            comment_text = st.text_input("コメント")
            submit_btn = st.form_submit_button("書き込む")

        if submit_btn and comment_text:
            save_comment(lab_name, user_name, comment_text)
            st.success("投稿しました！")
            time.sleep(1)
            st.rerun()

        comments_df = load_comments()
        if not comments_df.empty and "研究室名" in comments_df.columns:
            lab_comments = comments_df[comments_df["研究室名"] == lab_name]
            for _, c in lab_comments.iloc[::-1].iterrows():
                st.info(f"{c['日付']} : {c['名前']}\n\n{c['内容']}")
        else:
            st.caption("まだ投稿はありません。")

    with tab3:
        st.write("（ファイル共有は一時保存のみ）")
        uploaded_file = st.file_uploader("ファイルをアップロード")
        if uploaded_file and st.button("アップロード"):
            save_uploaded_file(uploaded_file, lab_name)
            st.success("アップロード成功")

if st.session_state.page == 'search':
    show_sidebar_add_lab()
    show_search_page()
elif st.session_state.page == 'detail':
    show_detail_page()
