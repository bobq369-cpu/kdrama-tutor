import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


APP_TITLE = "K-드라마 튜터 (마당 식당 에디션)"
APP_SUBTITLE = "치앙마이 마당(Madang) 식당 — 실전 한국어 주문/응대 연습"

# 설정 버튼(⚙️) 위치(px). 값을 바꾸면 버튼이 이동합니다.
SETTINGS_BUTTON_TOP_PX = 43
SETTINGS_BUTTON_RIGHT_PX = 100  # 오른쪽에서의 거리. 크게 하면 버튼이 왼쪽으로 이동


@dataclass
class LineItem:
    show: str
    level: str
    kr: str
    roman: str
    en: str
    notes: str
    vocab: List[Tuple[str, str]]
    patterns: List[Tuple[str, str]]
    th: Optional[str] = None  # 태국어 뜻/발음 (예: อยากได้ จาจังมยอน)


# 마당 식당 전용 데이터 (roman: 로마자, en: 영어, th: 태국어 설명)
SAMPLE_LINES: List[LineItem] = [
    LineItem(
        show="(마당 식당) 주문하기",
        level="A1",
        kr="여기 짜장면 하나랑 탕수육 소(小)자 주세요.",
        roman="Yeogi Jjajangmyeon hana-rang Tangsuyuk so-ja juseyo.",
        en="I'd like one Jjajangmyeon and a small Tangsuyuk, please.",
        notes="식당에서 음식을 주문할 때 쓰는 가장 기본적인 표현.",
        vocab=[("짜장면", "Jjajangmyeon"), ("탕수육", "Tangsuyuk"), ("주세요", "Please give me")],
        patterns=[("~ 주세요", "무언가를 정중하게 요청할 때")],
        th=None,  # 예: อยากได้ จาจังมยอน หนึ่ง ที่ กับ ทังซูยุก ขนาดเล็ก
    ),
    LineItem(
        show="(마당 식당) 맵기 조절",
        level="A1",
        kr="짬뽕은 덜 맵게 해주실 수 있나요?",
        roman="Jjamppong-eun deol maep-ge hae-jusil su innayo?",
        en="Can you make the Jjamppong less spicy?",
        notes="매운 음식을 잘 못 먹을 때 요청하는 표현.",
        vocab=[("짬뽕", "Jjamppong"), ("덜 맵게", "Less spicy")],
        patterns=[("~ 해주실 수 있나요?", "가능한지 물어볼 때")],
        th=None,
    ),
    LineItem(
        show="(마당 식당) 추천 메뉴",
        level="A2",
        kr="사장님, 여기 태국 분들이 제일 좋아하는 메뉴가 뭐예요?",
        roman="Sajang-nim, yeogi Taeguk bun-deuri jeil joa-haneun menu-ga mwo-yeyo?",
        en="Boss, what is the most popular menu item for Thai people here?",
        notes="현지인에게 인기 있는 메뉴를 물어볼 때.",
        vocab=[("사장님", "Boss/Owner"), ("제일", "Most/Best"), ("좋아하는", "Favorite")],
        patterns=[("~가 뭐예요?", "정보를 물어볼 때")],
        th=None,
    ),
    LineItem(
        show="(마당 식당) 계산하기",
        level="A1",
        kr="잘 먹었습니다! 계산해 주세요.",
        roman="Jal meogeot-seumnida! Gyesan-hae juseyo.",
        en="It was delicious! Check, please.",
        notes="식사를 마치고 나갈 때 쓰는 인사와 요청.",
        vocab=[("잘 먹었습니다", "Thank you for the meal"), ("계산", "Bill/Check")],
        patterns=[("~해 주세요", "행동을 부탁할 때")],
        th=None,
    ),
]


LEVELS = ["A1", "A2", "B1", "B2", "C1"]


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("profile", {"name": "학습자", "level": "A2", "goal": "K-드라마로 자연스러운 회화 익히기"})
    ss.setdefault("gemini_api_key", "")
    ss.setdefault("admin_mode", False)
    ss.setdefault("history", [])
    ss.setdefault("saved_lines", [])
    ss.setdefault("deck", [])
    ss.setdefault("deck_stats", {"correct": 0, "wrong": 0})


