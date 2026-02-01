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

# 리모컨 값 (inject_custom_css에서 설정, JS로 위치 적용)
REMOCON = {"back_top": "15px", "back_left_offset": "0px", "title_top": "50px", "title_left_offset": "0px",
           "role_top": "110px", "role_left_offset": "0px", "prompt_top": "160px", "prompt_left_offset": "0px",
           "smart_top": "230px", "smart_left_offset": "0px"}

# --- 2. CSS 설정 (위치 제어 리모컨 통합) ---
def inject_custom_css():
    # ============================================================
    # 🎛️ [사장님 전용 리모컨]
    # ============================================================
    
    # [1] 전체 화면 상단 여백
    main_top_padding = "0px"
    main_top_margin = "0px"

    # [2] 뒤로가기 버튼 (✕) — 화면 기준 고정 (JS로 직접 적용)
    back_top = "-50px"
    back_left_offset = "0px"   # 정중앙 기준 X 오프셋 (0px = 중앙)
    REMOCON["back_top"] = back_top
    REMOCON["back_left_offset"] = back_left_offset

    # [3] 제목 — 절대 위치, 0px 기준 정중앙 (JS로 직접 적용)
    title_top = "-100px"
    title_left_offset = "0px"
    REMOCON["title_top"] = title_top
    REMOCON["title_left_offset"] = title_left_offset

    # [4] 역할 설명 — 절대 위치
    role_top = "80px"
    role_left_offset = "100px"
    REMOCON["role_top"] = role_top
    REMOCON["role_left_offset"] = role_left_offset

    # [5] 안내 박스 — 절대 위치
    prompt_top = "200px"
    prompt_left_offset = "0px"
    REMOCON["prompt_top"] = prompt_top
    REMOCON["prompt_left_offset"] = prompt_left_offset

    # [6] 추천 표현 바 — 절대 위치 (JS로 직접 적용)
    smart_top = "800px"
    smart_left_offset = "0px"
    REMOCON["smart_top"] = smart_top
    REMOCON["smart_left_offset"] = smart_left_offset

    # 채팅 영역 시작 위치 (위 요소들과 겹치지 않도록)
    chat_area_top = "320px"

    # ============================================================

    st.markdown(
        f"""
        <style>
            /* 1. 기본 헤더 숨김 & 메인 컨테이너 */
            header[data-testid="stHeader"] {{ display: none !important; }}
            .main .block-container {{
                padding-top: {main_top_padding} !important;
                margin-top: {main_top_margin} !important;
                max-width: 700px;
                position: relative !important;  /* 절대 위치 기준점 */
            }}
            .stApp {{ background-color: #FFFFFF; font-family: 'Pretendard', sans-serif; }}

            /* [2] 뒤로가기 버튼: 화면 고정, 정중앙 (0px 기준) */
            div[data-testid="stVerticalBlock"]:has(div#back-btn-area):not(:has(> div[data-testid="stVerticalBlock"]:has(div#back-btn-area))) {{
                position: fixed !important;
                top: {back_top} !important;
                left: calc(50% + {back_left_offset}) !important;
                transform: translate(-50%, 0) !important;
                width: auto !important;
                height: auto !important;
                z-index: 999999 !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#back-btn-area):not(:has(> div[data-testid="stVerticalBlock"]:has(div#back-btn-area))) .stButton button {{
                width: 32px !important;
                height: 32px !important;
                border-radius: 50% !important;
                background-color: white !important;
                border: 1px solid #eee !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
                padding: 0 !important;
                line-height: 1 !important;
                font-size: 14px !important;
            }}

            /* [3] 제목: 절대 위치, 정중앙 (0px 기준) */
            div[data-testid="stVerticalBlock"]:has(#learning-title-wrap):not(:has(> div[data-testid="stVerticalBlock"]:has(#learning-title-wrap))) {{
                position: absolute !important;
                top: {title_top} !important;
                left: calc(50% + {title_left_offset}) !important;
                transform: translate(-50%, 0) !important;
                width: 100% !important;
                max-width: 700px !important;
                margin: 0 !important;
                z-index: 10 !important;
            }}
            #learning-title-wrap {{ margin: 0 !important; }}

            /* [4] 역할 설명: 절대 위치, 정중앙 (0px 기준) */
            div[data-testid="stVerticalBlock"]:has(#role-caption-wrap):not(:has(> div[data-testid="stVerticalBlock"]:has(#role-caption-wrap))) {{
                position: absolute !important;
                top: {role_top} !important;
                left: calc(50% + {role_left_offset}) !important;
                transform: translate(-50%, 0) !important;
                width: 100% !important;
                max-width: 700px !important;
                margin: 0 !important;
                z-index: 9 !important;
            }}
            #role-caption-wrap {{
                font-size: 0.875rem !important;
                color: gray !important;
                margin: 0 !important;
            }}

            /* [5] 안내 박스: 절대 위치, 정중앙 (0px 기준) */
            div[data-testid="stVerticalBlock"]:has(div#start-prompt-marker):not(:has(> div[data-testid="stVerticalBlock"]:has(div#start-prompt-marker))) {{
                position: absolute !important;
                top: {prompt_top} !important;
                left: calc(50% + {prompt_left_offset}) !important;
                transform: translate(-50%, 0) !important;
                width: 100% !important;
                max-width: 700px !important;
                margin: 0 !important;
                z-index: 8 !important;
            }}

            /* [6] 추천 표현 바: 절대 위치, 정중앙 (0px 기준) — CSS + JS 보조 */
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) {{
                position: absolute !important;
                top: {smart_top} !important;
                left: calc(50% + {smart_left_offset}) !important;
                transform: translate(-50%, 0) !important;
                width: 100% !important;
                max-width: 700px !important;
                margin: 0 !important;
                z-index: 1 !important;
            }}

            /* 채팅 영역: 위 요소들과 겹치지 않도록 상단 여백 (컨테이너 전체에만 적용) */
            div[data-testid="stVerticalBlock"]:has(div#chat-area-marker):has(> div[data-testid="stVerticalBlock"]:has(div#chat-area-marker)) {{
                padding-top: {chat_area_top} !important;
            }}

            /* 추천 표현 바 내부 컬럼/버튼 */
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) [data-testid="stHorizontalBlock"],
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) > div:has([data-testid="stColumn"]) {{
                width: 100% !important;
                display: flex !important;
                flex-wrap: nowrap !important;
                gap: 10px !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) [data-testid="stColumn"] {{
                flex: 1 1 50% !important;
                width: 50% !important;
                min-width: 0 !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: stretch !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) .stButton {{
                flex: 0 0 90px !important;
                min-width: 0 !important;
                width: 100% !important;
                min-height: 90px !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) .stButton button {{
                width: 100% !important;
                height: 90px !important;
                min-height: 90px !important;
                max-height: 90px !important;
                box-sizing: border-box !important;
                white-space: pre-wrap !important;
                word-break: keep-all !important;
                background-color: #FFFFFF !important;
                border: 1px solid #E5E5E5 !important;
                color: #4B5563 !important;
                border-radius: 12px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
                display: grid !important;
                place-items: center !important;
                text-align: center !important;
                padding: 10px !important;
                line-height: 1.4 !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) .stButton button > div {{
                text-align: center !important;
                width: 100% !important;
            }}
            div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]):not(:has(> div[data-testid="stVerticalBlock"]:has(div#smart-reply-area):has([data-testid="stColumn"]))) .stButton button:hover {{
                background-color: #F9FAFB !important;
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
            "깎아주세요.": "Please give me a discount.",
            "맛 좀 봐도 될까요?": "Can I taste this?",
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

    # JS로 뒤로가기/제목/역할/안내/추천표현 위치 직접 적용 (CSS 선택자 한계 우회)
    back_top = REMOCON.get("back_top", "15px")
    back_off = REMOCON.get("back_left_offset", "0px")
    title_top = REMOCON.get("title_top", "50px")
    title_off = REMOCON.get("title_left_offset", "0px")
    role_top = REMOCON.get("role_top", "110px")
    role_off = REMOCON.get("role_left_offset", "0px")
    prompt_top = REMOCON.get("prompt_top", "160px")
    prompt_off = REMOCON.get("prompt_left_offset", "0px")
    smart_top = REMOCON.get("smart_top", "230px")
    smart_off = REMOCON.get("smart_left_offset", "0px")
    st.components.v1.html(f"""
    <script>
    (function() {{
        const doc = window.parent?.document || document;
        const applyBack = (el, top, off) => {{
            if (!el) return;
            let block = el.closest('[data-testid="stVerticalBlock"]');
            if (block) block.style.cssText = 'position:fixed!important;top:'+top+'!important;left:calc(50% + '+off+')!important;transform:translate(-50%,0)!important;width:auto!important;height:auto!important;z-index:999999!important;';
        }};
        applyBack(doc.getElementById('back-btn-area'), '{back_top}', '{back_off}');
        const applyPos = (el, top, off, z) => {{
            if (!el) return;
            let block = el.closest('[data-testid="stVerticalBlock"]');
            if (block) block.style.cssText = 'position:absolute!important;top:'+top+'!important;left:calc(50% + '+off+')!important;transform:translate(-50%,0)!important;width:100%!important;max-width:700px!important;margin:0!important;z-index:'+z+'!important;';
        }};
        applyPos(doc.getElementById('learning-title-wrap'), '{title_top}', '{title_off}', 10);
        applyPos(doc.getElementById('role-caption-wrap'), '{role_top}', '{role_off}', 9);
        const promptEl = doc.getElementById('start-prompt-marker');
        if (promptEl) {{
            let block = promptEl.closest('[data-testid="stVerticalBlock"]');
            if (block) block = block.parentElement?.closest('[data-testid="stVerticalBlock"]') || block;
            if (block) block.style.cssText = 'position:absolute!important;top:{prompt_top}!important;left:calc(50% + {prompt_off})!important;transform:translate(-50%,0)!important;width:100%!important;max-width:700px!important;margin:0!important;z-index:8!important;';
        }}
        const el = doc.getElementById('smart-reply-area');
        if (el) {{
            let block = el.closest('[data-testid="stVerticalBlock"]');
            while (block) {{
                if (block.querySelector('[data-testid="stColumn"]')) {{
                    block.style.cssText = 'position:absolute!important;top:{smart_top}!important;left:calc(50% + {smart_off})!important;transform:translate(-50%,0)!important;width:100%!important;max-width:700px!important;margin:0!important;z-index:1!important;';
                    break;
                }}
                block = block.parentElement?.closest('[data-testid="stVerticalBlock"]');
            }}
        }}
    }})();
    </script>
    """, height=0)


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
    
    # 1. 뒤로가기 버튼
    with st.container():
        st.markdown('<div id="back-btn-area"></div>', unsafe_allow_html=True)
        if st.button("✕", key="back_btn"):
            st.session_state.current_page = "HOME"
            st.rerun()

    # 2. 제목 & 역할 설명
    st.markdown(f"<div id='learning-title-wrap'><h1 style='text-align: center;'>{current_scenario['icon']} {current_scenario['title']}</h1></div>", unsafe_allow_html=True)
    st.markdown(f"<div id='role-caption-wrap'>💡 역할: {html.escape(current_scenario['role'])}</div>", unsafe_allow_html=True)

    # 3. 채팅창 (상단 여백용 마커 — 리모컨 chat_area_top 으로 조절)
    chat_container = st.container()
    with chat_container:
        st.markdown('<div id="chat-area-marker"></div>', unsafe_allow_html=True)
        if not st.session_state.messages:
            # [중요] 안내 박스를 '컨테이너'에 담고 ID를 부여해서 CSS로 제어 가능하게 만듦
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
