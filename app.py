import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# 한국 시간(KST) = UTC + 9
KST = timezone(timedelta(hours=9))
WEEKDAYS_KO = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")


def get_current_kst_str() -> str:
    """현재 한국 시간(KST)을 '2026년 1월 30일 금요일 오후 4시 35분' 형식으로 반환."""
    now = datetime.now(KST)
    wd = WEEKDAYS_KO[now.weekday()]
    h = now.hour
    if h == 0:
        ampm, h12 = "오전", 12
    elif h < 12:
        ampm, h12 = "오전", h
    elif h == 12:
        ampm, h12 = "오후", 12
    else:
        ampm, h12 = "오후", h - 12
    return f"{now.year}년 {now.month}월 {now.day}일 {wd} {ampm} {h12}시 {now.minute}분"

import streamlit as st

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


APP_TITLE = "K-드라마 튜터 (마당 식당 에디션)"
APP_SUBTITLE = "치앙마이 마당(Madang) 식당 — 실전 한국어 주문/응대 연습"

# 설정 버튼(⚙️) 위치(px). 값을 바꾸면 버튼이 이동합니다.
SETTINGS_BUTTON_TOP_PX = 42
SETTINGS_BUTTON_RIGHT_PX = 100  # 오른쪽에서의 거리. 크게 하면 버튼이 왼쪽으로 이동

