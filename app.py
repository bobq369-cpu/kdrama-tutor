import streamlit as st
import google.generativeai as genai
import sqlite3
import difflib
import time
import base64
import json
import os
import io
from datetime import datetime
from gtts import gTTS

# ==========================================
# 1. 환경 설정 및 초기화 (보고서 3.1, 5.1)
# ==========================================
st.set_page_config(
    page_title="K-Tutor Global",
    page_icon="🇰🇷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# API 키 설정
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except (KeyError, FileNotFoundError):
    st.error("🚨 API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# DB 초기화 (보고서 3.3, 5.2)
DB_NAME = "k_tutor.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT,
                    user_message TEXT,
                    ai_response TEXT,
                    correction TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# ==========================================
# 2. 디자인 시스템: CSS 주입 (보고서 4.1, 4.2)
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
        /* 폰트 설정 (Pretendard) */
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css");
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif !important;
            background-color: #FAF1DB; /* Hanok Beige: 배경색 */
        }
        
        .stApp {
            background-color: #FAF1DB; /* 전체 배경 */
        }

        /* 상단 헤더 제거 및 여백 조정 (보고서 4.2) */
        header {visibility: hidden;}
        .main .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
            max-width: 700px;
        }

        /* 시나리오 카드 디자인 (보고서 5.3) */
        .scenario-card-btn > button {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E5E5 !important;
            border-radius: 15px !important;
            padding: 20px !important;
            height: auto !important;
            min-height: 160px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            transition: transform 0.2s !important;
            width: 100%;
        }
        .scenario-card-btn > button:hover {
            transform: translateY(-5px);
            border-color: #81DFDC !important; /* Seoul Sky */
        }

        /* 채팅 말풍선 디자인 (보고서 4.1) */
        .chat-bubble {
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 10px;
            font-size: 16px;
            line-height: 1.5;
            max-width: 85%;
            word-wrap: break-word;
            position: relative;
        }
        
        .user-bubble {
            background-color: #81DFDC; /* Seoul Sky */
            color: #004D40;
            margin-left: auto;
            border-top-right-radius: 0;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
        }
        
        .ai-bubble {
            background-color: #FFFFFF;
            color: #265481; /* Ink Navy */
            border: 1px solid #E9ECEF;
            margin-right: auto;
            border-top-left-radius: 0;
        }

        /* Diff View (교정) 디자인 (보고서 5.5) */
        .correction-box {
            background-color: #FFF9DB; /* 연한 노란색 */
            border-left: 4px solid #EE6C4D; /* Persimmon */
            padding: 12px;
            margin: 5px 0 15px 0;
            border-radius: 4px;
            font-size: 0.9rem;
            color: #495057;
        }
        .diff-del {
            background-color: #FFC9C9;
            text-decoration: line-through;
            color: #C92A2A;
            padding: 0 4px;
            border-radius: 3px;
        }
        .diff-add {
            background-color: #B2F2BB; /* Soft Sage */
            font-weight: bold;
            color: #2B8A3E;
            padding: 0 4px;
            border-radius: 3px;
        }

        /* 하단 오디오 입력창 스타일 */
        .stAudioInput {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 680px;
            z-index: 999;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-radius: 20px;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 3. 데이터 및 시나리오 정의
# ==========================================
SCENARIOS = {
    "airport": {
        "id": "airport",
        "title": "공항 입국 심사",
        "icon": "✈️",
        "role": "깐깐한 입국 심사관",
        "level": "초급 (Beginner)",
        "desc": "입국 목적과 체류 기간을 묻는 질문에 대답해보세요.",
        "context": "당신은 한국 공항의 입국 심사대에 서 있습니다. 심사관이 여권을 확인하며 질문합니다."
    },
    "cafe": {
        "id": "cafe",
        "title": "카페 주문하기",
        "icon": "☕",
        "role": "친절한 카페 직원",
        "level": "중급 (Intermediate)",
        "desc": "원하는 음료와 옵션(얼음 양, 사이즈)을 주문해보세요.",
        "context": "서울의 힙한 카페입니다. 직원이 주문을 받으러 기다리고 있습니다."
    }
}

# ==========================================
# 4. 로직 함수 (AI, Diff, TTS)
# ==========================================

# 4.1 Diff 생성 함수 (보고서 5.5)
def generate_diff_html(original, corrected):
    matcher = difflib.SequenceMatcher(None, original.split(), corrected.split())
    html_output = []
    
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == 'equal':
            html_output.append(" ".join(original.split()[i1:i2]))
        elif opcode == 'replace':
            html_output.append(f'<span class="diff-del">{" ".join(original.split()[i1:i2])}</span>')
            html_output.append(f'<span class="diff-add">{" ".join(corrected.split()[j1:j2])}</span>')
        elif opcode == 'delete':
            html_output.append(f'<span class="diff-del">{" ".join(original.split()[i1:i2])}</span>')
        elif opcode == 'insert':
            html_output.append(f'<span class="diff-add">{" ".join(corrected.split()[j1:j2])}</span>')
            
    return " ".join(html_output)

# 4.2 AI 응답 생성 (LLM + STT 통합) - 보고서 3.2
# 비용 효율성을 위해 STT도 Gemini에게 맡깁니다.
def process_conversation(audio_bytes, text_input=None):
    scenario = SCENARIOS[st.session_state.current_scenario]
    
    # 시스템 프롬프트: JSON 포맷으로 응답 강제
    system_prompt = f"""
    당신은 {scenario['role']}입니다. 상황: {scenario['context']}.
    한국어 튜터로서 사용자와 대화하세요.
    
    반드시 다음 JSON 형식으로만 응답하세요:
    {{
        "user_stt": "사용자의 말을 받아적은 텍스트 (오디오 입력인 경우)",
        "response": "당신의 자연스러운 대답",
        "correction": "사용자 문장의 자연스러운 교정본 (오류가 없으면 그대로)",
        "explanation": "교정 이유나 더 나은 표현 팁 (간략하게)"
    }}
    
    사용자 입력이 한국어가 아니거나 어색하면 친절하게 교정해주세요.
    """
    
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt)
    
    try:
        if audio_bytes:
            # 오디오 입력 처리
            response = model.generate_content([
                "사용자의 오디오 입력을 듣고 대화를 이어가세요.",
                {"mime_type": "audio/wav", "data": audio_bytes}
            ])
        else:
            # 텍스트 입력 처리
            response = model.generate_content(text_input)
            
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI 오류: {e}")
        return None

