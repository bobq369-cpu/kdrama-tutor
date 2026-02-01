import streamlit as st
import google.generativeai as genai
import os
import re
import html
import time
from gtts import gTTS
import tempfile
import base64

# --- 1. 기본 설정 및 비밀키 가져오기 ---
st.set_page_config(
    page_title="K-Tutor Global",
    page_icon="🇰🇷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("API 키가 설정되지 않았습니다. 스트림릿 설정에서 GOOGLE_API_KEY를 추가해주세요.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. CSS 설정 (채팅 화면 및 공통) ---
def inject_custom_css():
    # [사장님 전용 리모컨 좌표]
    back_x = "20px"
    back_y = "20px"
    prompt_y = "50px"

    st.markdown(
        f"""
        <style>
            /* 기본 폰트 및 배경 설정 */
            .stApp {{ background-color: #F8F9FA; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; }}
            header[data-testid="stHeader"] {{ display: none !important; }}
            .main .block-container {{ max-width: 700px; padding-top: 2rem; }}

            /* [채팅 화면] 뒤로가기 버튼 (왼쪽 상단 고정) */
            div[data-testid="stVerticalBlock"]:has(div#back-btn-area) {{
                position: fixed !important; top: {back_y} !important; left: {back_x} !important;
                width: auto !important; height: auto !important; z-index: 999999 !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#back-btn-area) .stButton button {{
                width: 32px !important; height: 32px !important; border-radius: 50% !important;
                background-color: white !important; border: 1px solid #eee !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important; padding: 0 !important;
                line-height: 1 !important; font-size: 14px !important;
            }}

            /* [채팅 화면] 안내 박스 위치 조정 */
            div[data-testid="stVerticalBlock"]:has(div#start-prompt-marker) {{
                transform: translate(0px, {prompt_y}) !important; position: relative; z-index: 8;
            }}

            /* [채팅 화면] 추천 표현 바 정렬 */
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area) {{
                width: 100% !important; max-width: 700px !important; margin: 0 auto !important;
            }}
            /* 추천 표현 버튼 스타일 */
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area) .stButton button {{
                width: 100% !important; min-height: 60px !important; height: auto !important;
                background-color: #FFFFFF !important; border: 1px solid #E5E5E5 !important;
                color: #4B5563 !important; border-radius: 12px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
                white-space: pre-wrap !important; word-break: keep-all !important;
                display: flex; align-items: center; justify-content: center; text-align: center; padding: 12px !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area) .stButton button:hover {{
                background-color: #F9FAFB !important; transform: translateY(-2px);
            }}

            /* 기타 유틸리티 */
            .kakao-correction {{ font-size: 13px; color: #8B0000; margin-top: 8px; padding: 8px 12px; background: #FFF5F5; border-radius: 10px; }}
            .tts-player-wrap audio {{ width: 100%; height: 36px; outline: none; }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- [핵심] 홈 화면 카드 디자인 CSS ---
def inject_home_card_css():
    st.markdown(
        """
        <style>
            /* 홈 화면의 시나리오 카드 버튼 전용 스타일 */
            .scenario-card-button > button {
                background-color: #FFFFFF !important;
                border: 1px solid #E6E6E6 !important; /* 은은한 테두리 */
                border-radius: 20px !important; /* 둥근 모서리 */
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important; /* 부드러운 그림자 */
                padding: 30px 25px !important; /* 내부 여백 */
                height: auto !important; 
                min-height: 180px !important; /* 카드 최소 높이 설정 */
                
                text-align: left !important;
                display: flex !important;
                flex-direction: column !important; /* 내용 세로 배치 */
                align-items: flex-start !important; /* 왼쪽 정렬 */
                justify-content: flex-start !important; /* 상단 정렬 */
                
                white-space: pre-wrap !important; /* 줄바꿈 허용 */
                font-family: 'Pretendard', sans-serif !important;
                color: #1a1a1a !important;
                line-height: 1.6 !important;
                transition: all 0.2s ease !important; /* 부드러운 움직임 */
            }
            
            /* 마우스 올렸을 때 효과 */
            .scenario-card-button > button:hover {
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1) !important;
                transform: translateY(-3px); /* 살짝 떠오름 */
                border-color: #d0d0d0 !important;
            }

            /* 홈 화면 제목 스타일 */
            .home-title {
                text-align: center;
                margin-bottom: 3rem;
                font-weight: 700;
                color: #333;
                font-size: 2.2rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_custom_css()

# --- 3. 데이터 및 헬퍼 함수 ---
IMAGE_GALLERY = {
    "menu": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4",
    "passport": "https://images.unsplash.com/photo-1544015759-42b786315268",
    "money": "https://images.unsplash.com/photo-1554672723-bca4ef185960",
    "baggage": "https://images.unsplash.com/photo-1553531384-cc64ac80f931",
}

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

def strip_for_tts(text):
    if not text: return ""
    t = re.sub(r"\[IMAGE:\s*\w+\]", "", text).strip()
    if "||" in t: t = t.split("||", 1)[0].strip()
    return t or ""

@st.cache_data(show_spinner=False)
def _generate_tts_html_cached(clean_text):
    if not clean_text: return ""
    try:
        tts = gTTS(text=clean_text, lang='ko', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                md = f"""<div class="tts-player-wrap"><audio controls><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio></div>"""
            os.unlink(fp.name)
            return md
    except Exception as e:
        return f"<span>(오디오 오류: {e})</span>"

def text_to_speech_html(text, autoplay=False):
    html = _generate_tts_html_cached(strip_for_tts(text))
    if autoplay and html: html = html.replace("<audio controls ", "<audio controls autoplay ", 1)
    return html

def get_ai_response(messages, scenario_key):
    system_instruction = f"""
    역할: {SCENARIOS[scenario_key]['role']}
    상황: {SCENARIOS[scenario_key]['context']}
    지침: 한국어 튜터로서 친절하게 답하고, 필요시 [IMAGE: key] 태그 사용. 오류 교정 시 끝에 || 사용.
    """
    model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_instruction)
    gemini_messages = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} for m in messages]
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            response = model.generate_content(gemini_messages)
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                time.sleep(4)
                continue
            return f"(AI 응답 오류: {e})"
    return f"(AI 응답 오류: {last_error})"

