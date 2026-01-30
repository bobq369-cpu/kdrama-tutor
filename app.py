import streamlit as st
import google.generativeai as genai
import os
from gtts import gTTS
import tempfile
import base64

# --- 1. 기본 설정 및 비밀키 가져오기 ---
st.set_page_config(
    page_title="K-Tutor Global",
    page_icon="🇰🇷",
    layout="centered",  # 모바일 느낌을 위해 중앙 정렬
    initial_sidebar_state="collapsed"  # 사이드바 기본 숨김
)

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("API 키가 설정되지 않았습니다. 스트림릿 설정에서 GOOGLE_API_KEY를 추가해주세요.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. 프리미엄 UI를 위한 커스텀 CSS ---
def inject_custom_css():
    st.markdown(
        """
        <style>
            /* 전체 배경 및 폰트 설정 */
            .stApp {
                background-color: #F8F9FA; /* 아주 연한 회색 배경 */
                font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
            }
            /* 메인 컨테이너 스타일링 (모바일 카드뷰 느낌) */
            .main .block-container {
                max-width: 700px;
                padding-top: 2rem;
                padding-bottom: 5rem;
                background-color: #FFFFFF;
                border-radius: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.05);
                margin-top: 20px;
                margin-bottom: 20px;
            }
            /* 헤더, 푸터 숨기기 */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* 채팅 말풍선 스타일 */
            .chat-bubble {
                padding: 15px 20px;
                border-radius: 25px;
                margin-bottom: 10px;
                max-width: 80%;
                word-wrap: break-word;
                font-size: 16px;
                line-height: 1.5;
            }
            /* 사용자 말풍선 (오른쪽, 파란색) */
            .user-bubble {
                background-color: #007AFF;
                color: white;
                margin-left: auto;
                border-bottom-right-radius: 5px;
            }
            /* AI 말풍선 (왼쪽, 회색) */
            .ai-bubble {
                background-color: #F2F2F7;
                color: black;
                margin-right: auto;
                border-bottom-left-radius: 5px;
            }
            /* 탭 스타일 변경 */
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            .stTabs [data-baseweb="tab"] {
                height: 50px;
                white-space: pre-wrap;
                background-color: #F2F2F7;
                border-radius: 15px;
                color: #8E8E93;
                font-weight: 600;
                padding: 0 20px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #007AFF !important;
                color: white !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_custom_css()

# --- 3. 시나리오 데이터 정의 (확장 가능) ---
SCENARIOS = {
    "airport": {
        "title": "공항 입국 심사 (Airport Immigration)",
        "icon": "✈️",
        "role": "깐깐하지만 공정한 한국 입국 심사관",
        "context": "사용자가 한국에 막 도착해서 입국 심사를 받고 있습니다.",
        "key_phrases": {
            "방문 목적이 무엇입니까?": "What is the purpose of your visit?",
            "여행으로 왔습니다.": "I am here for travel/tourism.",
            "얼마나 머무르실 예정입니까?": "How long will you be staying?",
            "일주일 정도 있을 겁니다.": "I will stay for about a week.",
            "숙소는 어디입니까?": "Where is your accommodation?"
        }
    },
    "restaurant": {
        "title": "식당 주문하기 (Ordering at a Restaurant)",
        "icon": "🍜",
        "role": "친절하고 활기찬 서울 맛집 식당 이모님",
        "context": "사용자가 식당에 들어와서 메뉴를 고르고 주문을 하려고 합니다.",
        "key_phrases": {
            "어서 오세요! 몇 분이세요?": "Welcome! How many people?",
            "두 명이에요.": "Two people, please.",
            "여기요, 주문할게요.": "Excuse me, I'd like to order.",
            "이거 덜 맵게 해주세요.": "Please make this less spicy.",
            "반찬 좀 더 주세요.": "Can I get some more side dishes, please?"
        }
    },
    "market": {
        "title": "전통시장 쇼핑 (Traditional Market Shopping)",
        "icon": "🍎",
        "role": "인심 좋고 흥정을 좋아하는 시장 상인",
        "context": "사용자가 활기찬 시장에서 물건을 구경하고 가격을 물어봅니다.",
        "key_phrases": {
            "이거 얼마예요?": "How much is this?",
            "좀 깎아주세요.": "Please give me a discount.",
            "맛 좀 봐도 될까요?": "Can I taste this?",
            "너무 비싸요.": "It's too expensive.",
            "많이 파세요!": "Have a great sale! (Goodbye greeting)"
        }
    }
}

# --- 4. Helper 함수들 (TTS, AI 모델) ---

def text_to_speech_autoplay(text):
    """gTTS를 사용하여 텍스트를 음성으로 변환하고 자동 재생 가능한 오디오 태그를 반환합니다."""
    try:
        tts = gTTS(text=text, lang='ko', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                md = f"""
                    <audio controls autoplay style="height: 30px; margin-top: 5px;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """
            os.unlink(fp.name)
            return md
    except Exception as e:
        return f"<span>(오디오 오류: {e})</span>"

def get_ai_response(messages, scenario_key):
    """Gemini Pro 모델을 사용하여 답변을 생성합니다 (검색 기능 포함)."""
    try:
        # 2026년 세계관 고정 프롬프트
        current_time_str = "2026년 1월 31일 토요일"
        
        system_instruction = f"""
        [기본 설정]
        현재 시각: {current_time_str}
        장소: 대한민국
        중요 사실: 현재 대한민국 대통령은 이재명입니다. (2025년 취임)

        [역할 및 상황]
        당신의 역할은 '{SCENARIOS[scenario_key]['role']}'입니다.
        상황: {SCENARIOS[scenario_key]['context']}

        [대화 지침]
        1. 사용자의 한국어 학습을 돕는 튜터로서, 자연스럽고 몰입감 있는 대화를 이끌어가세요.
        2. 구글 검색 도구를 사용할 수 있습니다. 최신 정보(날씨, 뉴스 등)가 필요하면 검색하되, 위의 [기본 설정](2026년 날짜, 대통령)과 충돌하는 검색 결과는 무시하고 기본 설정을 따르세요.
        3. 답변은 너무 길지 않게, 실제 대화처럼 하세요.
        """

        # 실시간 검색 툴 설정
        tools = [{'google_search_retrieval': {}}]
        model = genai.GenerativeModel('gemini-pro', system_instruction=system_instruction, tools=tools)

        # 메시지 기록 변환
        gemini_messages = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [m["content"]]})

        response = model.generate_content(gemini_messages)
        return response.text
    except Exception as e:
        return f"(AI 응답 오류가 발생했습니다: {e})"