# 설정(관리자 모드) 진입용 4자리 비밀번호. 원하는 값으로 변경하세요.
ADMIN_PIN = "1920"


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
SAMPLE_LINES_RESTAURANT: List[LineItem] = [
    LineItem(
        show="(마당 식당) 주문하기",
        level="A1",
        kr="여기 짜장면 하나랑 탕수육 소(小)자 주세요.",
        roman="Yeogi Jjajangmyeon hana-rang Tangsuyuk so-ja juseyo.",
        en="I'd like one Jjajangmyeon and a small Tangsuyuk, please.",
        notes="식당에서 음식을 주문할 때 쓰는 가장 기본적인 표현.",
        vocab=[("짜장면", "Jjajangmyeon"), ("탕수육", "Tangsuyuk"), ("주세요", "Please give me")],
        patterns=[("~ 주세요", "무언가를 정중하게 요청할 때")],
        th=None,
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

# 공항 테마: 체크인·보안검색·기내 등
SAMPLE_LINES_AIRPORT: List[LineItem] = [
    LineItem(
        show="(공항) 체크인",
        level="A1",
        kr="인천행 비행기 표 하나 예약했는데요, 체크인 해주세요.",
        roman="Incheon-haeng bihaenggi pyo hana ye-yak-haet-neundeyo, chekeu-in hae juseyo.",
        en="I have a reservation for a flight to Incheon. I'd like to check in, please.",
        notes="공항 카운터에서 체크인 요청할 때.",
        vocab=[("인천행", "To Incheon"), ("예약했는데요", "I made a reservation"), ("체크인", "Check-in")],
        patterns=[("~ 해주세요", "행동을 정중히 요청할 때")],
        th=None,
    ),
    LineItem(
        show="(공항) 수하물",
        level="A1",
        kr="이 가방 기내에 가지고 타도 될까요?",
        roman="I gabang ginae-e gajigo tado doelkkayo?",
        en="Can I take this bag on board?",
        notes="기내 반입 가능 여부를 물을 때.",
        vocab=[("가방", "Bag"), ("기내", "Cabin"), ("가지고 타다", "Take on board")],
        patterns=[("~ 될까요?", "가능 여부를 물을 때")],
        th=None,
    ),
    LineItem(
        show="(공항) 출구/환승",
        level="A2",
        kr="환승이에요. 다음 비행기 탑승 게이트가 어디예요?",
        roman="Hwanseung-ieyo. Da-eum bihaenggi tapseung geiteu-ga eodi-yeyo?",
        en="I'm in transit. Where is the gate for my next flight?",
        notes="환승 시 다음 게이트 위치를 물을 때.",
        vocab=[("환승", "Transit"), ("탑승 게이트", "Boarding gate"), ("어디예요", "Where is")],
        patterns=[("~ 어디예요?", "위치를 물을 때")],
        th=None,
    ),
    LineItem(
        show="(공항) 기내 서비스",
        level="A1",
        kr="물 한 잔 주실 수 있을까요?",
        roman="Mul han jan jusil su isseulkkayo?",
        en="Could I have a glass of water, please?",
        notes="기내에서 음료 요청할 때.",
        vocab=[("물", "Water"), ("한 잔", "A glass"), ("주실 수 있을까요", "Could you give me")],
        patterns=[("~ 주실 수 있을까요?", "정중히 요청할 때")],
        th=None,
    ),
]

# 전통시장 테마: 흥정·가격·맛보기 등
SAMPLE_LINES_MARKET: List[LineItem] = [
    LineItem(
        show="(전통시장) 가격 문의",
        level="A1",
        kr="이거 얼마예요?",
        roman="Igeo eolma-yeyo?",
        en="How much is this?",
        notes="시장에서 가격을 물을 때 가장 많이 쓰는 표현.",
        vocab=[("이거", "This"), ("얼마예요", "How much is it")],
        patterns=[("이거/그거 얼마예요?", "가격 물어볼 때")],
        th=None,
    ),
    LineItem(
        show="(전통시장) 흥정",
        level="A2",
        kr="조금만 깎아주세요.",
        roman="Jogeum-man kkakka-juseyo.",
        en="Could you give me a little discount?",
        notes="가격을 조금 낮춰 달라고 할 때.",
        vocab=[("조금만", "Just a little"), ("깎다", "To reduce/discount")],
        patterns=[("~ 만 깎아주세요", "할인 요청할 때")],
        th=None,
    ),
    LineItem(
        show="(전통시장) 맛보기",
        level="A1",
        kr="맛보기 해도 될까요?",
        roman="Matbogi haedo doelkkayo?",
        en="May I try a sample?",
        notes="먹어보기/맛보기 허락을 구할 때.",
        vocab=[("맛보기", "Tasting/Sample"), ("해도 될까요", "Is it okay to")],
        patterns=[("~ 해도 될까요?", "허락을 구할 때")],
        th=None,
    ),
    LineItem(
        show="(전통시장) 양/개수",
        level="A1",
        kr="이거 한 근이에요? 저한테 한 근만 주세요.",
        roman="Igeo han geun-ieyo? Jeo-hante han geun-man juseyo.",
        en="Is this one geun (about 600g)? Please give me just one geun.",
        notes="전통시장에서 무게 단위(근)로 살 때.",
        vocab=[("한 근", "One geun (~600g)"), ("~만 주세요", "Just give me ~")],
        patterns=[("~ 만 주세요", "양을 지정할 때")],
        th=None,
    ),
]

# 테마별 메타: 페르소나, 인사말, 샘플 문장 리스트
THEMES: Dict[str, Dict] = {
    "restaurant": {
        "name": "식당",
        "name_en": "Restaurant",
        "persona": "태국 치앙마이의 한식당 '마당(Madang)'에서 일하는 눈치 빠르고 친절한 한국인 점원",
        "greeting": "어서오세요! 치앙마이 마당(Madang) 식당입니다. 주문하시겠어요? 😊",
        "lines": SAMPLE_LINES_RESTAURANT,
    },
    "airport": {
        "name": "공항",
        "name_en": "Airport",
        "persona": "인천공항에서 근무하는 친절하고 말이 빠른 한국인 지상직 직원",
        "greeting": "안녕하세요. 인천공항입니다. 체크인하시나요, 아니면 다른 문의가 있으신가요? ✈️",
        "lines": SAMPLE_LINES_AIRPORT,
    },
    "market": {
        "name": "전통시장",
        "name_en": "Market",
        "persona": "전통시장에서 장사를 하는 말주변이 좋고 유머러스한 한국인 상인",
        "greeting": "어서 오세요~ 오늘 뭐 찾으세요? 맛있는 거 많아요! 🥬",
        "lines": SAMPLE_LINES_MARKET,
    },
}

# 하위 호환: 기존 변수명 유지
SAMPLE_LINES: List[LineItem] = SAMPLE_LINES_RESTAURANT


LEVELS = ["A1", "A2", "B1", "B2", "C1"]

# 오늘의 한 문장: 날짜(일) 기준으로 매일 다른 표현 (실생활 유용 표현)
DAILY_SENTENCES: List[Dict] = [
    {"kr": "이거 얼마예요?", "roman": "Igeo eolma-yeyo?", "en": "How much is this?"},
    {"kr": "조금만 깎아주세요.", "roman": "Jogeum-man kkakka-juseyo.", "en": "Could you give me a little discount?"},
    {"kr": "여기 하나 주세요.", "roman": "Yeogi hana juseyo.", "en": "One of these, please."},
    {"kr": "봉지에 담아 주세요.", "roman": "Bongji-e dama juseyo.", "en": "Put it in a bag, please."},
    {"kr": "맛있게 드세요.", "roman": "Masitge deuseyo.", "en": "Enjoy your meal."},
    {"kr": "계산해 주세요.", "roman": "Gyesan-hae juseyo.", "en": "Check, please. / I'd like to pay."},
    {"kr": "카드 돼요?", "roman": "Kadeu dwaeyo?", "en": "Do you take cards?"},
    {"kr": "영수증 주세요.", "roman": "Yeongsujeung juseyo.", "en": "Receipt, please."},
    {"kr": "화장실 어디예요?", "roman": "Hwajangsil eodi-yeyo?", "en": "Where is the restroom?"},
    {"kr": "여기 앉아도 돼요?", "roman": "Yeogi anja-do dwaeyo?", "en": "May I sit here?"},
    {"kr": "메뉴판 주세요.", "roman": "Menyupan juseyo.", "en": "Menu, please."},
    {"kr": "이거로 할게요.", "roman": "Igeoro halgeyo.", "en": "I'll have this one."},
    {"kr": "맵지 않게 해주세요.", "roman": "Maepji anke hae juseyo.", "en": "Make it not spicy, please."},
    {"kr": "물 한 잔 더 주세요.", "roman": "Mul han jan deo juseyo.", "en": "One more glass of water, please."},
    {"kr": "포장해 주세요.", "roman": "Pojang-hae juseyo.", "en": "To go, please. / Wrap it up."},
    {"kr": "따뜻하게 해주세요.", "roman": "Ttatteutage hae juseyo.", "en": "Make it hot/warm, please."},
    {"kr": "여기서 먹을게요.", "roman": "Yeogiseo meogeulgeyo.", "en": "I'll eat here."},
    {"kr": "잘 먹었습니다.", "roman": "Jal meogeot-seumnida.", "en": "Thank you for the meal."},
    {"kr": "맛있어요.", "roman": "Masisseoyo.", "en": "It's delicious."},
    {"kr": "추천 메뉴 있어요?", "roman": "Chucheon menyu isseoyo?", "en": "Do you have any recommendations?"},
    {"kr": "조금만 기다려 주세요.", "roman": "Jogeum-man gidaryeo juseyo.", "en": "Please wait a moment."},
    {"kr": "이거 한 개에 얼마예요?", "roman": "Igeo han gae-e eolma-yeyo?", "en": "How much per piece?"},
    {"kr": "맛보기 해도 될까요?", "roman": "Matbogi haedo doelkkayo?", "en": "May I try a sample?"},
    {"kr": "너무 비싸요. 깎아주세요.", "roman": "Neomu bissayo. Kkakka-juseyo.", "en": "It's too expensive. Give me a discount."},
    {"kr": "여기 있어요?", "roman": "Yeogi isseoyo?", "en": "Is it here? / Are you here?"},
    {"kr": "네, 여기요.", "roman": "Ne, yeogiyo.", "en": "Yes, over here. / Yes, I'm here."},
    {"kr": "천 원이에요.", "roman": "Cheon won-ieyo.", "en": "It's 1,000 won."},
    {"kr": "감사합니다.", "roman": "Gamsa-hamnida.", "en": "Thank you."},
    {"kr": "괜찮아요.", "roman": "Gwaenchanayo.", "en": "It's okay. / No problem."},
    {"kr": "다음에 또 올게요.", "roman": "Da-eum-e tto olgeyo.", "en": "I'll come again next time."},
    {"kr": "편하게 드세요.", "roman": "Pyeonhage deuseyo.", "en": "Make yourself at home. / Help yourself."},
    {"kr": "뜨거우니까 조심하세요.", "roman": "Tteugeounikka josimhaseyo.", "en": "It's hot, so be careful."},
]

# K-Slang: 요즘 한국어 표현 (의미·사용법 영어 설명)
SLANG_ITEMS: List[Dict] = [
    {"word": "맛점", "meaning_en": "A blend of '맛있는(licious)' + '점심(lunch)'. Means 'enjoy your lunch' or 'have a nice lunch'.", "usage_en": "Say it when someone is about to eat lunch or when you're leaving at lunchtime. e.g. '맛점 하세요!' = 'Enjoy your lunch!'"},
    {"word": "대박", "meaning_en": "Literally 'big gourd'. Slang for 'awesome', 'amazing', 'daebak', or sometimes 'huge (success/fail)'.", "usage_en": "Use when something is impressive or shocking. e.g. '대박!' = 'Wow!/No way!' '대박이다' = 'It's amazing.'"},
    {"word": "진짜", "meaning_en": "Really, seriously, for real. Emphasizes that you mean what you say.", "usage_en": "Before a statement: '진짜 맛있어요' = 'It's really good.' Or alone: '진짜?' = 'Really?'"},
    {"word": "심심이", "meaning_en": "From '심심하다' (to be bored). A cute way to say 'I'm bored' or 'bored person'.", "usage_en": "Say '심심해요' or '나 심심이' when you're bored. Often used playfully."},
    {"word": "킹받다", "meaning_en": "Slang for 'extremely annoying' or 'makes me so mad'. From '열받다' (to get angry) with '킹(king)' for emphasis.", "usage_en": "Use when something really annoys you. e.g. '진짜 킹받아' = 'I'm so annoyed.'"},
    {"word": "레알", "meaning_en": "Konglish for 'real'. Used to mean 'for real', 'seriously'.", "usage_en": "Same as '진짜'. e.g. '레알?' = 'For real?' '레알 대박' = 'Seriously amazing.'"},
    {"word": "ㅋㅋ / ㅎㅎ", "meaning_en": "Korean internet laughter. ㅋㅋ = 'kk' (laughing), ㅎㅎ = 'hh' (softer laugh).", "usage_en": "Add at the end of messages like 'lol' or 'haha'. More ㅋ = more laughter. e.g. '맛있어요 ㅋㅋ'"},
    {"word": "갓", "meaning_en": "Konglish 'god' used as prefix. Means 'god-tier', 'the best'.", "usage_en": "Put before a word to praise. e.g. '갓 맛집' = 'god-tier restaurant', '갓 스타' = 'god star'."},
    {"word": "핵", "meaning_en": "Literally 'nuclear'. Slang for 'extremely', 'super'.", "usage_en": "Used like '핵 맛있어' = 'super delicious', '핵 귀여워' = 'super cute'."},
    {"word": "실화", "meaning_en": "Short for '실제 이야기' (real story). Means 'for real?', 'is this real?'.", "usage_en": "When something is hard to believe. e.g. '실화야?' = 'Is this for real?'"},
]


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("profile", {"name": "학습자", "level": "A2", "goal": "K-드라마로 자연스러운 회화 익히기"})
    ss.setdefault("current_theme", "restaurant")  # restaurant | airport | market
    ss.setdefault("gemini_api_key", "")
    ss.setdefault("admin_mode", False)
    ss.setdefault("settings_unlocked", False)  # 설정 팝오버 비밀번호 통과 여부
    ss.setdefault("history", [])
    ss.setdefault("saved_lines", [])
    ss.setdefault("deck", [])
    ss.setdefault("deck_stats", {"correct": 0, "wrong": 0})


def add_history(event_type: str, payload: Dict) -> None:
    st.session_state.history.append({"ts": now_iso(), "type": event_type, "payload": payload})


# Google Search Grounding: 실시간 검색 결과를 답변에 반영 (REST API 형식)
# https://ai.google.dev/gemini-api/docs/grounding
GOOGLE_SEARCH_TOOLS = [{"google_search": {}}]


def _get_response_text(response) -> str:
    """Gemini 응답에서 텍스트 추출 (response.text 또는 candidates에서)."""
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


# [핵심] 여러 모델을 순서대로 시도해보는 함수
# use_grounding=False: 역할플레이 등에서 두 번째 메시지부터 답장이 없어지는 현상 방지 (도구 없이만 호출)
def try_generate_content(prompt: str, use_grounding: bool = True) -> str:
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
            # 1) 먼저 Google Search Grounding으로 시도 (실시간 검색 반영)
            try:
                response = model.generate_content(prompt, tools=GOOGLE_SEARCH_TOOLS)
                text = _get_response_text(response)
                if text and text.strip():
                    return text.strip()
            except Exception:
                pass
            # 2) 도구 미지원/오류 시 같은 모델로 도구 없이 재시도 (답장은 반드시 보장)
            response = model.generate_content(prompt)
            text = _get_response_text(response)
            if text and text.strip():
                return text.strip()
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

    # 테마 선택: 식당 / 공항 / 전통시장 (AI 페르소나·추천 문장 자동 변경)
    st.sidebar.header("테마")
    theme_options = [(k, f"{v['name']} ({v['name_en']})") for k, v in THEMES.items()]
    current = st.session_state.get("current_theme", "restaurant")
    choice = st.sidebar.radio(
        "장소를 골라 보세요",
        options=[t[0] for t in theme_options],
        format_func=lambda k: dict(theme_options)[k],
        index=list(THEMES.keys()).index(current) if current in THEMES else 0,
        key="sidebar_theme_radio",
    )
    if choice != current:
        st.session_state["current_theme"] = choice
        st.rerun()

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
    """테마별 추천 문장을 보여주고, 선택한 표현으로 롤플레이 연결."""
    theme_key = st.session_state.get("current_theme", "restaurant")
    theme = THEMES.get(theme_key, THEMES["restaurant"])
    lines = theme["lines"]
    theme_name = theme["name"]

    st.header("메뉴 표현 익히기")
    st.caption(f"{theme_name}에서 쓸 수 있는 표현을 골라 보세요.")

    idx = st.selectbox(
        "표현 고르기",
        options=list(range(len(lines))),
        format_func=lambda i: lines[i].kr,
    )
    item = lines[idx]

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
        st.success(f"→ **{theme_name}** 탭에서 **AI 점원과 주문 연습**으로 이동해 연습해 보세요.")


def tab_slang() -> None:
    """요즘 한국어(K-Slang): 맛점, 대박, 진짜 등 의미·사용법 영어 설명."""
    st.header("요즘 한국어 (K-Slang)")
    st.caption("맛점, 대박, 진짜 같은 표현의 의미와 사용법을 영어로 알아보세요.")

    for i, s in enumerate(SLANG_ITEMS):
        with st.container():
            st.markdown(
                f"""
                <div class="slang-card">
                    <div class="slang-word">✨ {s["word"]}</div>
                    <div class="slang-meaning"><strong>Meaning:</strong> {s["meaning_en"]}</div>
                    <div class="slang-usage"><strong>Usage:</strong> {s["usage_en"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")  # 간격


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
    theme_key = st.session_state.get("current_theme", "restaurant")
    theme = THEMES.get(theme_key, THEMES["restaurant"])
    greeting = theme["greeting"]
    persona = theme["persona"]
    st.session_state.setdefault("pending_prompt", None)

    if "last_seed" not in st.session_state or st.session_state.last_seed != seed["kr"]:
        st.session_state.roleplay_history = [{"role": "model", "content": greeting}]
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
            fallback_msg = "잠시 답변이 어려워요. 주문이든 메뉴든 다시 말씀해 주세요! 😅"
            try:
                current_time_str = get_current_kst_str()
                full_prompt = f"""
                당신은 **{persona}**입니다.
                상대방은 한국어를 배우는 손님이에요. 미션 수행을 확인하는 선생님이 아니라, 손님과 즐겁게 수다도 떨 줄 아는 직원/상인이에요.
                직원의 태도: 친절함, 정중함, 격려해주는 태도. 대화는 풍부하고 자연스럽게.

                [시점·장소]
                Current Date: {current_time_str}
                Current Location: {theme.get('name_en', 'Restaurant')} setting (roleplay)

                [대화 우선순위 (필수)]
                - 손님이 날씨·안부·추천·질문 등을 하면 **그 질문에 대한 답변을 최우선**으로 해라. 답은 친절하고 풍부하게.
                - **매 답변 끝에 미션 문장을 똑같이 반복하지 마라.** 미션에만 집착하면 대화가 부자연스러워진다.
                - 오늘의 연습 문장(미션)은 "{seed['kr']}"이지만, 손님이 다른 이야기를 꺼내면 그 내용에 우선 집중해라.

                [미션 상기 (가볍게만)]
                - 미션은 **대화 흐름상 적절할 때만** 가볍게 언급해라. 예: 메뉴 추천을 마친 후, 혹은 대화가 마무리될 즈음에 "아 참, 아까 연습하시던 '여기 짜장면 하나랑...' 문장도 한 번 써보시겠어요?" 정도로만.
                - **이미 손님이 미션 문장을 한 번이라도 사용했다면**, 그 이후에는 미션을 더 강조하지 말고 일반적인 손님·점원 수다에만 집중해라.
                - 목표: 손님이 미션에 얽매이지 않고 편안하게 한국어 대화를 즐길 수 있게 해라.

                [2026년 한국 기본 정보 (간단 질문에만 사용)]
                - 대한민국 현 대통령은 이재명(Lee Jae-myung)입니다. 2025년 6월 취임.
                - 손님이 "현재 대통령이 누구야?"처럼 짧게만 물을 때만 이 정보로 답하고, 바로 식사·주문 이야기로 넘어가라.

                [역할 고정 및 정치 질문 방어 (필수)]
                - 너는 현재 역할(점원/직원/상인)이지, 정치 전문가나 판사가 아니다.
                - 손님이 대통령·재판·형량·뉴스 등 정치적인 깊은 이야기를 꺼내면, **"아이고, 저는 뉴스를 잘 안 봐서 그런 건 잘 모릅니다. 😅 다른 거 도와드릴까요?"** 처럼 짧게 넘기고 자연스럽게 현재 장소(주문/체크인/쇼핑 등) 이야기로 화제를 돌려라.
                - 손님이 사실을 우기면, 동의하거나 반박하지 말고 **"손님이 더 잘 아시네요! 저는 일 보러 가야겠어요."** 하고 넘겨라. 모르는 사실은 지어내지 말라.

                너는 현재 {current_time_str} 기준의 상황에 있다. 시간·날짜는 위 정보를 바탕으로 짧게만 답하라.
                대화 내역 (마지막 말에 자연스럽게 답하세요):
                """
                history_lines = []
                recent = st.session_state.roleplay_history[-8:]  # 최근 8턴만 (토큰/오류 방지)
                for m in recent:
                    role = "손님" if m["role"] == "user" else "점원"
                    history_lines.append(f"{role}: {m['content']}")
                full_prompt += "\n".join(history_lines)
                full_prompt += "\n위 맥락에 맞춰 손님의 마지막 말에 자연스럽게 한국어로 답변하세요. 점원으로서 한 번만 답하세요."
                try:
                    response_text = try_generate_content(full_prompt, use_grounding=False)
                except Exception as api_err:
                    err_str = str(api_err)
                    st.error(f"AI 연결 오류: {err_str}")
                    response_text = f"⚠️ **연결 오류:** {err_str}\n\n위 오류가 반복되면 ⚙️ 설정 → 관리자 모드에서 **Gemini API 키**를 확인해 주세요."
                if not (response_text and response_text.strip()):
                    response_text = fallback_msg
                placeholder.markdown(response_text)
                st.session_state.roleplay_history.append({"role": "model", "content": response_text})
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
                err_hint = " (⚙️ 설정 → 관리자 모드에서 Gemini API 키를 확인해 주세요.)"
                placeholder.markdown(fallback_msg + err_hint)
                st.session_state.roleplay_history.append({"role": "model", "content": fallback_msg + err_hint})

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

        /* 오늘의 한 문장 카드: 베이지 헤더와 어울리는 카드 */
        .daily-sentence-card {{
            background: linear-gradient(135deg, #FFF8E1 0%, #FFF3E0 100%) !important;
            border: 1px solid #FFE0B2 !important;
            border-radius: 12px !important;
            padding: 1rem 1.2rem !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            margin-bottom: 0.5rem !important;
        }}
        .daily-sentence-title {{
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            color: #5D4037 !important;
            margin-bottom: 0.5rem !important;
        }}
        .daily-sentence-kr {{
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            color: #E65100 !important;
        }}
        .daily-sentence-roman {{
            font-size: 0.9rem !important;
            color: #795548 !important;
            margin-top: 0.25rem !important;
        }}
        .daily-sentence-en {{
            font-size: 0.95rem !important;
            color: #5D4037 !important;
            margin-top: 0.25rem !important;
        }}

        /* K-Slang 카드: 깔끔한 카드 스타일 */
        .slang-card {{
            background-color: #FFFBF5 !important;
            border: 1px solid #FFE0B2 !important;
            border-radius: 12px !important;
            padding: 1rem 1.2rem !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
            margin-bottom: 0.8rem !important;
        }}
        .slang-word {{
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            color: #E65100 !important;
            margin-bottom: 0.4rem !important;
        }}
        .slang-meaning, .slang-usage {{
            font-size: 0.9rem !important;
            color: #5D4037 !important;
            line-height: 1.5 !important;
        }}
        .slang-usage {{
            margin-top: 0.3rem !important;
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
    # 팝업을 닫거나 다른 곳을 클릭하면 자동으로 다시 잠금 (방금 비밀번호 통과한 경우만 유지)
    if not st.session_state.get("just_unlocked", False):
        st.session_state["settings_unlocked"] = False
    st.session_state["just_unlocked"] = False
    _inject_hide_footer_early()
    # 상단 헤더 (HTML) → 바로 아래 설정 버튼(popover), CSS로 헤더 박스 위에 겹쳐 표시
    render_header()
    with st.popover("⚙️", help="설정"):
        if not st.session_state.get("settings_unlocked", False):
            pin = st.text_input(
                "4자리 비밀번호",
                type="password",
                max_chars=4,
                key="settings_pin_input",
                placeholder="****",
            )
            if st.button("확인", key="settings_pin_confirm"):
                if pin == ADMIN_PIN:
                    st.session_state["settings_unlocked"] = True
                    st.session_state["just_unlocked"] = True  # 이번 실행에서만 잠금 해제 유지
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        else:
            st.toggle(
                "관리자 모드 (Admin Mode)",
                value=st.session_state.get("admin_mode", False),
                key="admin_mode",
            )
            if st.button("잠금", key="settings_lock"):
                st.session_state["settings_unlocked"] = False
                st.rerun()
    # 오늘의 한 문장: 날짜(일) 기준 매일 다른 표현 (카드 스타일)
    day_idx = datetime.now(KST).timetuple().tm_yday % len(DAILY_SENTENCES)
    daily = DAILY_SENTENCES[day_idx]
    st.markdown(
        f"""
        <div class="daily-sentence-card">
            <div class="daily-sentence-title">📅 오늘의 한 문장</div>
            <div class="daily-sentence-kr">{daily["kr"]}</div>
            <div class="daily-sentence-roman">{daily["roman"]}</div>
            <div class="daily-sentence-en">{daily["en"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    st.divider()

    sidebar_profile()

    is_admin = st.session_state.get("admin_mode", False)
    _inject_app_styles(is_admin)

    tabs = st.tabs(["메뉴 표현 익히기", "요즘 한국어 (K-Slang)", "AI 점원과 주문 연습"])
    with tabs[0]:
        tab_menu_learn()
    with tabs[1]:
        tab_slang()
    with tabs[2]:
        tab_roleplay()


if __name__ == "__main__":
    main()