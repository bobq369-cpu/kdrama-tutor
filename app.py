# -*- coding: utf-8 -*-
"""
글로벌 AI 한국어 튜터 — Eggbun 스타일 모바일 앱
공항 / 식당 / 전통시장 3가지 테마, 표현 익히기 + 실전 대화, TTS, Google Search Grounding
"""
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import streamlit as st

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


# ——— 상수 ———
KST = timezone(timedelta(hours=9))
CURRENT_DATE_STR = "2026년 1월 31일 토요일"  # 시스템 프롬프트용
GOOGLE_SEARCH_TOOLS = [{"google_search": {}}]


def get_current_kst_str() -> str:
    """현재 한국 시간 문자열 (프롬프트 주입용)."""
    now = datetime.now(KST)
    wd = ("월", "화", "수", "목", "금", "토", "일")[now.weekday()]
    h = now.hour
    ampm = "오전" if h < 12 else "오후"
    h12 = 12 if h in (0, 12) else (h if h < 12 else h - 12)
    return f"{now.year}년 {now.month}월 {now.day}일 {wd}요일 {ampm} {h12}시 {now.minute}분"


# ——— 데이터 구조 ———
@dataclass
class LineItem:
    kr: str
    roman: str
    en: str
    notes: str = ""
    vocab: Optional[List[Tuple[str, str]]] = None
    patterns: Optional[List[Tuple[str, str]]] = None

    def __post_init__(self):
        self.vocab = self.vocab if self.vocab is not None else []
        self.patterns = self.patterns if self.patterns is not None else []


# 공항
LINES_AIRPORT: List[LineItem] = [
    LineItem("관광으로 왔어요. 일주일 있을 예정이에요.", "Gwangwang-euro wasseoyo. Ilju-il isseul yejeong-ieyo.", "I came for tourism. I'm planning to stay a week.", "입국 심사 시 답변.", [("관광", "tourism"), ("일주일", "one week")], [("~으로 왔어요", "목적")]),
    LineItem("호텔에 묵을 거예요. 주소 적어 왔어요.", "Hotel-e mug-eul geoyeyo. Juso jeogeo wasseoyo.", "I'll stay at a hotel. I wrote down the address.", "숙소 질문 답변.", [("묵다", "to stay"), ("주소", "address")], []),
    LineItem("인천행 비행기 표 예약했는데요, 체크인 해주세요.", "Incheon-haeng bihaenggi pyo ye-yak-haet-neundeyo, chekeu-in hae juseyo.", "I have a reservation for a flight to Incheon. I'd like to check in.", "체크인 요청.", [("인천행", "to Incheon"), ("체크인", "check-in")], [("~ 해주세요", "요청")]),
]

# 식당
LINES_RESTAURANT: List[LineItem] = [
    LineItem("삼겹살 2인분이랑 된장찌개 하나 주세요.", "Samgyeopsal i-inbun-irang doenjang-jjigae hana juseyo.", "Two orders of samgyeopsal and one doenjang jjigae, please.", "기본 주문.", [("삼겹살", "pork belly"), ("인분", "serving")], [("~ 주세요", "요청")]),
    LineItem("상추랑 쌈장 더 주실 수 있나요?", "Sangchu-rang ssamjang deo jusil su innayo?", "Could I have more lettuce and ssamjang?", "추가 요청.", [("상추", "lettuce"), ("쌈장", "ssamjang")], [("~ 더 주실 수 있나요?", "추가")]),
    LineItem("잘 먹었습니다! 계산해 주세요.", "Jal meogeot-seumnida! Gyesan-hae juseyo.", "It was delicious! Check, please.", "계산 요청.", [("잘 먹었습니다", "thanks for the meal"), ("계산", "bill")], [("~해 주세요", "부탁")]),
]