def parse_ai_message(content):
    raw = content or ""
    image_keys = re.findall(r"\[IMAGE:\s*(\w+)\]", raw)
    display = re.sub(r"\[IMAGE:\s*\w+\]", "", raw).strip()
    correction = None
    if "||" in display:
        parts = display.split("||", 1)
        display = parts[0].strip()
        correction = parts[1].strip() if len(parts) > 1 else None
    return display, image_keys, correction


# --- 4. 추천 표현 바 ---
def render_smart_reply_bar(current_scenario):
    with st.container():
        st.markdown('<div id="smart-reply-area"></div>', unsafe_allow_html=True)
        st.divider()
        st.caption("💡 추천 표현 (클릭하면 전송됩니다)")
        
        phrases = list(current_scenario["key_phrases"].items())
        col_a, col_b = st.columns(2)
        for idx, (kor, eng) in enumerate(phrases):
            with col_a if idx % 2 == 0 else col_b:
                if st.button(f"{kor}\n({eng})", key=f"phrase_{idx}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": kor})
                    st.rerun()


# --- 5. 메인 앱 로직 ---
def main():
    if "messages" not in st.session_state: st.session_state.messages = []
    if "selected_scenario" not in st.session_state: st.session_state.selected_scenario = "airport"
    if "current_page" not in st.session_state: st.session_state.current_page = "HOME"

    # ==========================================
    # [HOME 페이지] - 카드 디자인 적용
    # ==========================================
    if st.session_state.current_page == "HOME":
        inject_home_card_css() # 홈 화면 전용 CSS 주입
        
        st.markdown("<h1 class='home-title'>오늘 어디서 연습할까요?</h1>", unsafe_allow_html=True)
        
        items = list(SCENARIOS.items())
        col0, col1 = st.columns(2)
        for j, (key, sc) in enumerate(items):
            with col0 if j % 2 == 0 else col1:
                # 버튼을 감싸는 div에 클래스 적용하여 카드 스타일링
                st.markdown('<div class="scenario-card-button">', unsafe_allow_html=True)
                # 버튼 텍스트에 줄바꿈을 넣어 제목과 내용 분리
                button_text = f"{sc['icon']} {sc['title']}\n\n{sc['context']}"
                if st.button(button_text, key=f"start_{key}", use_container_width=True):
                    st.session_state.current_page = "LEARNING"
                    st.session_state.selected_scenario = key
                    st.session_state.messages = []
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        return

    # ==========================================
    # [LEARNING 페이지] - 채팅 화면
    # ==========================================
    current_scenario = SCENARIOS[st.session_state.selected_scenario]
    
    # 1. 뒤로가기 버튼 (좌측 상단 고정)
    with st.container():
        st.markdown('<div id="back-btn-area"></div>', unsafe_allow_html=True)
        if st.button("✕", key="back_btn"):
            st.session_state.current_page = "HOME"
            st.rerun()

    # 2. 제목 & 역할 설명
    st.markdown(f"<div id='learning-title-wrap'><h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1></div>", unsafe_allow_html=True)
    st.markdown(f"<div id='role-caption-wrap'>💡 역할: {html.escape(current_scenario['role'])}</div>", unsafe_allow_html=True)

    # 3. 채팅창
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            with st.container():
                st.markdown('<div id="start-prompt-marker"></div>', unsafe_allow_html=True)
                st.info("👋 대화를 시작해보세요! 표현 버튼을 누르거나 직접 입력해보세요.")
        
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                st.markdown(f"""<div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
                <div style="background:#FEE500;padding:10px 15px;border-radius:15px;border-top-right-radius:0;box-shadow:1px 1px 2px rgba(0,0,0,0.1);">
                {html.escape(msg["content"])}</div></div>""", unsafe_allow_html=True)
            else:
                display, imgs, corr = parse_ai_message(msg["content"])
                tts_code = text_to_speech_html(msg["content"], autoplay=(i==len(st.session_state.messages)-1 and st.session_state.get("play_tts")))
                corr_html = f"<div class='kakao-correction'>📝 {html.escape(corr)}</div>" if corr else ""
                img_html = "".join([f"<img src='{IMAGE_GALLERY[k]}' class='kakao-chat-img'>" for k in imgs if k in IMAGE_GALLERY])
                
                st.markdown(f"""<div style="display:flex;justify-content:flex-start;margin-bottom:10px;">
                <div style="font-size:20px;margin-right:10px;">🤖</div>
                <div style="max-width:80%;">
                <div style="background:#FFF;border:1px solid #E5E5E5;padding:10px 15px;border-radius:15px;border-top-left-radius:0;">
                {html.escape(display)}{tts_code}{corr_html}</div>{img_html}</div></div>""", unsafe_allow_html=True)

        if st.session_state.get("play_tts"): st.session_state.play_tts = False

    # 4. 추천 표현 바
    render_smart_reply_bar(current_scenario)

    # 5. 입력창
    if prompt := st.chat_input("한국어로 대화해보세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.spinner("AI가 답변 중..."):
            ai_text = get_ai_response(st.session_state.messages, st.session_state.selected_scenario)
        st.session_state.messages.append({"role": "assistant", "content": ai_text})
        st.session_state.play_tts = True
        st.rerun()

if __name__ == "__main__":
    main()