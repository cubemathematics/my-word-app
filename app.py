import streamlit as st
import datetime
import math
import io
import csv
from gtts import gTTS
from supabase import create_client, Client

st.set_page_config(page_title="선부고 스마트 단어장 - SeonbuWords", layout="centered", page_icon="🧠")

# --- 1. DB 연결 ---
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

# --- 2. 디자인 ---
def apply_apple_glass_design():
    st.markdown(
        """
        <style>
        .stApp { background-color: #f2f4f7; }
        .glass-card {
            background: rgba(255, 255, 255, 0.4); 
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05); 
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.7); 
            padding: 50px 20px; text-align: center; margin: 20px 0; color: #1d1d1f;
        }
        div.stButton > button {
            background: rgba(255, 255, 255, 0.5) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 16px !important; color: #1d1d1f !important; font-weight: 600 !important;
        }
        div.stButton > button[kind="primary"] {
            background: rgba(0, 122, 255, 0.85) !important; color: white !important;
        }
        </style>
        """, unsafe_allow_html=True
    )
apply_apple_glass_design()

# --- 3. 핵심 로직 ---
def fetch_user_words():
    user_id = st.session_state.user.id
    response = supabase.table("words").select("*").eq("user_id", user_id).execute()
    data = response.data
    for w in data:
        w["last_review"] = datetime.datetime.fromisoformat(w["last_review"])
        w["next_review"] = datetime.datetime.fromisoformat(w["next_review"])
        # 혹시 예전 데이터에 카테고리가 없다면 기본값 할당
        if "category" not in w or not w["category"]:
            w["category"] = "기본 단어장"
    return data