# 전통시장
LINES_MARKET: List[LineItem] = [
    LineItem("이거 얼마예요?", "Igeo eolma-yeyo?", "How much is this?", "가격 문의.", [("이거", "this"), ("얼마예요", "how much")], []),
    LineItem("조금만 깎아주세요.", "Jogeum-man kkakka-juseyo.", "Could you give me a little discount?", "흥정.", [("조금만", "a little"), ("깎다", "to discount")], [("~ 주세요", "요청")]),
    LineItem("맛보기 해도 될까요?", "Matbogi haedo doelkkayo?", "May I try a sample?", "맛보기.", [("맛보기", "tasting"), ("해도 될까요", "may I")], [("~ 해도 될까요?", "허락")]),
]

SCENARIOS: Dict[str, Dict] = {
    "airport": {
        "name": "공항",
        "name_en": "Airport",
        "situation": "입국 심사 받기",
        "role": "입국 심사관",
        "persona": "인천공항에서 근무하는 친절하지만 절차에 충실한 입국 심사관. 질문은 짧고 명확하게.",
        "greeting": "여권 주세요. 입국 목적이 뭐예요?",
        "emoji": "✈️",
        "lines": LINES_AIRPORT,
    },
    "restaurant": {
        "name": "식당",
        "name_en": "Restaurant",
        "situation": "한식당에서 주문하기",
        "role": "식당 직원",
        "persona": "한식당에서 일하는 친절한 한국인 직원. 손님에게 반말 섞인 존댓말로 편하게 대한다.",
        "greeting": "어서 오세요~ 몇 분이에요? 주문 도와드릴까요?",
        "emoji": "🍽️",
        "lines": LINES_RESTAURANT,
    },
    "market": {
        "name": "전통시장",
        "name_en": "Traditional Market",
        "situation": "전통시장에서 물건 사기",
        "role": "시장 상인",
        "persona": "전통시장에서 장사하는 말주변이 좋은 한국인 상인. 흥정도 받아준다.",
        "greeting": "어서 오세요~ 오늘 뭐 찾으세요?",
        "emoji": "🥬",
        "lines": LINES_MARKET,
    },
}


# ——— 상태 & API ———
def init_state():
    st.session_state.setdefault("theme", "restaurant")
    st.session_state.setdefault("gemini_api_key", "")
    st.session_state.setdefault("roleplay_seed", None)
    st.session_state.setdefault("roleplay_history", [])
    st.session_state.setdefault("last_seed", None)
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("tts_cache", {})


def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        st.session_state.gemini_api_key = st.secrets["GEMINI_API_KEY"]
    return st.session_state.get("gemini_api_key", "").strip()


def _get_response_text(response) -> str:
    if not response:
        return ""
    if getattr(response, "text", None) and response.text:
        return response.text
    try:
        if getattr(response, "candidates", None) and response.candidates:
            parts = response.candidates[0].content.parts
            return "".join(p.text for p in parts if getattr(p, "text", None))
    except (IndexError, AttributeError, TypeError):
        pass
    return ""


def try_generate_content(prompt: str, use_grounding: bool = True) -> str:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API 키가 없습니다. st.secrets에 GEMINI_API_KEY를 설정해 주세요.")
    if not GEMINI_AVAILABLE:
        raise ValueError("google-generativeai 패키지를 설치해 주세요.")
    genai.configure(api_key=api_key)
    for model_name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"):
        try:
            model = genai.GenerativeModel(model_name)
            kwargs = {"tools": GOOGLE_SEARCH_TOOLS} if use_grounding else {}
            response = model.generate_content(prompt, **kwargs)
            text = _get_response_text(response)
            if text and text.strip():
                return text.strip()
        except Exception:
            continue
    raise Exception("모델 연결에 실패했습니다. API 키와 모델 이름을 확인해 주세요.")


