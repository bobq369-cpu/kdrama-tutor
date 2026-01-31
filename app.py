import streamlit as st
import google.generativeai as genai
import os
import re
import html
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

# --- 2. CSS 설정 (상단 여백 제거 + 뒤로가기/추천 버튼 격리) ---
def inject_custom_css():
    # ============================================================
    # 🎛️ [사장님 전용 리모컨]
    # ============================================================
    # 상단 여백 (화면 맨 위에서 콘텐츠까지의 간격)
    main_top_padding = "0px"   # 0px=띄우지 않음, 20px=조금 띄움, 40px=더 띄움
    main_top_margin = "0px"    # 마진으로도 조절 가능

    # 뒤로가기 버튼 위치
    back_x = "15px"   # 왼쪽 간격
    back_y = "15px"   # 위쪽 간격

    # 제목(h1) 위치 조절 (테마 선택 후 화면의 큰 제목)
    title_margin_top = "-350px"      # 제목 위쪽 여백 (숫자 키우면 제목이 아래로 내려감)
    title_padding_top = "10px"    # 제목 위쪽 패딩
    title_margin_bottom = "0px"   # 제목 아래쪽 여백
    # ============================================================

    st.markdown(
        f"""
        <style>
            /* 1. 상단 헤더 숨기기 */
            header[data-testid="stHeader"] {{
                display: none !important;
            }}

            /* 2. 메인 화면 상단 여백 (리모컨 적용) */
            .main .block-container {{
                padding-top: {main_top_padding} !important;
                margin-top: {main_top_margin} !important;
                max-width: 700px;
            }}

            /* 3. 제목만 이동 (learning-title-wrap만 타겟 → 다른 요소 안 움직임) */
            #learning-title-wrap {{
                margin-top: {title_margin_top} !important;
                padding-top: {title_padding_top} !important;
                margin-bottom: {title_margin_bottom} !important;
            }}

            /* 4. 전체 폰트 및 배경 */
            .stApp {{
                background-color: #FFFFFF;
                font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
            }}

            /* [안전장치 1] 뒤로가기 버튼 (리모컨 적용) */
            div:has(div#back-btn-area) .stButton button {{
                position: fixed !important;
                left: {back_x} !important;
                top: {back_y} !important;
                z-index: 99999 !important;
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                background-color: white !important;
                border: 1px solid #eee !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
                padding: 0 !important;
            }}

            /* [안전장치 2] 추천 표현 버튼 디자인 통일 */
            div:has(div#smart-reply-area) .stButton button {{
                position: static !important;
                width: 100% !important;
                min-height: 80px !important;
                height: auto !important;
                background-color: #FFFFFF !important;
                border: 1px solid #E5E5E5 !important;
                color: #4B5563 !important;
                border-radius: 12px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
                white-space: pre-wrap !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                padding: 10px !important;
                transition: all 0.2s ease !important;
            }}

            div:has(div#smart-reply-area) .stButton button:hover {{
                background-color: #F9FAFB !important;
                border-color: #6B7280 !important;
                transform: translateY(-2px);
            }}

            .kakao-correction {{ font-size: 13px; color: #8B0000; margin-top: 8px; padding: 8px 12px; background: #FFF5F5; border-radius: 10px; }}
            .tts-player-wrap audio {{ width: 100%; height: 36px; outline: none; }}
        </style>
        """,
        unsafe_allow_html=True
    )

def inject_home_card_css():
    st.markdown(
        """
        <style>
            div.stButton > button {
                background-color: #FFFFFF !important;
                height: 180px !important;
                min-height: 180px !important;
                border-radius: 20px !important;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
                border: 1px solid rgba(0,0,0,0.06) !important;
                text-align: left !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                padding: 1.25rem 1.5rem !important;
                font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
                color: #1a1a1a !important;
                white-space: pre-wrap !important;
                line-height: 1.45 !important;
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
    try:
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_instruction)
        gemini_messages = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} for m in messages]
        response = model.generate_content(gemini_messages)
        return response.text
    except Exception as e:
        return f"(AI 응답 오류: {e})"

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


# --- 4. [복구 완료] 스마트 답장 바 (Relative 방식 + 격리) ---
def render_smart_reply_bar(current_scenario):
    """
    사장님이 원하셨던 '그 버전'입니다.
    안전한 Relative 방식을 사용하며, 뒤로가기 버튼의 스타일 간섭을 받지 않도록 격리(Marker)했습니다.
    """
    # ==========================================
    # 🎛️ 사장님 전용 미세 조정 패널 (숫자만 바꾸세요)
    # ==========================================
    
    # 1. Y축 (채팅과 추천 표현 사이 여백) — 채팅 끝에만 margin이라 제목 안 움직임
    # - "0px" : 기본
    # - "20px" : 추천 표현을 아래로 띄움 (채팅과 간격 생김)
    # - "40px" : 더 아래로
    adjust_y = "0px"

    # 2. X축 (좌/우 여백)
    adjust_x = "0px" 
    
    # ==========================================

    # CSS 적용 (채팅 끝 마커에 margin-bottom → 추천 표현만 아래로, 제목은 그대로)
    st.markdown(f"""
    <style>
    /* 채팅 끝 블록에만 아래 여백 → 제목/채팅은 고정, 추천 표현만 아래로 내려감 */
    div:has(div#chat-area-end) {{
        margin-bottom: {adjust_y} !important;
    }}
    /* 추천 표현 좌우만 이동 */
    div[data-testid="stVerticalBlock"]:has(div#smart-reply-area) {{
        margin-left: {adjust_x} !important;
        width: 100% !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        # [핵심] 이 마커가 있어야 스타일이 충돌하지 않습니다!
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

    if st.session_state.current_page == "HOME":
        inject_home_card_css()
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>오늘 어디서 연습할까요?</h1>", unsafe_allow_html=True)
        
        items = list(SCENARIOS.items())
        col0, col1 = st.columns(2)
        for j, (key, sc) in enumerate(items):
            with col0 if j % 2 == 0 else col1:
                if st.button(f"{sc['icon']} {sc['title']}\n\n{sc['context']}", key=f"start_{key}", use_container_width=True):
                    st.session_state.current_page = "LEARNING"
                    st.session_state.selected_scenario = key
                    st.session_state.messages = []
                    st.rerun()
        return

    # [LEARNING PAGE]
    current_scenario = SCENARIOS[st.session_state.selected_scenario]
    
    # [수정] 뒤로가기 버튼 격리 (Marker 사용) -> 추천 버튼에 절대 영향 안 줌
    with st.container():
        st.markdown('<div id="back-btn-area"></div>', unsafe_allow_html=True)
        if st.button("✕", key="back_btn"):
            st.session_state.current_page = "HOME"
            st.rerun()

    # 제목만 감싸는 wrapper (이 ID만 스타일하면 제목만 옮겨짐)
    st.markdown(f"<div id='learning-title-wrap'><h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1></div>", unsafe_allow_html=True)
    st.caption(f"💡 역할: {current_scenario['role']}")

    # 채팅 출력
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
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

        # 채팅 끝 마커 (이 블록에 margin-bottom 주면 추천 표현만 아래로 내려감, 제목 안 움직임)
        st.markdown('<div id="chat-area-end"></div>', unsafe_allow_html=True)

    # 추천 표현 (사장님이 원하셨던 '그 버전' + 찌그러짐 방지 포함)
    render_smart_reply_bar(current_scenario)

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