def add_history(event_type: str, payload: Dict) -> None:
    st.session_state.history.append({"ts": now_iso(), "type": event_type, "payload": payload})


# [핵심] 여러 모델을 순서대로 시도해보는 함수
def try_generate_content(prompt: str) -> str:
    # Gemini API 공식 문서 기준 현재 지원 모델 (gemini-1.5 시리즈는 deprecated)
    # https://ai.google.dev/gemini-api/docs/models
    candidates = [
        "gemini-2.5-flash",      # Stable, 가성비 좋음
        "gemini-2.5-pro",        # Stable, 고성능
        "gemini-2.0-flash",      # Stable
        "gemini-3-flash-preview", # Preview
        "gemini-3-pro-preview",  # Preview
    ]
    
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key:
        raise ValueError("API 키가 없습니다.")
        
    if not GEMINI_AVAILABLE:
        raise ValueError("google-generativeai 패키지가 설치되지 않았습니다.")
        
    genai.configure(api_key=api_key)
    
    errors = []
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            else:
                errors.append(f"{model_name}: 응답이 비어있습니다.")
                continue
        except Exception as e:
            error_msg = str(e)
            # 404 에러는 모델이 존재하지 않음을 의미
            if "404" in error_msg or "not found" in error_msg.lower():
                errors.append(f"{model_name}: 모델을 찾을 수 없습니다.")
            else:
                errors.append(f"{model_name}: {error_msg}")
            continue
            
    raise Exception(f"모든 모델 연결 실패. 다음 에러들을 확인하세요: {'; '.join(errors)}")


def _logo_transparent_png_bytes(logo_path: str):
    """로고의 체크무늬/밝은 배경을 제거해 완전히 투명한 PNG 바이트 반환."""
    try:
        from PIL import Image
        import io
        img = Image.open(logo_path).convert("RGBA")
        data = list(img.getdata())
        new_data = []
        for item in data:
            r, g, b, a = item
            # 밝은 픽셀(체크무늬·흰색·연한 회색) 완전 투명 처리
            if r > 215 and g > 215 and b > 215:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


# GitHub 등 원격 로고 URL (로컬 assets/logo.png 대신 사용 가능)
HEADER_LOGO_URL = "https://raw.githubusercontent.com/bobq369-cpu/kdrama-tutor/main/assets/madang_logo.png"