@st.cache_data
def get_audio_bytes(text, lang='en'):
    try:
        tts = gTTS(text=text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception: return None

def calculate_retrievability(t, s):
    if s == 0: return 0
    return (1 + (19/81) * (t / s)) ** -0.5

def update_memory_state(grade, s_old, d_old, r):
    d_new = max(1.0, min(10.0, d_old + (3 - grade))) 
    if grade == 1: s_new = max(0.1, s_old * 0.2) 
    else: 
        bonus = math.exp(0.5 * (1 - r)) - 1 
        s_new = s_old * (1 + 2.0 * ((11 - d_new) / 10.0) * bonus * (grade - 1))
    return s_new, d_new

# --- 세션 초기화 ---
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'study'
if 'show_meaning' not in st.session_state: st.session_state.show_meaning = False
if 'current_category' not in st.session_state: st.session_state.current_category = "기본 단어장"

# --- 4. 로그인 화면 ---
if st.session_state.user is None:
    st.markdown("<br><br><h1 style='text-align: center;'>🧠 SeonbuWords</h1>", unsafe_allow_html=True)
    choice = st.tabs(["🔑 로그인", "📝 회원가입"])
    with choice[0]:
        with st.form("login"):
            email = st.text_input("이메일 주소")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.success("로그인 성공!")
                    st.rerun()
                except: st.error("로그인 실패: 이메일이나 비밀번호를 확인해주세요.")
    with choice[1]:
        with st.form("signup"):
            new_email = st.text_input("사용할 이메일 주소")
            new_password = st.text_input("비밀번호 (6자리 이상)", type="password")
            if st.form_submit_button("새 계정 만들기", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("가입 완료! 로그인 탭에서 로그인해주세요.")
                except Exception as e: st.error(f"가입 실패: {e}")

# --- 5. 메인 화면 ---
else:
    if 'words' not in st.session_state:
        st.session_state.words = fetch_user_words()

    # 카테고리 목록 추출 (중복 제거)
    categories = list(set([w['category'] for w in st.session_state.words]))
    if not categories: categories = ["기본 단어장"]
    if st.session_state.current_category not in categories:
        st.session_state.current_category = categories[0]

    # --- 사이드바 ---
    with st.sidebar:
        st.markdown("<h3 style='color: #1d1d1f;'>👤 내 계정</h3>", unsafe_allow_html=True)
        if st.button("🚪 로그아웃", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
            
        st.divider()
        st.markdown("### 🗂️ 단어장 선택")
        # 여기서 카테고리(덱)를 선택합니다! 아이폰에서도 터치하기 편하게 드롭다운으로 만들었습니다.
        selected_category = st.selectbox("학습할 언어를 고르세요:", categories, index=categories.index(st.session_state.current_category))
        
        if selected_category != st.session_state.current_category:
            st.session_state.current_category = selected_category
            st.session_state.show_meaning = False
            st.rerun()
            
        st.divider()
        if st.session_state.page == 'study':
            if st.button("➕ 단어 추가하기", use_container_width=True, type="primary"):
                st.session_state.page = 'add'
                st.rerun()
        else:
            if st.button("⬅️ 학습하러 가기", use_container_width=True, type="primary"):
                st.session_state.page = 'study'
                st.session_state.words = fetch_user_words()
                st.rerun()

    # 현재 선택된 카테고리의 단어만 필터링
    filtered_words = [w for w in st.session_state.words if w['category'] == st.session_state.current_category]

    # --- 학습 화면 ---
    if st.session_state.page == 'study':
        st.markdown(f"<h2 style='text-align: center;'>📚 {st.session_state.current_category} 학습</h2>", unsafe_allow_html=True)

        now = datetime.datetime.now(datetime.timezone.utc)
        due_words = [w for w in filtered_words if w["next_review"] <= now]

        if not filtered_words:
            st.info("이 단어장에는 아직 추가된 단어가 없습니다. 왼쪽 메뉴에서 단어를 추가해보세요!")
        elif not due_words:
            st.success("🎉 오늘 복습할 단어를 모두 마쳤습니다!")
            st.balloons()
        else:
            current_word = due_words[0]
            time_passed = (now - current_word["last_review"]).total_seconds() / (24 * 3600) 
            current_r = calculate_retrievability(time_passed, current_word["s"])

            st.progress(1 - (len(due_words) / len(filtered_words)))
            st.caption(f"<div style='text-align:center;'>남은 단어: <b>{len(due_words)}</b>개</div>", unsafe_allow_html=True)

            glass_card_html = f"""
            <div class="glass-card">
            <h1 style="font-size: 60px; font-weight: 800; margin-bottom: 5px;">{current_word['word']}</h1>
            <p style="color: #86868b; font-weight: 600;">💡 현재 기억 확률: {int(current_r * 100)}%</p>
            """
            if st.session_state.show_meaning:
                formatted_meaning = current_word['meaning'].replace('\n', '<br>')
                glass_card_html += f"""<hr style="border: 0; background: rgba(0,0,0,0.1); margin: 30px 0;"><h2 style="color: #0066cc;">{formatted_meaning}</h2>"""
            glass_card_html += "</div>"
            st.markdown(glass_card_html, unsafe_allow_html=True)

            # 언어에 맞게 음성 언어 자동 설정 (야매 팁: 단어에 키릴문자나 히라가나가 있으면 자동 감지할 수도 있지만, 일단은 기본 영어/선택으로 둡니다)
            audio_bytes = get_audio_bytes(current_word['word'])
            if audio_bytes: st.audio(audio_bytes, format="audio/mp3")

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
                            
                            update_data = {"s": s_new, "d": d_new, "last_review": now.isoformat(), "next_review": next_review_time.isoformat()}
                            supabase.table("words").update(update_data).eq("id", current_word["id"]).execute()
                            
                            # 메모리 업데이트
                            for w in st.session_state.words:
                                if w['id'] == current_word['id']:
                                    w.update({"s": s_new, "d": d_new, "last_review": now, "next_review": next_review_time})
                            
                            st.session_state.show_meaning = False
                            st.rerun()

    # --- 단어 추가 화면 ---
    elif st.session_state.page == 'add':
        st.markdown("<h2 style='text-align: center;'>☁️ 단어 추가 스튜디오</h2>", unsafe_allow_html=True)
        
        # 카테고리 입력기 (직접 입력하거나 기존 목록에서 선택)
        new_category = st.text_input("🗂️ 저장할 단어장 이름 (예: 영어, 러시아어, 일본어)", value=st.session_state.current_category)

        with st.form("add_card_form", clear_on_submit=True):
            new_word = st.text_input("새 단어")
            new_meaning = st.text_area("뜻 / 예문")
            if st.form_submit_button("내 단어장에 저장", use_container_width=True, type="primary"):
                if new_word and new_meaning and new_category:
                    if any(w['word'].lower() == new_word.lower() and w['category'] == new_category for w in st.session_state.words):
                        st.error("이 단어장에 이미 존재하는 단어입니다!")
                    else:
                        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        insert_data = {
                            "user_id": st.session_state.user.id,
                            "category": new_category,  # 👈 카테고리 추가!
                            "word": new_word, "meaning": new_meaning,
                            "s": 0.5, "d": 5.0, "last_review": now_iso, "next_review": now_iso
                        }
                        supabase.table("words").insert(insert_data).execute()
                        st.session_state.words = fetch_user_words()
                        st.session_state.current_category = new_category # 추가한 카테고리로 이동
                        st.success(f"[{new_category}] 단어장에 '{new_word}' 저장 완료!")
                else:
                    st.warning("단어장 이름, 단어, 뜻을 모두 입력해주세요.")
