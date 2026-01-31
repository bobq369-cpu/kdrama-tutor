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
    layout="centered",  # 모바일 느낌을 위해 중앙 정렬
    initial_sidebar_state="collapsed"  # 사이드바 기본 숨김
)

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("API 키가 설정되지 않았습니다. 스트림릿 설정에서 GOOGLE_API_KEY를 추가해주세요.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. iMessage 스타일 화이트 테마 CSS ---
def inject_custom_css():
    st.markdown(
        """
        <style>
            /* [핵심] 상단 헤더 공간 완전 삭제 (이게 범인입니다) */
            header[data-testid="stHeader"] {
                display: none !important;
            }

            /* [핵심] 메인 화면 여백 강제 제거 (천장에 붙이기) */
            .main .block-container {
                padding-top: 10px !important; /* 60px -> 10px로 강제 축소 */
                margin-top: 0px !important;
                max-width: 700px;
            }

            /* 전체 배경 및 폰트 */
            .stApp {
                background-color: #FFFFFF;
                font-family: 'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            /* (나머지 기존 스타일 유지) */
            .kakao-user-wrap { display: flex; justify-content: flex-end; margin-bottom: 10px; }
            .kakao-ai-wrap { display: flex; justify-content: flex-start; margin-bottom: 10px; align-items: flex-start; }
            .kakao-user-bubble { width: fit-content; max-width: 70%; word-wrap: break-word; }
            .kakao-ai-bubble { width: fit-content; max-width: 100%; word-wrap: break-word; }
            .kakao-ai-avatar { flex-shrink: 0; }
            .kakao-chat-img { max-width: 100%; border-radius: 12px; margin-top: 8px; }
            .kakao-correction { font-size: 13px; color: #8B0000; margin-top: 8px; padding: 8px 12px; background: #FFF5F5; border-radius: 10px; }
            .tts-player-wrap { margin-top: 8px; padding: 8px 12px; background: #F8F8F8; border-radius: 12px; }
            .tts-player-wrap audio { width: 100%; height: 36px; outline: none; }
            .tts-player-wrap audio::-webkit-media-controls-panel { background: transparent; }
        </style>
        """,
        unsafe_allow_html=True
    )

def inject_back_button_css():
    """뒤로가기 버튼을 화면 좌측 상단에 '공중부양(Fixed)' 시켜서 고정"""
    st.markdown(
        """
        <style>
            /* 버튼을 화면 왼쪽 위에 나사로 박듯이 고정 */
            div[data-testid="stVerticalBlock"] .stButton:first-of-type {
                position: fixed !important;
                top: 15px !important;   /* 맨 위에서 15px */
                left: 15px !important;  /* 왼쪽에서 15px */
                z-index: 99999 !important; /* 제일 위에 표시 */
                width: auto !important;
            }

            /* 버튼 디자인 (동그라미) */
            div[data-testid="stVerticalBlock"] .stButton:first-of-type button {
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                background-color: white !important;
                border: 1px solid #eee !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def inject_home_card_css():
    """홈 화면에서만 적용: 버튼을 큰 카드처럼 스타일링 (div.stButton > button)"""
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
                transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
            }
            div.stButton > button:hover {
                transform: translateY(-5px) !important;
                border-color: #007AFF !important;
                box-shadow: 0 8px 24px rgba(0,122,255,0.15) !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_custom_css()

# --- 3. 동적 이미지 갤러리 (모듈 로드 시 한 번만, 캐싱 불필요) ---
IMAGE_GALLERY = {
    "menu": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4",
    "passport": "https://images.unsplash.com/photo-1544015759-42b786315268",
    "money": "https://images.unsplash.com/photo-1554672723-bca4ef185960",
    "baggage": "https://images.unsplash.com/photo-1553531384-cc64ac80f931",
}

# --- 4. 시나리오 데이터 정의 (모듈 로드 시 한 번만, 확장 가능) ---
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

# --- 5. Helper 함수들 (TTS, AI 모델) ---

def strip_for_tts(text):
    """TTS용: [IMAGE: key] 태그와 || 교정 내용을 제거한 순수 대화 텍스트 반환."""
    if not text:
        return ""
    t = re.sub(r"\[IMAGE:\s*\w+\]", "", text).strip()
    if "||" in t:
        t = t.split("||", 1)[0].strip()
    return t or ""


@st.cache_data(show_spinner=False)
def _generate_tts_html_cached(clean_text):
    """동일 문장은 캐시에서 반환 (gTTS 재호출 없음)."""
    if not clean_text:
        return ""
    try:
        tts = gTTS(text=clean_text, lang='ko', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                onplay_js = 'onplay="var s=this;document.querySelectorAll(\'audio\').forEach(function(a){if(a!==s)a.pause();});"'
                md = f"""
                    <div class="tts-player-wrap">
                    <audio controls {onplay_js}>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    </div>
                    """
            os.unlink(fp.name)
            return md
    except Exception as e:
        return f"<span>(오디오 오류: {e})</span>"


def text_to_speech_html(text, autoplay=False):
    """gTTS로 음성 변환 후 오디오 HTML 반환. autoplay=True면 자동 재생. (캐시 사용)"""
    clean_text = strip_for_tts(text)
    html = _generate_tts_html_cached(clean_text)
    if not html:
        return ""
    if autoplay:
        html = html.replace("<audio controls ", "<audio controls autoplay ", 1)
    return html

# API에서 사용 가능한 모델 우선순위 (404 시 다음 모델 시도)
GEMINI_MODEL_NAMES = [
    "gemini-2.5-flash",   # 2025년 공식 Stable
    "gemini-2.0-flash",   # 2세대 안정
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]

def get_ai_response(messages, scenario_key):
    """Gemini 모델을 사용하여 답변을 생성합니다 (순수 대화 모델)."""
    current_time_str = "2026년 1월 31일 토요일"
    image_keys_desc = ", ".join(f"'{k}'" for k in IMAGE_GALLERY.keys())
    system_instruction = f"""
[기본 설정]
현재 시각: {current_time_str}
장소: 대한민국
중요 사실: 현재 대한민국 대통령은 이재명입니다. (2025년 취임)

[역할 및 상황]
당신의 역할은 '{SCENARIOS[scenario_key]['role']}'입니다.
상황: {SCENARIOS[scenario_key]['context']}

[대화 지침]
1. 너는 한국어 튜터로서 사용자의 질문에 친절하게 답하라. 자연스럽고 몰입감 있는 대화를 이끌어가고, 답변은 너무 길지 않게 실제 대화처럼 하라.
2. 상황에 맞는 이미지가 필요하면, 해당 문장 끝에 [IMAGE: key] 태그를 붙여라. 사용 가능한 key: {image_keys_desc}. 예: 메뉴판을 건네줄 때는 [IMAGE: menu], 여권을 보여달라고 할 때는 [IMAGE: passport], 계산/돈 이야기 시 [IMAGE: money], 수하물 이야기 시 [IMAGE: baggage].
3. 사용자의 한국어가 어색하거나 틀렸다면, 답변 끝에 반드시 파이프 두 개(||)를 넣고 그 다음 줄에 교정 내용을 적어라. 예: "네, 알겠습니다.|| '알겠어요'가 더 자연스러워요."
"""

    gemini_messages = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        gemini_messages.append({"role": role, "parts": [m["content"]]})

    last_error = None
    for model_name in GEMINI_MODEL_NAMES:
        try:
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            response = model.generate_content(gemini_messages)
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            err_lower = err_str.lower()
            if "404" in err_lower or "not found" in err_lower:
                continue
            if "429" in err_str or "quota" in err_lower or "exceeded" in err_lower:
                retry_sec = 60
                match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err_lower)
                if match:
                    retry_sec = max(1, int(float(match.group(1))))
                return (
                    f"⚠️ 무료 사용량이 소진되었습니다.\n\n"
                    f"잠시 후(약 {retry_sec}초) 다시 시도해주세요. "
                    f"할당량·결제는 Google AI Studio에서 확인할 수 있습니다."
                )
            return f"(AI 응답 오류가 발생했습니다: {e})"

    return f"(AI 응답 오류가 발생했습니다: {last_error})"


def parse_ai_message(content):
    """AI 응답에서 말풍선 텍스트, 이미지 키 목록, 교정 문구를 분리해 반환."""
    raw = content or ""
    image_keys = re.findall(r"\[IMAGE:\s*(\w+)\]", raw)
    display = re.sub(r"\[IMAGE:\s*\w+\]", "", raw).strip()
    correction = None
    if "||" in display:
        parts = display.split("||", 1)
        display = parts[0].strip()
        correction = parts[1].strip() if len(parts) > 1 else None
    return display, image_keys, correction


# --- 6. 스마트 답장 바 (Transform 방식 미세 조정) ---
def render_smart_reply_bar(current_scenario):
    """
    [무결점 버전] 너비 깨짐(Squash) 방지 + 안전한 위치 이동 (Transform 사용)
    """
    # ==========================================
    # 🎛️ 사장님 전용 미세 조정 패널
    # ==========================================

    # 1. Y축 (위/아래 이동)
    # - "0px" : 가만히 둠 (기본값)
    # - "-10px" : 위로 살짝 띄우기 (공중부양)
    # - "10px" : 아래로 살짝 내리기
    adjust_y = "0px"

    # 2. X축 (좌/우 이동)
    adjust_x = "0px"

    # ==========================================

    # CSS 적용 (Transform 사용 -> 레이아웃 절대 안 깨짐)
    st.markdown(f"""
    <style>
    /* 1. id='safe-reply-container'를 가진 구역을 찾아서 안전하게 이동 */
    div[data-testid="stVerticalBlock"]:has(#safe-reply-container) {{
        width: 100% !important;      /* 가로 꽉 채우기 (강제) */
        min-width: 100% !important;  /* 최소 너비 보장 (찌그러짐 방지) */

        /* [핵심] 좌표계 대신 Transform을 사용하여 시각적으로만 이동 */
        transform: translate({adjust_x}, {adjust_y}) !important;

        z-index: 1;
    }}
    </style>
    """, unsafe_allow_html=True)

    # 앵커 및 버튼 출력
    with st.container():
        st.markdown('<div id="safe-reply-container"></div>', unsafe_allow_html=True)  # 좌표 타겟용 앵커

        st.divider()
        st.caption("💡 추천 표현 (클릭하면 전송됩니다)")

        phrases = list(current_scenario["key_phrases"].items())
        col_a, col_b = st.columns(2)
        for idx, (kor, eng) in enumerate(phrases):
            with col_a if idx % 2 == 0 else col_b:
                if st.button(f"{kor}\n({eng})", key=f"phrase_{idx}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": kor})
                    st.rerun()


# --- 7. 메인 앱 로직 ---

def main():
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_scenario" not in st.session_state:
        st.session_state.selected_scenario = "airport"
    if "current_page" not in st.session_state:
        st.session_state.current_page = "HOME"

    # ----- 홈 화면 (카드형 그리드) -----
    if st.session_state.current_page == "HOME":
        inject_home_card_css()
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>오늘 어디서 연습할까요?</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 2rem;'>Select a scene to start learning</p>", unsafe_allow_html=True)

        items = list(SCENARIOS.items())
        col0, col1 = st.columns(2)
        for j, (key, sc) in enumerate(items):
            col = col0 if j % 2 == 0 else col1
            with col:
                label = f"{sc['icon']} {sc['title']}\n\n{sc['context']}"
                if st.button(label, key=f"start_{key}", use_container_width=True):
                    st.session_state.current_page = "LEARNING"
                    st.session_state.selected_scenario = key
                    st.session_state.messages = []
                    st.session_state.tts_cache = {}
                    st.rerun()
        return

    # ----- 학습 화면 (LEARNING) -----
    current_scenario = SCENARIOS[st.session_state.selected_scenario]
    inject_back_button_css()

    # 뒤로 가기: 좌측 상단 작은 원형 버튼
    if st.button("✕", key="back_btn"):
        st.session_state.current_page = "HOME"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 선택된 테마 제목 (h1으로 강조) — 상단에는 제목·역할만. 추천 표현 바 호출 없음.
    st.markdown(f"<h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1>", unsafe_allow_html=True)
    st.caption(f"💡 역할: {current_scenario['role']}")

    # 단일 채팅 인터페이스 (대화 기록)
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 대화를 시작해보세요! 표현 버튼을 누르거나 직접 입력해보세요.")

        if "tts_cache" not in st.session_state:
            st.session_state.tts_cache = {}

        messages = st.session_state.messages
        for i, message in enumerate(messages):
            if message["role"] == "user":
                safe_content = html.escape(message["content"])
                user_html = (
                    '<div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">'
                    '<div style="background-color: #FEE500; padding: 10px 15px; border-radius: 15px; '
                    'border-top-right-radius: 0; font-size: 16px; color: black; max-width: 70%; width: fit-content; '
                    'box-shadow: 1px 1px 2px rgba(0,0,0,0.1); word-wrap: break-word;">'
                    f"{safe_content}"
                    "</div></div>"
                )
                st.markdown(user_html, unsafe_allow_html=True)
            else:
                bubble_text, image_keys, correction = parse_ai_message(message["content"])
                safe_bubble = html.escape(bubble_text) if bubble_text else ""
                is_last_message = (i == len(messages) - 1)
                should_autoplay = is_last_message and st.session_state.get("play_tts")
                if i not in st.session_state.tts_cache:
                    st.session_state.tts_cache[i] = text_to_speech_html(message["content"], autoplay=False)
                tts_html = st.session_state.tts_cache[i] or ""
                if tts_html and should_autoplay:
                    tts_html = tts_html.replace("<audio controls ", "<audio controls autoplay ", 1)
                correction_html = ""
                if correction:
                    safe_correction = html.escape(correction)
                    correction_html = f'<div class="kakao-correction">📝 빨간펜 선생님: {safe_correction}</div>'
                img_tags = ""
                for key in image_keys:
                    if key in IMAGE_GALLERY:
                        url = html.escape(IMAGE_GALLERY[key])
                        img_tags += f'<img class="kakao-chat-img" src="{url}" alt="">'
                ai_bubble_inner = safe_bubble + tts_html + correction_html
                ai_html = (
                    '<div style="display: flex; justify-content: flex-start; margin-bottom: 10px; align-items: flex-start;">'
                    '<div style="width: 40px; height: 40px; min-width: 40px; border-radius: 50%; background-color: #EFEFEF; '
                    'display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 20px;">🤖</div>'
                    '<div style="max-width: 70%;">'
                    '<div style="font-size: 12px; color: #666; margin-bottom: 3px;">AI 튜터</div>'
                    '<div style="background-color: #FFFFFF; border: 1px solid #E5E5E5; padding: 10px 15px; '
                    'border-radius: 15px; border-top-left-radius: 0; font-size: 16px; color: black; max-width: 100%; '
                    'width: fit-content; box-shadow: 1px 1px 2px rgba(0,0,0,0.05); word-wrap: break-word;">'
                    f"{ai_bubble_inner}"
                    "</div>"
                    f"{img_tags}"
                    "</div></div>"
                )
                st.markdown(ai_html, unsafe_allow_html=True)

        if st.session_state.get("play_tts"):
            st.session_state.play_tts = False

    # [유일한 위치] 추천 표현: 채팅 루프 직후, st.chat_input 직전. (구분선은 함수 내부에서 처리)
    render_smart_reply_bar(current_scenario)

    # 채팅 입력: 입력 시 메시지 추가 후 rerun
    if prompt := st.chat_input("한국어로 대화해보세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # 마지막 메시지가 사용자 것이면 AI 응답 생성 후 추가하고 rerun
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.spinner(f"{current_scenario['icon']} AI가 답변을 생각 중입니다..."):
            ai_response_text = get_ai_response(st.session_state.messages, st.session_state.selected_scenario)
        st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
        if "play_tts" not in st.session_state:
            st.session_state.play_tts = False
        st.session_state.play_tts = True
        st.rerun()


if __name__ == "__main__":
    main()

# 서버 업데이트용 강제 주석 (v2.0)