import streamlit as st
import streamlit.components.v1 as components
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

# --- 2. CSS 설정 (상단 여백 + 뒤로가기/제목/추천 표현 격리) ---
def inject_custom_css():
    # ============================================================
    # 🎛️ [사장님 전용 리모컨]
    # ============================================================

    # [1] 전체 화면 상단 여백 (이걸 건드리면 전체가 다 같이 움직입니다)
    main_top_padding = "0px"
    main_top_margin = "0px"  # 최대한 위로 붙임

    # [2] 뒤로가기 버튼 위치 (고정됨)
    back_x = "15px"
    back_y = "15px"

    # [3] 제목(Title) 위치 미세 조정 (유체이탈 방식)
    title_x = "0px"    # 좌우 이동 (음수: 왼쪽, 양수: 오른쪽)
    title_y = "0px"    # 상하 이동 (음수: 위로, 양수: 아래로)

    # [4] 추천 표현 바 위치 (세션에 저장 → render_smart_reply_bar + 스크립트에서 사용)
    adjust_smart_y = "150px"
    adjust_smart_x = "0px"
    if "remocon" not in st.session_state:
        st.session_state.remocon = {}
    st.session_state.remocon["adjust_smart_x"] = adjust_smart_x
    st.session_state.remocon["adjust_smart_y"] = adjust_smart_y

    # [5] 역할 캡션("💡 역할: ...") 위치 (유체이탈)
    subtitle_x = "0px"
    subtitle_y = "0px"

    # [6] "대화를 시작해보세요!..." 안내 박스 위치 (유체이탈)
    prompt_x = "0px"
    prompt_y = "0px"
    # ============================================================

    st.markdown(
        f"""
        <style>
            /* 1. 헤더 숨기기 */
            header[data-testid="stHeader"] {{ display: none !important; }}

            /* 2. 메인 컨테이너 여백 */
            .main .block-container {{
                padding-top: {main_top_padding} !important;
                margin-top: {main_top_margin} !important;
                max-width: 700px;
            }}

            /* 3. [핵심] 제목 래퍼 스타일 (Transform 사용) */
            #learning-title-wrap {{
                transform: translate({title_x}, {title_y}) !important;
                margin-top: 10px !important;
                margin-bottom: 10px !important;
                padding: 0 !important;
                position: relative;
                z-index: 10;
            }}

            /* 4. 뒤로가기 버튼 (고정) */
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

            /* 5. 역할 캡션("💡 역할: ...") (유체이탈) */
            #role-caption-wrap {{
                position: relative !important;
                z-index: 9 !important;
                transform: translate({subtitle_x}, {subtitle_y}) !important;
            }}

            /* 6. "대화를 시작해보세요!..." 안내 박스: 마커 블록 + 다음 형제(실제 안내 박스) 둘 다 이동 */
            div:has(> #start-prompt-wrap),
            div:has(> #start-prompt-wrap) + div {{
                position: relative !important;
                z-index: 8 !important;
                transform: translate({prompt_x}, {prompt_y}) !important;
            }}

            /* 7. 추천 표현 바: (A) 마커가 직계자식인 블록 + 그 뒤 형제들 (B) 마커가 중첩된 경우 섹션 블록 전체 */
            div:has(> #smart-reply-area),
            div:has(> #smart-reply-area) ~ div,
            div:has(#smart-reply-area):has(> div:nth-child(2)):not(:has(div:has(#smart-reply-area):has(> div:nth-child(2)))),
            [data-testid="stVerticalBlock"]:has(#smart-reply-area):not(:has([data-testid="stVerticalBlock"]:has(#smart-reply-area))) {{
                position: relative !important;
                z-index: 1 !important;
                transform: translate({adjust_smart_x}, {adjust_smart_y}) !important;
            }}

            /* 추천 버튼 디자인 */
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

            /* 폰트 및 배경 */
            .stApp {{ background-color: #FFFFFF; font-family: 'Pretendard', 'Noto Sans KR', sans-serif; }}
        </style>
        """,
        unsafe_allow_html=True
    )
    # 추천 표현 바 위치: Streamlit DOM에서 #smart-reply-area가 있는 가장 안쪽 블록에 transform 적용
    st.markdown(
        f"""
        <script>
        (function() {{
            var x = "{adjust_smart_x}";
            var y = "{adjust_smart_y}";
            function apply() {{
                var blocks = document.querySelectorAll('[data-testid="stVerticalBlock"]');
                var target = null;
                for (var i = 0; i < blocks.length; i++) {{
                    if (blocks[i].querySelector('#smart-reply-area')) target = blocks[i];
                }}
                if (target) {{
                    target.style.setProperty('position', 'relative', 'important');
                    target.style.setProperty('z-index', '1', 'important');
                    target.style.setProperty('transform', 'translate(' + x + ', ' + y + ')', 'important');
                    target.style.setProperty('width', '100%', 'important');
                }}
            }}
            if (document.readyState === 'complete') apply();
            else window.addEventListener('load', apply);
            setTimeout(apply, 500);
        }})();
        </script>
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
                font-family: 'Pretendard', sans-serif !important;
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
                if attempt < max_retries - 1:
                    wait = 4
                    if "retry in" in err_str.lower():
                        match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err_str, re.I)
                        if match:
                            wait = max(3, min(10, int(float(match.group(1)) + 0.5)))
                    time.sleep(wait)
                    continue
                return "⏳ 지금은 요청이 많아 일시적으로 응답할 수 없어요. 잠시 후 다시 시도해 주세요. (무료 한도 초과)"
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


# --- 4. 추천 표현 바 위치 적용 (부모 문서 DOM 조작) ---
def _apply_smart_reply_position_script():
    """리모컨 값으로 추천 표현 바가 들어 있는 블록에 transform 적용. CSS 선택자가 Streamlit DOM에서 안 먹힐 때 사용."""
    components.html(
        """
        <script>
        (function() {
            var doc = window.parent.document;
            var el = doc.getElementById("smart-reply-area");
            if (!el) return;
            var x = el.getAttribute("data-x") || "0px";
            var y = el.getAttribute("data-y") || "0px";
            var blocks = doc.querySelectorAll("[data-testid='stVerticalBlock']");
            var target = null;
            for (var i = 0; i < blocks.length; i++) {
                if (blocks[i].querySelector("#smart-reply-area")) target = blocks[i];
            }
            if (target) {
                target.style.setProperty("position", "relative", "important");
                target.style.setProperty("z-index", "1", "important");
                target.style.setProperty("transform", "translate(" + x + ", " + y + ")", "important");
                target.style.setProperty("width", "100%", "important");
            }
        })();
        </script>
        """,
        height=0,
    )

# --- 5. 스마트 답장 바 ---
def render_smart_reply_bar(current_scenario):
    remocon = st.session_state.get("remocon", {})
    sx = remocon.get("adjust_smart_x", "0px")
    sy = remocon.get("adjust_smart_y", "0px")
    with st.container():
        st.markdown(
            f'<div id="smart-reply-area" data-x="{sx}" data-y="{sy}"></div>',
            unsafe_allow_html=True
        )
        st.divider()
        st.caption("💡 추천 표현 (클릭하면 전송됩니다)")
        phrases = list(current_scenario["key_phrases"].items())
        col_a, col_b = st.columns(2)
        for idx, (kor, eng) in enumerate(phrases):
            with col_a if idx % 2 == 0 else col_b:
                if st.button(f"{kor}\n({eng})", key=f"phrase_{idx}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": kor})
                    st.rerun()


# --- 6. 메인 앱 로직 ---
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

    current_scenario = SCENARIOS[st.session_state.selected_scenario]

    with st.container():
        st.markdown('<div id="back-btn-area"></div>', unsafe_allow_html=True)
        if st.button("✕", key="back_btn"):
            st.session_state.current_page = "HOME"
            st.rerun()

    st.markdown(f"<div id='learning-title-wrap'><h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div id='role-caption-wrap' style='font-size:0.875rem;color:gray;'>💡 역할: {html.escape(current_scenario['role'])}</div>",
        unsafe_allow_html=True
    )

    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown('<div id="start-prompt-wrap"></div>', unsafe_allow_html=True)
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
        st.markdown('<div id="chat-area-end"></div>', unsafe_allow_html=True)

    render_smart_reply_bar(current_scenario)

    # 추천 표현 바 위치: iframe 스크립트로 부모 문서의 블록에 transform 적용 (CSS 선택자 미동작 대응)
    _apply_smart_reply_position_script()

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