def render_header() -> None:
    """슬림 헤더: 로고 + 텍스트 한 줄 Flexbox, 파스텔 톤. (divider는 호출부에서 처리)"""
    st.markdown(
        """
        <div class="header-container">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">🍲</span>
            <div class="header-text">마당 Madang · 치앙마이 한식당 · 한국어 주문 연습</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_profile() -> None:
    # [항상 실행] API 키 연결 로직은 백그라운드에서 항상 적용 (AI 기능 유지)
    if "GEMINI_API_KEY" in st.secrets:
        st.session_state.gemini_api_key = st.secrets["GEMINI_API_KEY"]
        if GEMINI_AVAILABLE:
            genai.configure(api_key=st.session_state.gemini_api_key)

    # 관리자 모드는 상단 헤더 우측 ⚙️ 설정(팝오버)에서만 제어. 여기서는 표시만.
    if not st.session_state.get("admin_mode", False):
        return  # 관리자 모드 꺼져 있으면 사이드바 관리 UI 숨김

    # --- 아래는 admin_mode 일 때만 표시 (API 키, 학습 설정, 데이터) ---
    st.sidebar.divider()
    st.sidebar.header("Gemini API Key")

    if "GEMINI_API_KEY" in st.secrets:
        st.sidebar.success("✅ 주인님, 자동으로 로그인했습니다! (Secrets)")
    else:
        api_key = st.sidebar.text_input(
            "API 키를 입력하세요",
            value=st.session_state.get("gemini_api_key", ""),
            type="password",
            help="Gemini API 키를 입력하면 AI 기능을 사용할 수 있습니다.",
            key="gemini_api_key_input"
        )
        if api_key != st.session_state.get("gemini_api_key", ""):
            st.session_state.gemini_api_key = api_key.strip()
            if api_key.strip():
                try:
                    if GEMINI_AVAILABLE:
                        genai.configure(api_key=api_key.strip())
                        st.sidebar.success("API 키가 설정되었습니다.")
                        add_history("api_key_set", {"status": "success"})
                    else:
                        st.sidebar.warning("google-generativeai 패키지가 설치되지 않았습니다.")
                except Exception as e:
                    st.sidebar.error(f"API 키 설정 오류: {str(e)}")
            else:
                st.sidebar.info("API 키가 제거되었습니다.")

    if st.session_state.get("gemini_api_key", ""):
        st.sidebar.success("✅ AI 기능 활성화됨")
    else:
        st.sidebar.info("ℹ 기본 모드 (규칙 기반)")

    st.sidebar.divider()
    st.sidebar.header("학습 설정")
    name = st.sidebar.text_input("이름", value=st.session_state.profile["name"])
    level = st.sidebar.selectbox("레벨", options=LEVELS, index=LEVELS.index(st.session_state.profile["level"]))
    goal = st.sidebar.text_area("목표", value=st.session_state.profile["goal"], height=80)
    if st.sidebar.button("설정 저장"):
        st.session_state.profile.update({"name": normalize_ws(name) or "학습자", "level": level, "goal": normalize_ws(goal)})
        add_history("profile_saved", dict(st.session_state.profile))
        st.sidebar.success("저장했어요.")

    st.sidebar.divider()
    st.sidebar.header("데이터")
    if st.sidebar.button("학습 기록 초기화"):
        st.session_state.history = []
        st.session_state.saved_lines = []
        st.session_state.deck = []
        st.session_state.deck_stats = {"correct": 0, "wrong": 0}
        st.sidebar.warning("기록/저장/덱을 초기화했어요.")


def line_picker(lines: List[LineItem], preferred_level: str) -> List[LineItem]:
    idx = {lvl: i for i, lvl in enumerate(LEVELS)}
    p = idx.get(preferred_level, 1)
    return [x for x in lines if idx.get(x.level, 1) <= p]


def card_line(item: LineItem) -> None:
    st.subheader(f"{item.show} · {item.level}")
    st.markdown(f"**대사(KR)**: {item.kr}")
    st.markdown(f"**로마자**: {item.roman}")
    st.markdown(f"**의미(EN)**: {item.en}")
    if item.notes:
        st.info(item.notes)

    with st.expander("어휘(핵심 단어)"):
        for w, m in item.vocab:
            st.write(f"- **{w}**: {m}")

    with st.expander("패턴/문법 포인트"):
        for p, e in item.patterns:
            st.write(f"- **{p}**: {e}")

    item_hash = hashlib.md5(f"{item.show}_{item.kr}".encode()).hexdigest()[:8]
    
    cols = st.columns(3)
    if cols[0].button("이 대사 저장", use_container_width=True, key=f"save_line_{item_hash}"):
        st.session_state.saved_lines.append(
            {"saved_at": now_iso(), "show": item.show, "level": item.level, "kr": item.kr, "roman": item.roman, "en": item.en}
        )
        add_history("line_saved", {"kr": item.kr, "show": item.show})
        st.success("저장했어요.")

    if cols[1].button("퀴즈에 추가", use_container_width=True, key=f"add_quiz_{item_hash}"):
        make_quiz_from_line(item)
        add_history("deck_add", {"kr": item.kr})
        st.success("덱에 추가했어요.")

    if cols[2].button("롤플레이 시작", use_container_width=True, key=f"start_roleplay_{item_hash}"):
        add_history("roleplay_start", {"kr": item.kr})
        st.session_state["roleplay_seed"] = {"kr": item.kr, "en": item.en}
        st.info("아래 ‘롤플레이’ 탭에서 진행해요.")


def make_quiz_from_line(item: LineItem) -> None:
    if not item.vocab:
        return
    key_word, _meaning = item.vocab[0]
    blanked = item.kr.replace(key_word, "____", 1)
    st.session_state.deck.append(
        {"type": "blank", "prompt": blanked, "answer": key_word, "source": item.kr, "show": item.show, "level": item.level}
    )
    st.session_state.deck.append(
        {"type": "meaning", "prompt": f"다음 대사의 의미를 한국어로 자연스럽게 설명해보세요:\n\n{item.kr}", "answer": item.en, "source": item.kr}
    )


def tab_menu_learn() -> None:
    """심플 메뉴판: SAMPLE_LINES만 보여주고, 선택한 표현으로 주문 연습 연결."""
    st.header("메뉴 표현 익히기")
    st.caption("마당 식당에서 쓸 수 있는 표현을 골라 보세요.")

    idx = st.selectbox(
        "표현 고르기",
        options=list(range(len(SAMPLE_LINES))),
        format_func=lambda i: SAMPLE_LINES[i].kr,
    )
    item = SAMPLE_LINES[idx]

    st.markdown(f"**{item.kr}**")
    st.caption(f"로마자: {item.roman}")
    st.write(f"의미: {item.en}" + (f"  \n(TH) {item.th}" if getattr(item, "th", None) else ""))
    if item.notes:
        st.info(item.notes)
    with st.expander("핵심 단어"):
        for w, m in item.vocab:
            st.write(f"- **{w}**: {m}")
    with st.expander("패턴"):
        for p, e in item.patterns:
            st.write(f"- **{p}**: {e}")

    if st.button("AI 점원과 주문 연습하기", type="primary"):
        st.session_state.roleplay_seed = {"kr": item.kr, "en": item.en}
        add_history("roleplay_start", {"kr": item.kr})
        st.success("→ 오른쪽 탭 **AI 점원과 주문 연습**에서 연습해 보세요.")


def generate_support_card(kr: str, profile_level: str) -> LineItem:
    api_key = st.session_state.get("gemini_api_key", "").strip()
    
    if api_key and GEMINI_AVAILABLE:
        try:
            # [수정됨] 자동 모델 찾기 함수 사용
            prompt = f"""다음 한국어 드라마 대사를 분석해주세요. JSON 형식으로 답변해주세요.
            대사: {kr}
            학습자 레벨: {profile_level}
            다음 형식으로 답변해주세요:
            {{
                "roman": "로마자 발음",
                "en": "영어 번역",
                "notes": "대사의 맥락/의미 설명",
                "vocab": [["단어1", "의미1"], ["단어2", "의미2"]],
                "patterns": [["문법 패턴1", "설명1"], ["문법 패턴2", "설명2"]]
            }}"""
            
            result_text = try_generate_content(prompt)
            
            import json
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            try:
                data = json.loads(result_text)
                return LineItem(
                    show="(내 대사 - AI 분석)",
                    level=profile_level,
                    kr=kr,
                    roman=data.get("roman", simple_romanize_hint(kr)),
                    en=data.get("en", "의미를 분석 중입니다..."),
                    notes=data.get("notes", "대사 분석 결과입니다."),
                    vocab=[tuple(v) for v in data.get("vocab", [])][:6],
                    patterns=[tuple(p) for p in data.get("patterns", [])][:6]
                )
            except json.JSONDecodeError:
                pass
        
        except Exception as e:
            st.warning(f"AI 분석 오류: {str(e)}")
    
    return LineItem(
        show="(내 대사)", level=profile_level, kr=kr, 
        roman=simple_romanize_hint(kr), 
        en="Gemini API 키가 필요하거나 AI 연결에 실패했습니다.", 
        notes="기본 분석 모드입니다.", 
        vocab=extract_vocab_hints(kr), 
        patterns=extract_pattern_hints(kr)
    )


def simple_romanize_hint(kr: str) -> str:
    return "발음 힌트: " + kr


COMMON_VOCAB: List[Tuple[str, str]] = [
    ("괜찮아", "OK"), ("진짜", "really"), ("지금", "now"), ("왜", "why")
]


def extract_vocab_hints(kr: str) -> List[Tuple[str, str]]:
    hits = []
    for w, m in COMMON_VOCAB:
        if w in kr:
            hits.append((w, m))
    return hits[:6]


PATTERN_RULES: List[Tuple[str, str]] = [
    ("겠", "추측/의지"), ("-게요", "약속"), ("-죠", "확인"), ("-잖아", "강조")
]


def extract_pattern_hints(kr: str) -> List[Tuple[str, str]]:
    found = []
    for key, exp in PATTERN_RULES:
        if key in kr:
            found.append((key, exp))
    return found[:6]


def tab_roleplay() -> None:
    """Chat Pattern: 헤더 → 과거 대화 전부 출력 → (대기 중 입력이면 처리) → st.chat_input 맨 마지막 → 입력창 하단 고정."""
    if "roleplay_seed" not in st.session_state:
        st.info("👋 먼저 **메뉴 표현 익히기** 탭에서 표현을 골라 **AI 점원과 주문 연습하기** 버튼을 눌러 주세요.")
        return

    seed = st.session_state["roleplay_seed"]
    st.session_state.setdefault("pending_prompt", None)

    if "last_seed" not in st.session_state or st.session_state.last_seed != seed["kr"]:
        st.session_state.roleplay_history = [
            {"role": "model", "content": "어서오세요! 치앙마이 마당(Madang) 식당입니다. 주문하시겠어요? 😊"}
        ]
        st.session_state.last_seed = seed["kr"]

    # ─── 1. 헤더/미션 출력 ───────────────────────────────────────────────
    st.header("AI 점원과 주문 연습")
    st.success(f"🎯 오늘의 미션: **{seed['kr']}**")

    # ─── 2. st.chat_input 호출 전에 과거 대화(history) 전부 출력 ─────────
    for msg in st.session_state.roleplay_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ─── 3. 이전 제출분(pending) 처리: 사용자 말 → AI 말풍선(Thinking... → 응답) → history 추가 ───
    if st.session_state.get("pending_prompt") is not None:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

        st.session_state.roleplay_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("model"):
            placeholder = st.empty()
            placeholder.markdown("Thinking...")
            try:
                full_prompt = f"""
                당신은 태국 치앙마이의 한식당 '마당(Madang)'의 친절한 직원입니다. 
                상대방은 한국어를 배우는 손님입니다.
                현재 연습 상황: "{seed['kr']}"
                직원의 태도: 친절함, 정중함, 격려해주는 태도.
                대화 내역:
                {[m['content'] for m in st.session_state.roleplay_history]}
                위 맥락에 맞춰 손님(user)의 말에 자연스럽게 한국어로 답변하세요.
                """
                response_text = try_generate_content(full_prompt)
                placeholder.markdown(response_text)
                st.session_state.roleplay_history.append({"role": "model", "content": response_text})
            except Exception as e:
                placeholder.error(f"오류가 발생했습니다: {e}")

        st.rerun()

    # ─── 4. 입력창은 항상 맨 마지막에 호출 → 화면 하단 고정, Thinking 중에도 움직이지 않음 ───
    if prompt := st.chat_input("메시지 입력..."):
        st.session_state.pending_prompt = prompt
        st.rerun()


def _inject_app_styles(is_admin: bool) -> None:
    """파스텔 톤 + 슬림 헤더: 툴바 공간 제거(display:none), 헤더 Flexbox, 탭 파스텔 Coral/Peach."""
    toolbar_rule = (
        '[data-testid="stToolbar"] { display: block !important; }'
        if is_admin
        else '[data-testid="stToolbar"] { display: none !important; }'
    )
    st.markdown(
        f"""
        <style>
        /* 1. 본문 상단 여백 강제 삭제 (가장 중요) */
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }}
        .main .block-container {{
            max-width: 900px;
        }}

        /* 2. 헤더 바 배경 투명화 */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            z-index: 1;
        }}

        /* 3. 우측 상단 툴바: 관리자일 때만 표시, 아니면 공간까지 제거 */
        {toolbar_rule}

        /* ─── 4. 앱 배경: 파스텔 톤 ─── */
        .main {{
            background-color: #FFF8E1 !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: #FFF3E0 !important;
        }}

        /* 본문 컨테이너: 설정 버튼 absolute 위치의 기준 */
        .main .block-container {{
            position: relative !important;
        }}

        /* ─── 5. 슬림 헤더 (Flexbox): 로고 + 텍스트 한 줄, 파스텔 오렌지/베이지 ─── */
        .header-container {{
            display: flex;
            align-items: center;
            background-color: #FFF3E0 !important;
            padding: 0.6rem 1.2rem !important;
            border-radius: 12px !important;
            margin-bottom: 0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }}
        .header-logo {{
            height: 2.2rem !important;
            width: auto !important;
            object-fit: contain;
        }}
        .header-text {{
            font-size: 1.1rem !important;
            font-weight: bold !important;
            color: #5D4037 !important;
            margin-left: 1rem !important;
        }}

        /* ─── 6. 카드 스타일 (헤더 행 제외) ─── */
        .main .block-container > div:not(:first-child) {{
            background-color: white !important;
            border-radius: 15px !important;
            padding: 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            margin-bottom: 1rem !important;
        }}

        /* ─── 7. 탭: 파스텔 Coral/Peach, 선택 시 부드러운 강조 ─── */
        [data-testid="stTabs"] {{
            padding: 0.5rem 0 1rem 0 !important;
            border-bottom: 2px solid #FFCCBC !important;
        }}
        [data-testid="stTabs"] button,
        [data-testid="stTabs"] [role="tab"],
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.2rem !important;
            border-radius: 10px !important;
            color: #5D4037 !important;
        }}
        [data-testid="stTabs"] button:hover,
        [data-testid="stTabs"] [role="tab"]:hover {{
            color: #3E2723 !important;
            background-color: #FFE0B2 !important;
        }}
        [data-testid="stTabs"] button[aria-selected="true"],
        [data-testid="stTabs"] [role="tab"][aria-selected="true"],
        [data-testid="stTabs"] [aria-selected="true"],
        div[data-baseweb="tab-list"] button[aria-selected="true"] {{
            font-weight: 700 !important;
            background-color: #FFF3E0 !important;
            color: #E65100 !important;
            border-radius: 10px !important;
            border-bottom: none !important;
        }}

        /* ─── 8. 하단 풋터 및 Manage app 버튼 완전 숨김 ─── */
        footer {{
            display: none !important;
            visibility: hidden !important;
        }}
        [data-testid="stManageAppButton"] {{
            display: none !important;
            visibility: hidden !important;
        }}
        /* 하단 데코레이션 영역(Manage app 포함) 숨김 */
        [data-testid="stDecoration"] {{
            display: none !important;
        }}
        /* 하단 Manage app 링크(풋터 내부) */
        footer a[href*="manage"] {{
            display: none !important;
        }}

        /* ─── 9. 설정 버튼: 가장 작은 크기의 깔끔한 흰색 버튼, 우측 상단 고정 ─── */
        div[data-testid="stPopover"] {{
            position: fixed !important;
            top: {SETTINGS_BUTTON_TOP_PX}px !important;
            right: {SETTINGS_BUTTON_RIGHT_PX}px !important;
            z-index: 999999 !important;
            width: auto !important;
        }}
        div[data-testid="stPopover"] > button {{
            background-color: white !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 8px !important;
            width: 10px !important;
            height: 10px !important;
            min-width: 10px !important;
            min-height: 10px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
            color: #5D4037 !important;
        }}
        div[data-testid="stPopover"] > button:hover {{
            background-color: #f5f5f5 !important;
            border-color: #d0d0d0 !important;
            color: #E65100 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_hide_footer_early() -> None:
    """앱 로드 시 가장 먼저 풋터/Manage app 숨김 CSS 주입 (우선 적용)."""
    st.markdown(
        """
        <style>
        footer { display: none !important; visibility: hidden !important; }
        [data-testid="stManageAppButton"] { display: none !important; visibility: hidden !important; }
        [data-testid="stDecoration"] { display: none !important; }
        [data-testid="stBottom"] { display: none !important; }
        .stDeployButton { display: none !important; }
        div[data-testid="stAppViewContainer"] > footer { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🍲", layout="wide")
    init_state()
    _inject_hide_footer_early()
    # 상단 헤더 (HTML) → 바로 아래 설정 버튼(popover), CSS로 헤더 박스 위에 겹쳐 표시
    render_header()
    with st.popover("⚙️", help="설정"):
        st.toggle(
            "관리자 모드 (Admin Mode)",
            value=st.session_state.get("admin_mode", False),
            key="admin_mode",
        )
        st.link_button("Manage App (편집하기)", "https://share.streamlit.io")
    st.divider()

    sidebar_profile()

    is_admin = st.session_state.get("admin_mode", False)
    _inject_app_styles(is_admin)

    tabs = st.tabs(["메뉴 표현 익히기", "AI 점원과 주문 연습"])
    with tabs[0]:
        tab_menu_learn()
    with tabs[1]:
        tab_roleplay()


if __name__ == "__main__":
    main()