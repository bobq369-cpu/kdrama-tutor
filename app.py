import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import base64
import tempfile
import os

# --- 1. 설정 및 초기화 (Configuration & Init) ---
st.set_page_config(page_title="K-Tutor Global", layout="wide")

# API 키 설정 (실제 배포 시 st.secrets 혹은 환경변수 사용 권장)
# st.session_state에 api_key가 없으면 사이드바에서 입력받음
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.header("설정 (Settings)")
    api_key_input = st.text_input("Gemini API Key를 입력하세요", type="password")
    if api_key_input:
        st.session_state.api_key = api_key_input
        genai.configure(api_key=st.session_state.api_key)
        st.success("API Key가 설정되었습니다!")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "home"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = None
if "model" not in st.session_state:
    # 안전 설정 및 모델 초기화
    st.session_state.model = genai.GenerativeModel('gemini-2.0-flash')

# --- 2. 핵심 로직 함수 (Core Logic) ---

def text_to_speech(text):
    """gTTS를 사용하여 텍스트를 오디오로 변환하고 base64로 인코딩"""
    try:
        # 텍스트에서 괄호 안의 내용이나 특수기호 등은 발음하지 않도록 정제 가능 (생략)
        tts = gTTS(text=text, lang='ko')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
            os.unlink(fp.name)
            return f"data:audio/mp3;base64,{b64}"
    except Exception as e:
        st.error(f"TTS 생성 오류: {e}")
        return None

def generate_ai_response(user_input, scenario):
    """Gemini API 호출 및 응답 처리"""
    if not st.session_state.api_key:
        return "API Key를 먼저 설정해주세요.", None

    # 시스템 프롬프트 구성 (요구사항 반영: 교정, 이미지 태그)
    system_prompt = f"""
    당신은 한국어 회화 튜터입니다. 현재 상황: {scenario['title']}
    역할: {scenario['role']}
    사용자: 한국어를 배우는 외국인

    [규칙]
    1. 사용자의 말에 자연스럽게 대화하세요.
    2. 사용자 문장에 오류가 있다면 문장 끝에 '||'를 붙이고 교정된 문장과 설명을 덧붙이세요.
    3. 상황에 맞는 이미지가 필요하면 '[IMAGE: 키워드]' 형식을 포함하세요.
    4. 응답은 한국어로 하되, 초급~중급 수준에 맞춰주세요.
    """
    
    # 히스토리 기반 대화 생성
    messages = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [msg["content"]]})
    
    messages.append({"role": "user", "parts": [user_input]})

    try:
        response = st.session_state.model.generate_content(messages)
        return response.text
    except Exception as e:
        return f"에러 발생: {str(e)}"

# --- 3. 화면 UI 함수 (UI Components) ---

def go_home():
    st.session_state.page = "home"
    st.session_state.chat_history = []
    st.session_state.current_scenario = None
    st.rerun()

def start_scenario(scenario):
    st.session_state.current_scenario = scenario
    st.session_state.page = "chat"
    # 첫 인사말 자동 생성 로직이 필요하다면 여기에 추가
    st.rerun()

# --- 4. 메인 실행 흐름 (Main Execution) ---

# 시나리오 데이터 (예시)
SCENARIOS = {
    "airport": {"title": "공항 입국 심사", "role": "입국 심사관", "desc": "여권을 보여주고 입국 목적을 설명하세요.", "replies": ["여행 왔어요.", "얼마나 머무나요?", "호텔 바우처 여기 있습니다."]},
    "restaurant": {"title": "식당 주문하기", "role": "식당 종업원", "desc": "메뉴를 고르고 음식을 주문해보세요.", "replies": ["메뉴판 좀 주세요.", "이거 안 매운가요?", "물 좀 더 주세요."]},
    "market": {"title": "시장 물건 사기", "role": "상인", "desc": "가격을 흥정하고 물건을 구매하세요.", "replies": ["이거 얼마예요?", "좀 깎아주세요.", "봉투에 담아주세요."]}
}

if st.session_state.page == "home":
    st.title("🇰🇷 K-Tutor Global")
    st.subheader("연습하고 싶은 상황을 선택하세요")
    
    # 그리드 형태로 시나리오 카드 배치
    cols = st.columns(3)
    for idx, (key, data) in enumerate(SCENARIOS.items()):
        with cols[idx % 3]:
            st.info(f"**{data['title']}**\n\n{data['desc']}")
            if st.button(f"시작하기 ({data['title']})", key=f"btn_{key}"):
                start_scenario(data)

elif st.session_state.page == "chat":
    scenario = st.session_state.current_scenario
    
    # 상단 네비게이션
    col1, col2 = st.columns([8, 2])
    with col1:
        st.title(f"💬 {scenario['title']}")
    with col2:
        if st.button("🏠 홈으로"):
            go_home()

    # 채팅 히스토리 표시
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                # 오디오가 있으면 재생
                if "audio" in msg and msg["audio"]:
                    st.audio(msg["audio"], format="audio/mp3")

    # 추천 표현 (Smart Replies)
    st.write("💡 **추천 표현**")
    reply_cols = st.columns(len(scenario['replies']))
    selected_reply = None
    for idx, reply in enumerate(scenario['replies']):
        if reply_cols[idx].button(reply):
            selected_reply = reply

    # 사용자 입력 처리
    prompt = st.chat_input("한국어로 대화를 입력하세요...")
    
    # 버튼 클릭 혹은 직접 입력 시 실행
    final_input = selected_reply if selected_reply else prompt

    if final_input:
        # 1. 사용자 메시지 추가
        st.session_state.chat_history.append({"role": "user", "content": final_input})
        
        # 2. AI 응답 생성
        ai_text = generate_ai_response(final_input, scenario)
        
        # 3. TTS 생성 (AI 텍스트에서 특수문자/태그 제외하고 순수 텍스트만 추출하는 로직 권장)
        # 여기서는 전체 텍스트를 변환합니다.
        audio_data = text_to_speech(ai_text.split("||")[0]) # 교정 내용 제외하고 앞부분만 읽기 등 응용 가능
        
        # 4. AI 메시지 저장
        st.session_state.chat_history.append({"role": "assistant", "content": ai_text, "audio": audio_data})
        
        st.rerun()