# 4.3 TTS 생성
def generate_tts(text):
    try:
        tts = gTTS(text=text, lang='ko', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
        os.unlink(fp.name)
        return f'<audio controls autoplay src="data:audio/mp3;base64,{b64}" style="width: 100%; height: 30px; margin-top: 5px;"></audio>'
    except:
        return ""

# ==========================================
# 5. 메인 앱 플로우
# ==========================================

def main():
    if "page" not in st.session_state: st.session_state.page = "HOME"
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # --- PAGE 1: 홈 (시나리오 선택) ---
    if st.session_state.page == "HOME":
        st.markdown("<h1 style='text-align: center; color: #265481;'>🇰🇷 K-Tutor Global</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>오늘 연습할 대화 주제를 선택해주세요.</p>", unsafe_allow_html=True)
        st.write("") # 간격

        col1, col2 = st.columns(2)
        for idx, (key, data) in enumerate(SCENARIOS.items()):
            with col1 if idx % 2 == 0 else col2:
                # 보고서 5.3: 카드형 UI 구현
                st.markdown(f'<div class="scenario-card-btn">', unsafe_allow_html=True)
                if st.button(f"{data['icon']}\n\n{data['title']}\n{data['level']}", key=key):
                    st.session_state.current_scenario = key
                    st.session_state.messages = [] # 대화 초기화
                    st.session_state.page = "CHAT"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 2: 채팅 (롤플레잉) ---
    elif st.session_state.page == "CHAT":
        sc = SCENARIOS[st.session_state.current_scenario]
        
        # 상단 네비게이션
        c1, c2 = st.columns([1, 8])
        with c1:
            if st.button("⬅", help="홈으로"):
                st.session_state.page = "HOME"
                st.rerun()
        with c2:
            st.markdown(f"**{sc['icon']} {sc['title']}** ({sc['role']})")
        
        st.divider()

        # 채팅 영역
        chat_container = st.container()
        with chat_container:
            if not st.session_state.messages:
                st.info(f"💡 Tip: {sc['desc']}")
                # 초기 인사
                initial_msg = "안녕하세요! 여권 좀 보여주시겠습니까?" if sc['id'] == 'airport' else "어서오세요! 주문 도와드릴까요?"
                st.session_state.messages.append({"role": "assistant", "content": initial_msg})

            # 메시지 렌더링 Loop
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-bubble user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-bubble ai-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
                    
                    # 보고서 5.5: Diff View 교정 렌더링
                    if "correction" in msg and msg["correction"]:
                        original = st.session_state.messages[-2]['content'] # 직전 유저 메시지
                        correction = msg['correction']
                        explanation = msg.get('explanation', '')
                        
                        if original.strip() != correction.strip():
                            diff_html = generate_diff_html(original, correction)
                            st.markdown(f"""
                            <div class="correction-box">
                                <strong>✨ AI 교정:</strong> {diff_html}<br>
                                <span style="font-size: 0.8rem; color: #868E96;">💡 {explanation}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # TTS 재생 (마지막 메시지인 경우)
                    if msg == st.session_state.messages[-1] and "tts_html" not in msg:
                         msg["tts_html"] = generate_tts(msg["content"])
                    
                    if "tts_html" in msg:
                        st.markdown(msg["tts_html"], unsafe_allow_html=True)

        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True) # 하단 여백 확보

        # 보고서 5.4: Audio Input & Partial Rerun (Fragment)
        # 하단에 고정된 오디오 입력창 처리
        handle_input()

# Fragment를 사용하여 오디오 입력 시 전체 리로드 방지 (보고서 3.1)
@st.fragment
def handle_input():
    audio_val = st.audio_input("말하기 (터치하여 녹음)")
    
    if audio_val:
        with st.spinner("듣고 있는 중..."):
            # 오디오 바이트 변환
            audio_bytes = audio_val.read()
            
            # AI 처리
            result = process_conversation(audio_bytes=audio_bytes)
            
            if result:
                # 세션에 대화 추가
                user_text = result.get("user_stt", "(음성 인식 불가)")
                st.session_state.messages.append({"role": "user", "content": user_text})
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "correction": result.get("correction"),
                    "explanation": result.get("explanation")
                })
                
                # DB 로그 저장 (보고서 3.3)
                try:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO chat_logs (scenario_id, user_message, ai_response, correction) VALUES (?, ?, ?, ?)",
                              (st.session_state.current_scenario, user_text, result["response"], result.get("correction")))
                    conn.commit()
                    conn.close()
                except:
                    pass

                # 강제 리런으로 UI 업데이트
                st.rerun()

if __name__ == "__main__":
    main()