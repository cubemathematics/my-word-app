import streamlit as st
import datetime
import math
import json
import os
import io
import csv # 🌟 대량의 엑셀/텍스트 데이터를 읽어내기 위한 부품
from gtts import gTTS

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
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
            padding: 0.6rem 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background: rgba(255, 255, 255, 0.9) !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
            border-color: #d2d2d7 !important;
        }
        div.stButton > button[kind="primary"] {
            background: rgba(0, 122, 255, 0.85) !important;
            color: white !important;
            border: 1px solid rgba(0, 122, 255, 0.5) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background: rgba(0, 122, 255, 1) !important;
        }
        audio { width: 100%; margin-top: -15px; margin-bottom: 20px; border-radius: 12px; }
        </style>
        """,
        unsafe_allow_html=True
    )

DATA_FILE = "words_data.json"

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

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for w in data:
                w["last_review"] = datetime.datetime.fromisoformat(w["last_review"])
                w["next_review"] = datetime.datetime.fromisoformat(w["next_review"])
            return data
    else:
        now = datetime.datetime.now()
        return [
            {"word": "Resilience", "meaning": "회복 탄력성", "s": 0.5, "d": 5.0, "last_review": now, "next_review": now},
            {"word": "Serendipity", "meaning": "뜻밖의 행운", "s": 0.5, "d": 5.0, "last_review": now, "next_review": now}
        ]

def save_data(data):
    save_list = []
    for w in data:
        w_copy = w.copy()
        w_copy["last_review"] = w_copy["last_review"].isoformat()
        w_copy["next_review"] = w_copy["next_review"].isoformat()
        save_list.append(w_copy)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save_list, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="고급 DSR 단어장", layout="centered")
apply_apple_glass_design() 

if 'words' not in st.session_state:
    st.session_state.words = load_data()
if 'show_meaning' not in st.session_state:
    st.session_state.show_meaning = False
if 'page' not in st.session_state:
    st.session_state.page = 'study'

# ==========================================
# 라우팅
# ==========================================
if st.session_state.page == 'study':
    # --- 학습 화면 ---
    with st.sidebar:
        st.markdown("<h2 style='color: #1d1d1f;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
        if st.button("➕ 새 카드 제작 스튜디오로 이동", use_container_width=True, type="primary"):
            st.session_state.page = 'add'
            st.rerun()
        st.divider()
        st.caption(f"총 저장된 단어: **{len(st.session_state.words)}**개")

    now = datetime.datetime.now()
    due_words = [i for i, w in enumerate(st.session_state.words) if w["next_review"] <= now]

    st.markdown("<h1 style='text-align: center; color: #1d1d1f; font-weight: 800; letter-spacing: -1px;'>🧠 Smart Memorizer</h1>", unsafe_allow_html=True)

    if not due_words:
        st.success("🎉 복습 완료! 현재는 모든 단어가 기억 속에 안전합니다.")
        st.balloons()
    else:
        current_index = due_words[0]
        current_word = st.session_state.words[current_index]
        time_passed = (now - current_word["last_review"]).total_seconds() / (24 * 3600) 
        current_r = calculate_retrievability(time_passed, current_word["s"])

        st.progress(1 - (len(due_words) / len(st.session_state.words)))
        st.caption(f"<div style='text-align:center;'>오늘 복습할 단어: <b>{len(due_words)}</b>개 남음</div>", unsafe_allow_html=True)

        glass_card_html = f"""
        <div style="background: rgba(255, 255, 255, 0.4); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.7); padding: 50px 20px 30px 20px; text-align: center; margin: 20px 0 15px 0; color: #1d1d1f;">
        <h1 style="font-size: 64px; font-weight: 800; margin-bottom: 5px; letter-spacing: -2px;">{current_word['word']}</h1>
        <p style="color: #86868b; font-size: 16px; margin-top: 0; font-weight: 600;">💡 현재 기억 확률: {int(current_r * 100)}%</p>
        """
        
        if st.session_state.show_meaning:
            formatted_meaning = current_word['meaning'].replace('\n', '<br>')
            glass_card_html += f"""<hr style="border: 0; height: 1px; background: rgba(0,0,0,0.1); margin: 30px 0;"><h2 style="color: #0066cc; font-weight: 700; margin-top: 0px;">{formatted_meaning}</h2>"""
            
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
                        current_word["s"] = s_new
                        current_word["d"] = d_new
                        current_word["last_review"] = now
                        current_word["next_review"] = now + datetime.timedelta(days=s_new)
                        save_data(st.session_state.words)
                        st.session_state.show_meaning = False
                        st.rerun()

elif st.session_state.page == 'add':
    # --- 🌟 카드 스튜디오 ---
    if st.button("⬅️ 학습 화면으로 돌아가기"):
        st.session_state.page = 'study'
        st.rerun()

    st.markdown("<h1 style='text-align: center; color: #1d1d1f; font-weight: 800; letter-spacing: -1px; margin-top: 20px;'>🛠️ Card Studio</h1>", unsafe_allow_html=True)
    
    # 두 개의 탭으로 나누어 UI를 깔끔하게 분리합니다.
    tab1, tab2 = st.tabs(["✏️ 직접 만들기", "📦 단어장 대량 불러오기 (CSV)"])
    
    with tab1:
        st.caption("하나씩 정성스럽게 카드를 만듭니다.")
        with st.form("add_card_form", clear_on_submit=True):
            new_word = st.text_input("카드 앞면 (단어)", placeholder="예: Serendipity")
            new_meaning = st.text_area("카드 뒷면 (뜻, 예문)", placeholder="예: 뜻밖의 행운", height=100)
            if st.form_submit_button("💳 새 카드 추가하기", use_container_width=True):
                if new_word and new_meaning:
                    if any(w['word'].lower() == new_word.lower() for w in st.session_state.words):
                        st.error(f"'{new_word}' 카드는 이미 존재합니다!")
                    else:
                        now = datetime.datetime.now()
                        st.session_state.words.append({"word": new_word, "meaning": new_meaning, "s": 0.5, "d": 5.0, "last_review": now, "next_review": now})
                        save_data(st.session_state.words)
                        st.success(f"🎉 '{new_word}' 추가 완료!")
                else:
                    st.warning("모두 입력해주세요.")
                    
    with tab2:
        st.caption("다른 사람이 만든 단어장을 1초 만에 앱에 이식합니다.")
        st.info("💡 엑셀에서 **A열에는 단어, B열에는 뜻**을 적고 **CSV(쉼표로 분리)** 형식으로 저장한 파일을 올려주세요.")
        
        uploaded_file = st.file_uploader("CSV 단어장 파일 업로드", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("🚀 단어장 데이터 이식 시작!", type="primary"):
                try:
                    # CSV 파일을 읽어서 분석합니다.
                    content = uploaded_file.read().decode("utf-8-sig").splitlines()
                    reader = csv.reader(content)
                    
                    added_count = 0
                    now = datetime.datetime.now()
                    
                    for row in reader:
                        if len(row) >= 2: # 단어와 뜻이 모두 있는 줄만 처리
                            csv_word = row[0].strip()
                            csv_meaning = row[1].strip()
                            
                            # 빈 칸이거나 이미 있는 단어면 건너뜁니다.
                            if not csv_word or not csv_meaning: continue
                            if any(w['word'].lower() == csv_word.lower() for w in st.session_state.words): continue
                            
                            # 새 단어를 우리 뇌과학 알고리즘에 맞게 초기화합니다.
                            st.session_state.words.append({"word": csv_word, "meaning": csv_meaning, "s": 0.5, "d": 5.0, "last_review": now, "next_review": now})
                            added_count += 1
                            
                    if added_count > 0:
                        save_data(st.session_state.words)
                        st.success(f"🎉 성공! 총 **{added_count}**개의 단어가 내 뇌 속으로 들어올 준비를 마쳤습니다.")
                    else:
                        st.warning("추가할 수 있는 새로운 단어가 없습니다. (이미 다 있는 단어이거나 파일 양식이 잘못되었습니다.)")
                except Exception as e:
                    st.error("파일을 읽는 중 에러가 발생했습니다. CSV 파일이 맞는지 확인해주세요.")