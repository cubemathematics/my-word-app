import streamlit as st
import datetime
import math
import io
import csv
from gtts import gTTS
from supabase import create_client, Client

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="선부고 스마트 단어장 - SeonbuWords", layout="centered", page_icon="🧠")

# --- 1. DB 연결 ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try: supabase = init_connection()
except Exception as e: st.stop()

# --- 2. 디자인 및 아이폰 앱 설정 ---
def apply_apple_glass_design():
    # 🚨 바로 이 부분에 아이폰(iOS) 사파리 전용 웹 앱 태그가 들어갑니다!
    st.markdown(
        """
        <!-- 🍎 아이폰 바탕화면 앱 설정을 위한 메타 태그 -->
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="SeonbuWords">
        
        <style>
        .stApp { background-color: #f2f4f7; }
        .glass-card {
            background: rgba(255, 255, 255, 0.4); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05); 
            backdrop-filter: blur(20px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.7); 
            padding: 50px 20px; text-align: center; margin: 20px 0; color: #1d1d1f;
        }
        div.stButton > button {
            background: rgba(255, 255, 255, 0.5) !important; backdrop-filter: blur(10px) !important;
            border-radius: 16px !important; color: #1d1d1f !important; font-weight: 600 !important;
        }
        div.stButton > button[kind="primary"] { background: rgba(0, 122, 255, 0.85) !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True
    )
apply_apple_glass_design()

# --- 3. 핵심 데이터 로직 ---
def fetch_user_decks():
    res = supabase.table("decks").select("*").eq("user_id", st.session_state.user.id).execute()
    return res.data

def fetch_words_for_deck(deck_id):
    res = supabase.table("words").select("*").eq("deck_id", deck_id).execute()
    data = res.data
    for w in data:
        w["last_review"] = datetime.datetime.fromisoformat(w["last_review"])
        w["next_review"] = datetime.datetime.fromisoformat(w["next_review"])
    return data

@st.cache_data
def get_audio_bytes(text, lang='en'):
    try:
        tts = gTTS(text=text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except: return None

def calculate_retrievability(t, s):
    return 0 if s == 0 else (1 + (19/81) * (t / s)) ** -0.5

def update_memory_state(grade, s_old, d_old, r):
    d_new = max(1.0, min(10.0, d_old + (3 - grade))) 
    if grade == 1: s_new = max(0.1, s_old * 0.2) 
    else: 
        bonus = math.exp(0.5 * (1 - r)) - 1 
        s_new = s_old * (1 + 2.0 * ((11 - d_new) / 10.0) * bonus * (grade - 1))
    return s_new, d_new

# --- 세션 초기화 ---
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'current_deck' not in st.session_state: st.session_state.current_deck = None
if 'show_meaning' not in st.session_state: st.session_state.show_meaning = False

# --- 4. 로그인 화면 (버그 수정 및 자동완성 적용) ---
if st.session_state.user is None:
    st.markdown("<br><br><h1 style='text-align: center;'>🧠 SeonbuWords</h1>", unsafe_allow_html=True)
    choice = st.tabs(["🔑 로그인", "📝 회원가입"])
    
    with choice[0]:
        with st.form("login_form"):
            email = st.text_input("이메일 주소", key="login_email", autocomplete="email")
            password = st.text_input("비밀번호", type="password", key="login_pw", autocomplete="current-password")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
            
        if submitted:
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e: 
                    st.error("로그인 실패: 이메일이나 비밀번호가 틀렸습니다.")
            else:
                st.warning("이메일과 비밀번호를 모두 입력해주세요.")

    with choice[1]:
        with st.form("signup_form"):
            new_email = st.text_input("새 이메일", key="signup_email", autocomplete="email")
            new_password = st.text_input("비밀번호(6자 이상)", type="password", key="signup_pw", autocomplete="new-password")
            signup_submitted = st.form_submit_button("회원가입 완료", type="primary", use_container_width=True)
            
        if signup_submitted:
            if new_email and len(new_password) >= 6:
                try:
                    supabase.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("🎉 가입 완료! 이제 왼쪽 '로그인' 탭에서 로그인해주세요.")
                except Exception as e: 
                    st.error("가입 실패: 이미 가입된 이메일이거나 오류가 발생했습니다.")
            else:
                st.warning("이메일과 6자리 이상의 비밀번호를 입력해주세요.")

# --- 5. 메인 시스템 ---
else:
    st.session_state.decks = fetch_user_decks()

    with st.sidebar:
        st.write(f"👤 **{st.session_state.user.email}**")
        if st.button("🚪 로그아웃", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
        st.divider()
        if st.button("🏠 내 덱 목록 (홈)", use_container_width=True, type="primary" if st.session_state.page == 'home' else "secondary"):
            st.session_state.page = 'home'
            st.session_state.current_deck = None
            st.rerun()

    # 화면 A: 홈
    if st.session_state.page == 'home':
        st.markdown("<h2 style='text-align: center;'>🗂️ 내 단어장(덱) 목록</h2>", unsafe_allow_html=True)
        
        with st.expander("➕ 새 덱(단어장) 만들기", expanded=not st.session_state.decks):
            with st.form("new_deck_form", clear_on_submit=True):
                new_deck_name = st.text_input("덱 이름 (예: TORFL 러시아어, 학교 내신 영어)")
                if st.form_submit_button("생성하기"):
                    if new_deck_name:
                        try:
                            supabase.table("decks").insert({"user_id": st.session_state.user.id, "name": new_deck_name}).execute()
                            st.success(f"'{new_deck_name}' 덱 생성 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"🚨 생성 실패: {e}")
        
        st.divider()

        if not st.session_state.decks:
            st.info("아직 만든 덱이 없습니다. 위에서 새 덱을 만들어보세요!")
        else:
            for deck in st.session_state.decks:
                with st.container():
                    st.markdown(f"### 📘 {deck['name']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("▶️ 학습하기", key=f"study_{deck['id']}", use_container_width=True, type="primary"):
                            st.session_state.current_deck = deck
                            st.session_state.page = 'study'
                            st.rerun()
                    with col2:
                        if st.button("➕ 단어 넣기", key=f"add_{deck['id']}", use_container_width=True):
                            st.session_state.current_deck = deck
                            st.session_state.page = 'add'
                            st.rerun()
                    st.markdown("---")

    # 화면 B: 단어 추가
    elif st.session_state.page == 'add':
        deck = st.session_state.current_deck
        st.markdown(f"<h2 style='text-align: center;'>[{deck['name']}] 단어 추가</h2>", unsafe_allow_html=True)
        
        if st.button("⬅️ 뒤로 가기 (홈)", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

        with st.form("add_word_form", clear_on_submit=True):
            new_word = st.text_input("단어 (외국어)")
            new_meaning = st.text_area("뜻 / 예문")
            if st.form_submit_button("이 덱에 저장", type="primary", use_container_width=True):
                if new_word and new_meaning:
                    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    supabase.table("words").insert({
                        "user_id": st.session_state.user.id,
                        "deck_id": deck['id'],
                        "word": new_word, "meaning": new_meaning,
                        "s": 0.5, "d": 5.0, "last_review": now_iso, "next_review": now_iso
                    }).execute()
                    st.success("저장 완료!")
                else: st.warning("단어와 뜻을 입력하세요.")

    # 화면 C: 단어 학습
    elif st.session_state.page == 'study':
        deck = st.session_state.current_deck
        st.markdown(f"<h2 style='text-align: center;'>📚 [{deck['name']}] 학습 중</h2>", unsafe_allow_html=True)
        
        words_in_deck = fetch_words_for_deck(deck['id'])
        now = datetime.datetime.now(datetime.timezone.utc)
        due_words = [w for w in words_in_deck if w["next_review"] <= now]

        if not words_in_deck:
            st.info("이 덱에 카드가 없습니다. 뒤로 가서 단어를 추가해 보세요!")
            if st.button("⬅️ 홈으로 가기"): st.session_state.page = 'home'; st.rerun()
        elif not due_words:
            st.success("🎉 축하합니다! 이 덱의 오늘 복습을 모두 마쳤습니다.")
            st.balloons()
            if st.button("⬅️ 다른 덱 공부하기"): st.session_state.page = 'home'; st.rerun()
        else:
            current_word = due_words[0]
            time_passed = (now - current_word["last_review"]).total_seconds() / (24 * 3600) 
            current_r = calculate_retrievability(time_passed, current_word["s"])

            st.progress(1 - (len(due_words) / len(words_in_deck)))
            st.caption(f"<div style='text-align:center;'>남은 카드: <b>{len(due_words)}</b>장</div>", unsafe_allow_html=True)

            glass_card_html = f"""
            <div class="glass-card">
            <h1 style="font-size: 60px; font-weight: 800;">{current_word['word']}</h1>
            <p style="color: #86868b;">💡 현재 기억 확률: {int(current_r * 100)}%</p>
            """
            if st.session_state.show_meaning:
                glass_card_html += f"""<hr><h2 style="color: #0066cc;">{current_word['meaning'].replace('\n', '<br>')}</h2>"""
            glass_card_html += "</div>"
            st.markdown(glass_card_html, unsafe_allow_html=True)

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
                            next_review = (now + datetime.timedelta(days=s_new)).isoformat()
                            supabase.table("words").update({"s": s_new, "d": d_new, "last_review": now.isoformat(), "next_review": next_review}).eq("id", current_word["id"]).execute()
                            st.session_state.show_meaning = False
                            st.rerun()
