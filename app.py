import streamlit as st
import datetime
import math
import io
import csv
from gtts import gTTS
from supabase import create_client, Client

# ==========================================
# 🔐 1. Supabase 클라우드 DB 연결
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("⚠️ 데이터베이스 연결 실패. Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# ==========================================
# 🛠️ 2. 핵심 기능 및 디자인 세팅
# ==========================================
@st.cache_data
def get_audio_bytes(text, lang='en'):
    try:
        tts = gTTS(text=text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        return None

def apply_apple_glass_design():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f2f4f7;
            background-image: 
                radial-gradient(at 0% 0%, hsla(210, 40%, 92%, 1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, hsla(220, 20%, 88%, 1) 0px, transparent 50%),
                radial-gradient(at 50% 50%, hsla(200, 30%, 94%, 1) 0px, transparent 50%);
            background-attachment: fixed;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
        }
        .block-container, .main { background: transparent !important; }
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.3) !important; 
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.6);
        }
        header { background: transparent !important; }
        div.stButton > button {
            background: rgba(255, 255, 255, 0.5) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 16px !important; 
            color: #1d1d1f !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background: rgba(255, 255, 255, 0.9) !important;
            transform: translateY(-1px);
        }
        div.stButton > button[kind="primary"] {
            background: rgba(0, 122, 255, 0.85) !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def calculate_retrievability(t, s):
    if s == 0: return 0
    return (1 + (19/81) * (t / s)) ** -0.5

def update_memory_state(grade, s_old, d_old, r):
    d_new = d_old + (3 - grade) 
    d_new = max(1.0, min(10.0, d_new)) 
    if grade == 1: s_new = max(0.1, s_old * 0.2) 
    else: 
        bonus = math.exp(0.5 * (1 - r)) - 1 
        difficulty_factor = (11 - d_new) / 10.0
        s_new = s_old * (1 + 2.0 * difficulty_factor * bonus * (grade - 1))
    return s_new, d_new

# ==========================================
# 🗄️ 3. 데이터베이스 조작 로직 (CRUD)
# ==========================================
def fetch_words_from_db():
    response = supabase.table("words").select("*").execute()
    data = response.data
    for w in data:
        w["last_review"] = datetime.datetime.fromisoformat(w["last_review"])
        w["next_review"] = datetime.datetime.fromisoformat(w["next_review"])
    return data

st.set_page_config(page_title="선부고 스마트 단어장", layout="centered")
apply_apple_glass_design() 

# 앱 실행 시 클라우드에서 단어장 다운로드
if 'words' not in st.session_state:
    st.session_state.words = fetch_words_from_db()
if 'show_meaning' not in st.session_state:
    st.session_state.show_meaning = False
if 'page' not in st.session_state:
    st.session_state.page = 'study'

# ==========================================
# 🚀 4. 라우팅 및 UI 화면
# ==========================================
if st.session_state.page == 'study':
    with st.sidebar:
        st.markdown("<h2 style='color: #1d1d1f;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
        if st.button("➕ 단어 추가 & 불러오기", use_container_width=True, type="primary"):
            st.session_state.page = 'add'
            st.rerun()
        st.divider()
        st.caption(f"☁️ 클라우드에 저장된 단어: **{len(st.session_state.words)}**개")

    now = datetime.datetime.now(datetime.timezone.utc)
    due_words = [i for i, w in enumerate(st.session_state.words) if w["next_review"] <= now]

    st.markdown("<h1 style='text-align: center; color: #1d1d1f; font-weight: 800; letter-spacing: -1px;'>🧠 Seonbu Smart Memorizer</h1>", unsafe_allow_html=True)

    if not due_words:
        st.success("🎉 복습 완료! 현재는 모든 단어가 뇌 속에 안전합니다.")
        st.balloons()
    else:
        current_index = due_words[0]
        current_word = st.session_state.words[current_index]
        time_passed = (now - current_word["last_review"]).total_seconds() / (24 * 3600) 
        current_r = calculate_retrievability(time_passed, current_word["s"])

        st.progress(1 - (len(due_words) / len(st.session_state.words)))
        st.caption(f"<div style='text-align:center;'>오늘 복습할 단어: <b>{len(due_words)}</b>개 남음</div>", unsafe_allow_html=True)

        glass_card_html = f"""
        <div style="background: rgba(255, 255, 255, 0.4); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05); backdrop-filter: blur(20px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.7); padding: 50px 20px; text-align: center; margin: 20px 0; color: #1d1d1f;">
        <h1 style="font-size: 64px; font-weight: 800; margin-bottom: 5px;">{current_word['word']}</h1>
        <p style="color: #86868b; font-weight: 600;">💡 현재 기억 확률: {int(current_r * 100)}%</p>
        """
        
        if st.session_state.show_meaning:
            formatted_meaning = current_word['meaning'].replace('\n', '<br>')
            glass_card_html += f"""<hr style="border: 0; height: 1px; background: rgba(0,0,0,0.1); margin: 30px 0;"><h2 style="color: #0066cc;">{formatted_meaning}</h2>"""
            
        glass_card_html += "</div>"
        st.markdown(glass_card_html, unsafe_allow_html=True)

        audio_bytes = get_audio_bytes(current_word['word'])
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")

        if not st.session_state.show_meaning:
            if st.button("👀 정답 확인", use_container_width=True, type="primary"):
                st.session_state.show_meaning = True
                st.rerun()
        else:
            cols = st.columns(4)
            grades = [(1, "🔴 몰랐음"), (2, "🟠 헷갈림"), (3, "🟢 알맞음"), (4, "🔵 쉬움")]
            for i, (grade, label) in enumerate(grades):
                with cols[i]:
                    if st.button(label, key=f"grade_{i}", use_container_width=True):
                        s_new, d_new = update_memory_state(grade, current_word["s"], current_word["d"], current_r)
                        next_review_time = now + datetime.timedelta(days=s_new)
                        
                        # 1. 클라우드 DB 업데이트
                        update_data = {
                            "s": s_new, "d": d_new,
                            "last_review": now.isoformat(),
                            "next_review": next_review_time.isoformat()
                        }
                        supabase.table("words").update(update_data).eq("id", current_word["id"]).execute()
                        
                        # 2. 로컬 화면 동기화
                        current_word["s"] = s_new
                        current_word["d"] = d_new
                        current_word["last_review"] = now
                        current_word["next_review"] = next_review_time
                        
                        st.session_state.show_meaning = False
                        st.rerun()

elif st.session_state.page == 'add':
    if st.button("⬅️ 학습 화면으로 돌아가기"):
        st.session_state.page = 'study'
        st.rerun()

    st.markdown("<h1 style='text-align: center;'>☁️ Cloud Card Studio</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["✏️ 낱개 추가", "📦 대량 CSV 추가"])
    
    with tab1:
        with st.form("add_card_form", clear_on_submit=True):
            new_word = st.text_input("새 단어")
            new_meaning = st.text_area("뜻 / 예문")
            if st.form_submit_button("💳 클라우드에 추가하기", use_container_width=True):
                if new_word and new_meaning:
                    if any(w['word'].lower() == new_word.lower() for w in st.session_state.words):
                        st.error("이미 존재하는 단어입니다!")
                    else:
                        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        insert_data = {
                            "word": new_word, "meaning": new_meaning,
                            "s": 0.5, "d": 5.0, "last_review": now, "next_review": now
                        }
                        # 클라우드에 쏘고 새로고침!
                        supabase.table("words").insert(insert_data).execute()
                        st.session_state.words = fetch_words_from_db()
                        st.success(f"'{new_word}' DB 저장 완료!")
                else:
                    st.warning("모두 입력해주세요.")
                    
    with tab2:
        st.info("💡 A열 단어, B열 뜻 형식의 CSV를 올려주세요. (서버 과부하 방지를 위해 한 번에 100개 이하를 권장합니다.)")
        uploaded_file = st.file_uploader("단어장 파일", type=["csv"])
        if uploaded_file is not None:
            if st.button("🚀 클라우드 대량 이식!", type="primary"):
                content = uploaded_file.read().decode("utf-8-sig").splitlines()
                reader = csv.reader(content)
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                existing_words = [w['word'].lower() for w in st.session_state.words]
                
                bulk_data = []
                for row in reader:
                    if len(row) >= 2:
                        w, m = row[0].strip(), row[1].strip()
                        if w and m and w.lower() not in existing_words:
                            bulk_data.append({
                                "word": w, "meaning": m, "s": 0.5, "d": 5.0,
                                "last_review": now, "next_review": now
                            })
                            existing_words.append(w.lower())
                            
                if bulk_data:
                    supabase.table("words").insert(bulk_data).execute()
                    st.session_state.words = fetch_words_from_db()
                    st.success(f"🎉 총 {len(bulk_data)}개의 단어가 클라우드에 영구 보관되었습니다!")
                else:
                    st.warning("추가할 수 있는 새로운 단어가 없습니다.")