# --- 5. 메인 앱 로직 ---

def main():
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_scenario" not in st.session_state:
        st.session_state.selected_scenario = "airport"  # 기본값

    # 메인 화면 최상단: 테마 선택
    scenario_options = {k: v["title"] for k, v in SCENARIOS.items()}
    selected_key = st.selectbox(
        "오늘 어디서 연습할까요? (Select Scene)",
        options=list(scenario_options.keys()),
        format_func=lambda x: scenario_options[x],
        key="scenario_selector"
    )
    if selected_key != st.session_state.selected_scenario:
        st.session_state.selected_scenario = selected_key
        st.session_state.messages = []
        st.rerun()

    current_scenario = SCENARIOS[st.session_state.selected_scenario]

    # 선택된 테마 제목 (h1으로 강조)
    st.markdown(f"<h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1>", unsafe_allow_html=True)
    st.caption(f"💡 역할: {current_scenario['role']}")

    # 탭 구성
    tab1, tab2 = st.tabs(["📖 표현 익히기 (Learn)", "🗣️ 실전 대화 (Roleplay)"])

    # 탭 1: 표현 익히기
    with tab1:
        st.markdown("### 핵심 표현을 배워보세요!")
        for kor, eng in current_scenario['key_phrases'].items():
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{kor}**")
                    st.caption(eng)
                with col2:
                    # TTS 버튼 (간단한 구현)
                    if st.button("🔊 듣기", key=f"tts_{kor}"):
                        st.markdown(text_to_speech_autoplay(kor), unsafe_allow_html=True)
                st.divider()

    # 탭 2: 실전 대화 (채팅 인터페이스)
    with tab2:
        chat_container = st.container()
        
        # 대화 기록 표시
        with chat_container:
            if not st.session_state.messages:
                 st.info("👋 대화를 시작해보세요! (예: '안녕하세요')")

            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-bubble user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
                else:
                    # AI 메시지와 TTS 버튼
                    st.markdown(f'<div class="chat-bubble ai-bubble">{message["content"]}</div>', unsafe_allow_html=True)
                    # 이전 메시지에 대한 TTS 재생 버튼 (선택 사항)
                    # st.markdown(text_to_speech_autoplay(message["content"]), unsafe_allow_html=True)
        
        # 사용자 입력 처리
        if prompt := st.chat_input("한국어로 대화해보세요..."):
            # 사용자 메시지 추가 및 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                 st.markdown(f'<div class="chat-bubble user-bubble">{prompt}</div>', unsafe_allow_html=True)

            # AI 응답 생성
            with st.spinner(f"{current_scenario['icon']} AI가 답변을 생각 중입니다..."):
                ai_response_text = get_ai_response(st.session_state.messages, st.session_state.selected_scenario)
            
            # AI 응답 추가, 표시 및 TTS 자동 재생
            st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
            with chat_container:
                st.markdown(f'<div class="chat-bubble ai-bubble">{ai_response_text}</div>', unsafe_allow_html=True)
                # 답변 자동 재생 (선택 사항, 너무 시끄러우면 주석 처리)
                st.markdown(text_to_speech_autoplay(ai_response_text), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
