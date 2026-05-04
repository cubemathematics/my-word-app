import streamlit as st
import datetime
import math
import io
import csv
from gtts import gTTS
from supabase import create_client, Client

# ==========================================
# ⚙️ 페이지 기본 설정 (가장 먼저 와야 함)
# ==========================================
st.set_page_config(page_title="선부고 스마트 단어장 - SeonbuWords", layout="centered", page_icon="🧠")

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
# 🎨 2. 애플 스타일 글래스모피즘 디자인
# ==========================================
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
        
        /* 카드 디자인 */
        .glass-card {
            background: rgba(255, 255, 255, 0.4); 
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05); 
            backdrop-filter: blur(20px); 
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px; 
            border: 1px solid rgba(255, 255, 255, 0.7); 
            padding: 50px 20px; 
            text-align: center; 
            margin: 20px 0; 
            color: #1d1d1f;
        }
        
        /* 버튼 디자인 */
        div.stButton > button {
            background: rgba(255, 255, 255, 0.5) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 16px !important; 
            color: #1d1d1f !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background: rgba(255, 255, 255, 0.9) !important;
            transform: translateY(-2px);
        }
        div.stButton > button[kind="primary"] {
            background: rgba(0, 122, 255, 0.85) !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_apple_glass_design()

# ==========================================
# 🧠 3. 핵심 알고리즘 및 기능
# ==========================================
def fetch_user_words():
    """현재 로그인한 유저의 단어만 가져오기"""
    user_id = st.session_state.user.id
    response = supabase.table("words").select("*").eq("user_id", user_id).execute()
    data = response.data
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
    except Exception:
        return None

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
# 💾 4. 세션 상태 초기화
# ==========================================
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'study'
if 'show_meaning' not in st.session_state:
    st.session_state.show_meaning = False

# ==========================================
# 🚪 5. 로그인 / 회원가입 화면
# ==========================================
if st.session_state.user is None:
    st.markdown("<br><br><h1 style='text-align: center; color: #1d1d1f; font-weight: 800; font-size: 3rem;'>🧠 SeonbuWords</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #86868b; font-size: 1.2rem;'>선부고 학생들을 위한 개인화 단어장</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        choice = st.tabs(["🔑 로그인", "📝 회원가입"])
        
        # 로그인 탭
        with choice[0]:
            with st.form("login_form"):
                email = st.text_input("이메일 주소")
                password = st.text_input("비밀번호", type="password")
                submit_login = st.form_submit_button("로그인", type="primary", use_container_width=True)
                
                if submit_login:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        st.success("로그인 성공!")
                        st.rerun()
                    except Exception as e:
                        st.error("로그인 실패: 이메일이나 비밀번호를 확인해주세요.")
                        
        # 회원가입 탭
        with choice[1]:
            with st.form("signup_form"):
                new_email = st.text_input("사용할 이메일 주소")
                new_password = st.text_input("비밀번호 (6자리 이상)", type="password")
                submit_signup = st.form_submit_button("새 계정 만들기", type="primary", use_container_width=True)
                
                if submit_signup:
                    try:
                        res = supabase.auth.sign_up({"email": new_email, "password": new_password})
                        st.success("🎉 가입이 완료되었습니다! 왼쪽의 '로그인' 탭에서 로그인해주세요.")
                    except Exception as e:
                        st.error(f"🚨 진짜 에러 원인: {e}")
# ==========================================
# 📖 6. 메인 앱 화면 (로그인 성공 시)
# ==========================================
else:
    # 로그인한 유저의 데이터 불러오기
    if 'words' not in st.session_state:
        st.session_state.words = fetch_user_words()

    # 사이드바 (제어판 및 유저 정보)
    with st.sidebar:
        st.markdown("<h3 style='color: #1d1d1f;'>👤 내 계정</h3>", unsafe_allow_html=True)
        st.caption(f"**{st.session_state.user.email}**")
        
        if st.button("🚪 로그아웃", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            if 'words' in st.session_state:
                del st.session_state.words
            st.rerun()
            
        st.divider()
        st.markdown("<h3 style='color: #1d1d1f;'>⚙️ Control Panel</h3>", unsafe_allow_html=True)
        
        if st.session_state.page == 'study':
            if st.button("➕ 단어 추가하기", use_container_width=True, type="primary"):
                st.session_state.page = 'add'
                st.rerun()
        else:
            if st.button("⬅️ 학습하러 가기", use_container_width=True, type="primary"):
                st.session_state.page = 'study'
                st.session_state.words = fetch_user_words() # 돌아갈 때 데이터 갱신
                st.rerun()
                
        st.divider()
        st.caption(f"☁️ 내 단어장 보관량: **{len(st.session_state.words)}**개")

    # --- 화면 A: 단어 학습 화면 ---
    if st.session_state.page == 'study':
        st.markdown("<h2 style='text-align: center; color: #1d1d1f;'>📚 오늘의 학습</h2>", unsafe_allow_html=True)

        now = datetime.datetime.now(datetime.timezone.utc)
        due_words = [i for i, w in enumerate(st.session_state.words) if w["next_review"] <= now]

        if not due_words:
            st.success("🎉 오늘 복습할 단어를 모두 마쳤습니다! 훌륭합니다.")
            st.balloons()
        else:
            current_index = due_words[0]
            current_word = st.session_state.words[current_index]
            time_passed = (now - current_word["last_review"]).total_seconds() / (24 * 3600) 
            current_r = calculate_retrievability(time_passed, current_word["s"])

            st.progress(1 - (len(due_words) / len(st.session_state.words)) if len(st.session_state.words) > 0 else 1.0)
            st.caption(f"<div style='text-align:center;'>남은 단어: <b>{len(due_words)}</b>개</div>", unsafe_allow_html=True)

            # 단어 카드 렌더링
            glass_card_html = f"""
            <div class="glass-card">
            <h1 style="font-size: 60px; font-weight: 800; margin-bottom: 5px;">{current_word['word']}</h1>
            <p style="color: #86868b; font-weight: 600;">💡 현재 기억 확률: {int(current_r * 100)}%</p>
            """
            
            if st.session_state.show_meaning:
                formatted_meaning = current_word['meaning'].replace('\n', '<br>')
                glass_card_html += f"""<hr style="border: 0; height: 1px; background: rgba(0,0,0,0.1); margin: 30px 0;">
                                       <h2 style="color: #0066cc;">{formatted_meaning}</h2>"""
                
            glass_card_html += "</div>"
            st.markdown(glass_card_html, unsafe_allow_html=True)

            # 오디오 재생
            audio_bytes = get_audio_bytes(current_word['word'])
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")

            # 버튼 로직
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
                            
                            # DB 업데이트
                            update_data = {
                                "s": s_new, "d": d_new,
                                "last_review": now.isoformat(),
                                "next_review": next_review_time.isoformat()
                            }
                            supabase.table("words").update(update_data).eq("id", current_word["id"]).execute()
                            
                            # 로컬 동기화
                            current_word["s"] = s_new
                            current_word["d"] = d_new
                            current_word["last_review"] = now
                            current_word["next_review"] = next_review_time
                            
                            st.session_state.show_meaning = False
                            st.rerun()

    # --- 화면 B: 단어 추가 화면 ---
    elif st.session_state.page == 'add':
        st.markdown("<h2 style='text-align: center; color: #1d1d1f;'>☁️ 단어 추가 스튜디오</h2>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["✏️ 직접 입력", "📦 CSV 대량 업로드"])
        
        with tab1:
            with st.form("add_card_form", clear_on_submit=True):
                new_word = st.text_input("새 단어 (영어/러시아어/일본어)")
                new_meaning = st.text_area("뜻 / 예문")
                if st.form_submit_button("내 단어장에 저장", use_container_width=True, type="primary"):
                    if new_word and new_meaning:
                        if any(w['word'].lower() == new_word.lower() for w in st.session_state.words):
                            st.error("이미 내 단어장에 존재하는 단어입니다!")
                        else:
                            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            # 중요: user_id를 함께 전송
                            insert_data = {
                                "user_id": st.session_state.user.id,
                                "word": new_word, "meaning": new_meaning,
                                "s": 0.5, "d": 5.0, "last_review": now_iso, "next_review": now_iso
                            }
                            supabase.table("words").insert(insert_data).execute()
                            st.session_state.words = fetch_user_words()
                            st.success(f"'{new_word}' 저장 완료!")
                    else:
                        st.warning("단어와 뜻을 모두 입력해주세요.")
                        
        with tab2:
            st.info("💡 엑셀에서 A열에 단어, B열에 뜻을 적고 CSV로 저장해서 올려주세요.")
            uploaded_file = st.file_uploader("CSV 파일 선택", type=["csv"])
            if uploaded_file is not None:
                if st.button("🚀 대량 업로드 실행", type="primary"):
                    content = uploaded_file.read().decode("utf-8-sig").splitlines()
                    reader = csv.reader(content)
                    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    existing_words = [w['word'].lower() for w in st.session_state.words]
                    
                    bulk_data = []
                    for row in reader:
                        if len(row) >= 2:
                            w, m = row[0].strip(), row[1].strip()
                            if w and m and w.lower() not in existing_words:
                                bulk_data.append({
                                    "user_id": st.session_state.user.id,
                                    "word": w, "meaning": m, "s": 0.5, "d": 5.0,
                                    "last_review": now_iso, "next_review": now_iso
                                })
                                existing_words.append(w.lower())
                                
                    if bulk_data:
                        supabase.table("words").insert(bulk_data).execute()
                        st.session_state.words = fetch_user_words()
                        st.success(f"🎉 총 {len(bulk_data)}개의 단어가 추가되었습니다!")
                    else:
                        st.warning("추가할 수 있는 새로운 단어가 없습니다 (중복 또는 빈 칸).")