def text_to_speech_korean(text: str, max_chars: int = 500) -> Optional[bytes]:
    if not text or not text.strip() or not GTTS_AVAILABLE:
        return None
    clean = re.sub(r"[*_#\[\]()`]", " ", text).strip()
    clean = re.sub(r"\s+", " ", clean)[:max_chars]
    if not clean:
        return None
    cache = st.session_state.get("tts_cache", {})
    key = hashlib.md5(clean.encode("utf-8")).hexdigest()
    if key in cache:
        return cache[key]
    try:
        tts = gTTS(text=clean, lang="ko", slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        data = buf.read()
        cache[key] = data
        st.session_state["tts_cache"] = cache
        return data
    except Exception:
        return None


# ——— UI: CSS (Eggbun 스타일) ———
def inject_css():
    st.markdown(
        "<link href='https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap' rel='stylesheet'>"
        "<style>"
        "*{font-family:'Noto Sans KR',sans-serif !important;letter-spacing:-0.02em;}"
        ".main{background:#F8F9FA !important;}"
        ".block-container{padding-top:1rem !important;padding-bottom:5rem !important;max-width:480px !important;margin:0 auto !important;}"
        "header[data-testid='stHeader']{background:transparent !important;}"
        "[data-testid='stToolbar']{display:none !important;}"
        "section[data-testid='stSidebar']{background:#FFF !important;box-shadow:2px 0 12px rgba(0,0,0,0.05) !important;}"
        ".app-header{display:flex;align-items:center;background:#FFF;padding:0.9rem 1.2rem;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:0.75rem;}"
        ".app-header .title{font-size:1.1rem;font-weight:700;color:#111;margin-left:0.5rem;line-height:1.5;}"
        ".theme-badge{display:inline-flex;align-items:center;background:#FFF;border-radius:999px;padding:0.5rem 1rem;box-shadow:0 2px 10px rgba(0,0,0,0.06);margin-bottom:0.6rem;font-size:0.9rem;color:#374151;}"
        ".main .block-container > div:not(:first-child){background:#FFF !important;border-radius:16px !important;padding:1.25rem !important;box-shadow:0 2px 14px rgba(0,0,0,0.06) !important;margin-bottom:1rem !important;}"
        "[data-testid='stChatMessage']{border-radius:20px !important;padding:0.7rem 1rem !important;box-shadow:0 1px 6px rgba(0,0,0,0.07) !important;}"
        "[data-testid='stChatMessage'] > div:last-child{border-radius:20px !important;}"
        "div[data-testid='stChatMessage']{background:#F0F0F0 !important;}"
        "div[data-testid='stChatMessage']:nth-of-type(even){background:#007AFF !important;color:#FFF !important;}"
        "div[data-testid='stChatMessage']:nth-of-type(even) p,div[data-testid='stChatMessage']:nth-of-type(even) .stMarkdown{color:#FFF !important;}"
        "[data-testid='stTabs']{border-bottom:none !important;}"
        "[data-testid='stTabs'] button{font-size:0.95rem !important;font-weight:600 !important;border-radius:12px !important;transition:all 0.2s !important;}"
        "[data-testid='stTabs'] button[aria-selected='true']{background:#111 !important;color:#FFF !important;border:none !important;}"
        "footer,[data-testid='stManageAppButton'],[data-testid='stDecoration']{display:none !important;}"
        "</style>",
        unsafe_allow_html=True,
    )


# ——— 사이드바: 테마 선택만 ———
def sidebar_theme():
    get_api_key()
    scenario_keys = list(SCENARIOS.keys())
    labels = [f"{SCENARIOS[k]['emoji']} {SCENARIOS[k]['name']} — {SCENARIOS[k]['situation']}" for k in scenario_keys]
    idx = scenario_keys.index(st.session_state.theme) if st.session_state.theme in scenario_keys else 0
    sel = st.sidebar.selectbox("테마 선택", range(len(scenario_keys)), format_func=lambda i: labels[i], index=idx, key="theme_select")
    new_theme = scenario_keys[sel]
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.session_state.roleplay_seed = None
        st.session_state.roleplay_history = []
        st.session_state.last_seed = None
        st.rerun()


# ——— 탭 1: 표현 익히기 ———
def tab_expressions():
    theme = st.session_state.theme
    scenario = SCENARIOS[theme]
    lines = scenario["lines"]
    st.markdown(f"**{scenario['situation']}** — 쓸 수 있는 표현을 골라 보세요.")
    idx = st.selectbox("표현", range(len(lines)), format_func=lambda i: lines[i].kr, key="expr_select")
    item = lines[idx]
    st.markdown(f"**{item.kr}**")
    st.caption(f"{item.roman}")
    st.write(item.en)
    if item.notes:
        st.caption(item.notes)
    if item.vocab:
        with st.expander("단어"):
            for w, m in item.vocab:
                st.write(f"**{w}** — {m}")
    if st.button("이 표현으로 실전 대화 시작", type="primary", key="start_rp"):
        st.session_state.roleplay_seed = {"kr": item.kr, "en": item.en}
        st.session_state.last_seed = None
        st.session_state.roleplay_history = []
        st.rerun()


# ——— 탭 2: 실전 대화 ———
def tab_roleplay():
    if not st.session_state.roleplay_seed:
        st.info("👋 **표현 익히기** 탭에서 표현을 고른 뒤 **실전 대화 시작** 버튼을 눌러 주세요.")
        return

    seed = st.session_state.roleplay_seed
    theme = st.session_state.theme
    scenario = SCENARIOS[theme]
    greeting = scenario["greeting"]
    persona = scenario["persona"]
    role = scenario["role"]
    situation = scenario["situation"]

    if st.session_state.last_seed != seed["kr"]:
        st.session_state.roleplay_history = [{"role": "model", "content": greeting}]
        st.session_state.last_seed = seed["kr"]

    st.success(f"🎯 **{situation}** — 연습 문장: **{seed['kr']}**")

    for msg in st.session_state.roleplay_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "model" and msg.get("content"):
                audio_bytes = text_to_speech_korean(msg["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

    if st.session_state.get("pending_prompt") is not None:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        st.session_state.roleplay_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("model"):
            ph = st.empty()
            ph.markdown("Thinking...")
            kst_str = get_current_kst_str()
            sys_block = f"""
당신은 {persona}
현재 시각: {kst_str}
현재 날짜는 2026년 1월 31일이며, 대한민국 대통령은 이재명입니다. 이 정보를 인지하고 답변하세요.
상대는 한국어를 배우는 학습자입니다. 연습 문장: "{seed['kr']}"
대화는 자연스럽게 하되, 연습 문장을 적절한 타이밍에만 언급하세요.
대화 내역:
"""
            recent = st.session_state.roleplay_history[-8:]
            for m in recent:
                who = "학습자" if m["role"] == "user" else role
                sys_block += f"{who}: {m['content']}\n"
            sys_block += "\n위 맥락에 맞춰 학습자의 마지막 말에 한국어로 한 번만 답하세요."
            try:
                reply = try_generate_content(sys_block, use_grounding=False)
            except Exception as e:
                reply = f"연결 오류: {e}. st.secrets에 GEMINI_API_KEY를 설정해 주세요."
            if not (reply and reply.strip()):
                reply = "잠시 답변이 어렵습니다. 다시 말해 주세요."
            ph.markdown(reply)
            st.session_state.roleplay_history.append({"role": "model", "content": reply})
        st.rerun()

    if prompt := st.chat_input("메시지 입력..."):
        st.session_state.pending_prompt = prompt
        st.rerun()


# ——— 메인 ———
def main():
    st.set_page_config(page_title="글로벌 AI 한국어 튜터", page_icon="🇰🇷", layout="centered")
    st.markdown("<style>footer,[data-testid='stManageAppButton'],[data-testid='stDecoration']{display:none !important;}</style>", unsafe_allow_html=True)
    init_state()
    inject_css()

    scenario = SCENARIOS[st.session_state.theme]
    emo = scenario["emoji"]
    st.markdown(
        f"<div class='app-header'><span style='font-size:1.5rem;'>{emo}</span><span class='title'>글로벌 AI 한국어 튜터 · {scenario['name']}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='theme-badge'><span>{emo}</span> <span>지금: {scenario['name']} — {scenario['situation']}</span></div>",
        unsafe_allow_html=True,
    )

    sidebar_theme()

    tab1, tab2 = st.tabs(["표현 익히기", "실전 대화 (Roleplay)"])
    with tab1:
        tab_expressions()
    with tab2:
        tab_roleplay()


if __name__ == "__main__":
    main()
