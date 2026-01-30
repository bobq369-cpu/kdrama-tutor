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

try:
    from gtts import gTTS
    import io
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


APP_TITLE = "K-Tutor · 글로벌 한국어 학습 앱"
APP_SUBTITLE = "상황별 역할놀이로 실전 한국어를 익혀 보세요"


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


# 식당 시나리오: 삼겹살 주문 (역할: 식당 이모님)
SAMPLE_LINES_RESTAURANT: List[LineItem] = [
    LineItem(
        show="(식당) 삼겹살 주문",
        level="A1",
        kr="삼겹살 2인분이랑 된장찌개 하나 주세요.",
        roman="Samgyeopsal i-inbun-irang doenjang-jjigae hana juseyo.",
        en="I'd like two orders of samgyeopsal and one doenjang jjigae, please.",
        notes="고기집에서 삼겹살·찌개 주문할 때 쓰는 표현.",
        vocab=[("삼겹살", "Samgyeopsal (pork belly)"), ("인분", "Serving"), ("된장찌개", "Doenjang stew")],
        patterns=[("~ 주세요", "무언가를 정중하게 요청할 때")],
        th=None,
    ),
    LineItem(
        show="(식당) 반찬/추가",
        level="A1",
        kr="상추랑 쌈장 더 주실 수 있나요?",
        roman="Sangchu-rang ssamjang deo jusil su innayo?",
        en="Could I have more lettuce and ssamjang?",
        notes="쌈 채소·쌈장 추가 요청.",
        vocab=[("상추", "Lettuce"), ("쌈장", "Ssamjang (dipping sauce)")],
        patterns=[("~ 더 주실 수 있나요?", "추가 요청할 때")],
        th=None,
    ),
    LineItem(
        show="(식당) 추천 메뉴",
        level="A2",
        kr="이모님, 여기 제일 잘 나가는 메뉴가 뭐예요?",
        roman="Imo-nim, yeogi jeil jal na-ga-neun menu-ga mwo-yeyo?",
        en="What's the most popular menu here?",
        notes="이모님께 인기 메뉴 물어볼 때.",
        vocab=[("이모님", "Auntie / friendly term for server"), ("잘 나가다", "To sell well")],
        patterns=[("~가 뭐예요?", "정보를 물어볼 때")],
        th=None,
    ),
    LineItem(
        show="(식당) 계산하기",
        level="A1",
        kr="잘 먹었습니다! 계산해 주세요.",
        roman="Jal meogeot-seumnida! Gyesan-hae juseyo.",
        en="It was delicious! Check, please.",
        notes="식사 마치고 계산할 때.",
        vocab=[("잘 먹었습니다", "Thank you for the meal"), ("계산", "Bill/Check")],
        patterns=[("~해 주세요", "행동을 부탁할 때")],
        th=None,
    ),
]

# 공항 시나리오: 입국 심사 (역할: 입국 심사관)
SAMPLE_LINES_AIRPORT: List[LineItem] = [
    LineItem(
        show="(공항) 입국 목적",
        level="A1",
        kr="관광으로 왔어요. 일주일 있을 예정이에요.",
        roman="Gwangwang-euro wasseoyo. Ilju-il isseul yejeong-ieyo.",
        en="I came for tourism. I'm planning to stay for a week.",
        notes="입국 심사관이 목적·체류 기간을 물을 때 답하는 표현.",
        vocab=[("관광", "Tourism"), ("일주일", "One week"), ("예정", "Plan")],
        patterns=[("~으로 왔어요", "목적을 말할 때"), ("~ 있을 예정이에요", "계획을 말할 때")],
        th=None,
    ),
    LineItem(
        show="(공항) 숙소",
        level="A1",
        kr="호텔에 묵을 거예요. 주소 적어 왔어요.",
        roman="Hotel-e mug-eul geoyeyo. Juso jeogeo wasseoyo.",
        en="I'll be staying at a hotel. I wrote down the address.",
        notes="숙소 질문에 답할 때.",
        vocab=[("묵다", "To stay"), ("주소", "Address"), ("적다", "To write down")],
        patterns=[("~에 묵을 거예요", "숙소를 말할 때")],
        th=None,
    ),
    LineItem(
        show="(공항) 체크인",
        level="A1",
        kr="인천행 비행기 표 예약했는데요, 체크인 해주세요.",
        roman="Incheon-haeng bihaenggi pyo ye-yak-haet-neundeyo, chekeu-in hae juseyo.",
        en="I have a reservation for a flight to Incheon. I'd like to check in, please.",
        notes="공항 카운터에서 체크인 요청.",
        vocab=[("인천행", "To Incheon"), ("예약", "Reservation"), ("체크인", "Check-in")],
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
]

# 편의점 시나리오: 라면·교통카드 (역할: 알바생)
SAMPLE_LINES_CONVENIENCE_STORE: List[LineItem] = [
    LineItem(
        show="(편의점) 라면",
        level="A1",
        kr="라면 하나 먹고 갈게요. 뜨거운 물 부어 주세요.",
        roman="Ramen hana meokgo galgeyo. Tteugeoun mul bu-eo juseyo.",
        en="I'll have one ramen to eat here. Please add hot water.",
        notes="편의점에서 라면 먹고 갈 때.",
        vocab=[("라면", "Ramen"), ("먹고 가다", "Eat and go"), ("뜨거운 물", "Hot water")],
        patterns=[("~ 먹고 갈게요", "여기서 먹을 때")],
        th=None,
    ),
    LineItem(
        show="(편의점) 교통카드",
        level="A1",
        kr="교통카드 하나 새로 사고, 만 원 충전해 주세요.",
        roman="Gyotong-kadeu hana saero sago, man won chungjeon-hae juseyo.",
        en="I'd like to buy a new transit card and charge 10,000 won, please.",
        notes="교통카드 구매·충전 요청.",
        vocab=[("교통카드", "Transit card"), ("충전", "Recharge")],
        patterns=[("~ 해 주세요", "행동을 부탁할 때")],
        th=None,
    ),
    LineItem(
        show="(편의점) 계산",
        level="A1",
        kr="이거랑 이거 같이 계산해 주세요.",
        roman="Igeo-rang igeo gachi gyesan-hae juseyo.",
        en="I'd like to pay for these together, please.",
        notes="여러 품목 한꺼번에 계산.",
        vocab=[("같이", "Together"), ("계산", "Check out")],
        patterns=[("~ 같이 계산해 주세요", "함께 결제할 때")],
        th=None,
    ),
    LineItem(
        show="(편의점) 영수증",
        level="A1",
        kr="영수증 주세요.",
        roman="Yeongsujeung juseyo.",
        en="Receipt, please.",
        notes="영수증 요청.",
        vocab=[("영수증", "Receipt")],
        patterns=[("~ 주세요", "요청할 때")],
        th=None,
    ),
]

# K-드라마 시나리오: 카페에서 이별 통보 (역할: 재벌 2세 남주)
SAMPLE_LINES_KDRAMA: List[LineItem] = [
    LineItem(
        show="(K-드라마) 이별 통보",
        level="B1",
        kr="우리 이대로는 안 될 것 같아. 헤어지자.",
        roman="Uri idaero-neun an doel geot gata. Heeoji-ja.",
        en="I don't think we can go on like this. Let's break up.",
        notes="이별을 통보하는 드라마 같은 표현.",
        vocab=[("이대로", "Like this"), ("헤어지다", "To break up")],
        patterns=[("~ 것 같아", "추측/결정을 말할 때"), ("~자", "제안할 때")],
        th=None,
    ),
    LineItem(
        show="(K-드라마) 이유",
        level="B1",
        kr="네가 잘못한 게 아니라, 내가 더 이상 널 행복하게 해줄 수 없을 것 같아서.",
        roman="Ne-ga jalmoshan ge anira, nae-ga deo isang neol haengbok-hage hae-jul su eopseul geot gataseo.",
        en="It's not that you did something wrong. I just don't think I can make you happy anymore.",
        notes="이별 이유를 말할 때 (드라마 톤).",
        vocab=[("잘못", "Wrong"), ("행복하게 하다", "To make happy")],
        patterns=[("~ 게 아니라", "부정·대조"), ("~ 수 없을 것 같아서", "이유를 말할 때")],
        th=None,
    ),
    LineItem(
        show="(K-드라마) 마무리",
        level="B1",
        kr="지금까지 고마웠어. 앞으로 잘 지내.",
        roman="Jigeum-kkaji gomawoosseo. Apeuro jal jinae.",
        en="Thank you for everything until now. Take care.",
        notes="이별 인사.",
        vocab=[("지금까지", "Until now"), ("잘 지내다", "To get along / take care")],
        patterns=[("~ 고마웠어", "감사 인사"), ("앞으로 잘 지내", "작별 인사")],
        th=None,
    ),
    LineItem(
        show="(K-드라마) 카페 주문",
        level="A1",
        kr="아메리카노 두 잔 주세요.",
        roman="Americano du jan juseyo.",
        en="Two Americanos, please.",
        notes="카페에서 주문.",
        vocab=[("아메리카노", "Americano"), ("잔", "Cup")],
        patterns=[("~ 주세요", "요청할 때")],
        th=None,
    ),
]

# 글로벌 한국어 학습 앱(K-Tutor) 시나리오: 역할·상황·페르소나·인사말·추천 문장
# 선택한 시나리오에 따라 화면 제목·설명·AI 역할이 전부 바뀜
# 시나리오별 이미지: Unsplash 무료 이미지 URL (테마 비주얼 강화)
SCENARIOS: Dict[str, Dict] = {
    "airport": {
        "name": "공항",
        "name_en": "Airport",
        "role": "입국 심사관",
        "situation": "입국 심사 받기",
        "persona": "인천공항에서 근무하는 **깐깐하고 절차에 충실한 입국 심사관**. 표정은 무뚝뚝하고 질문은 짧고 명확하게. 규칙을 중요시하며 불필요한 수다를 하지 않음.",
        "greeting": "여권 주세요. 입국 목적이 뭐예요?",
        "lines": SAMPLE_LINES_AIRPORT,
        "emoji": "✈️",
        "image_url": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1200&q=80",
    },
    "restaurant": {
        "name": "식당",
        "name_en": "Restaurant",
        "role": "식당 이모님",
        "situation": "삼겹살 주문하기",
        "persona": "한식당에서 일하는 **친절하고 말걸기 좋은 식당 이모님**. 손님한테 반말 섞인 존댓말로 편하게 말하고, 추천도 잘해 줌.",
        "greeting": "어서 오세요~ 몇 분이에요? 삼겹살 드실 거예요? 🥩",
        "lines": SAMPLE_LINES_RESTAURANT,
        "emoji": "🥩",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=1200&q=80",
    },
    "convenience_store": {
        "name": "편의점",
        "name_en": "Convenience Store",
        "role": "알바생",
        "situation": "라면과 교통카드 사기",
        "persona": "편의점에서 일하는 **말이 짧고 무난한 알바생**. 바쁜 느낌으로 최소한의 말만 하고, 필요한 질문만 함.",
        "greeting": "어서 오세요. 찾는 거 있으세요?",
        "lines": SAMPLE_LINES_CONVENIENCE_STORE,
        "emoji": "🏪",
        "image_url": "https://images.unsplash.com/photo-1604719314656-89142e770061?w=1200&q=80",
    },
    "kdrama": {
        "name": "K-드라마",
        "name_en": "K-Drama",
        "role": "재벌 2세 남주인공",
        "situation": "카페에서 이별 통보하기",
        "persona": "드라마에 나오는 **재벌 2세 남주인공**. 카페에서 상대에게 이별을 통보하는 장면. 말투는 차갑고 단호하지만, 내면은 복잡하고 감정이 격함. 짧은 문장과 묵직한 침묵을 사용.",
        "greeting": "… 앉아. 할 말이 있어.",
        "lines": SAMPLE_LINES_KDRAMA,
        "emoji": "🎬",
        "image_url": "https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=1200&q=80",
    },
}


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
    ss.setdefault("profile", {"name": "학습자", "level": "A2", "goal": "글로벌 한국어 학습 (K-Tutor)"})
    ss.setdefault("current_scenario", "restaurant")  # airport | restaurant | convenience_store | kdrama
    ss.setdefault("gemini_api_key", "")
    ss.setdefault("history", [])
    ss.setdefault("saved_lines", [])
    ss.setdefault("deck", [])
    ss.setdefault("deck_stats", {"correct": 0, "wrong": 0})


def add_history(event_type: str, payload: Dict) -> None:
    st.session_state.history.append({"ts": now_iso(), "type": event_type, "payload": payload})


# TTS 캐시: 동일 텍스트 재생성 방지 (속도·API 절약)
def _tts_cache() -> Dict[str, bytes]:
    if "tts_cache" not in st.session_state:
        st.session_state["tts_cache"] = {}
    return st.session_state["tts_cache"]


def text_to_speech_korean(text: str, max_chars: int = 500) -> Optional[bytes]:
    """한국어 텍스트를 gTTS로 mp3 바이트로 변환. 에러 시 None, 필요 시 최대 max_chars만 변환."""
    if not text or not text.strip():
        return None
    if not GTTS_AVAILABLE:
        return None
    # 마크다운·특수문자 제거, 앞부분만 사용 (속도·품질)
    clean = re.sub(r"[*_#\[\]()`]", " ", text).strip()
    clean = re.sub(r"\s+", " ", clean)[:max_chars]
    if not clean:
        return None
    cache = _tts_cache()
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
        return data
    except Exception:
        return None


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


def render_header(scenario_key: str = "restaurant") -> None:
    """슬림 헤더: K-Tutor + 선택된 시나리오에 맞는 제목·설명. (divider는 호출부에서 처리)"""
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["restaurant"])
    emoji = scenario.get("emoji", "🇰🇷")
    title = f"K-Tutor · {scenario['name']} — {scenario['situation']}"
    st.markdown(
        f"""
        <div class="header-container">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">{emoji}</span>
            <div class="header-text">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_scenario() -> None:
    """사이드바 최상단: 학습 장소 선택(시나리오). API 키는 st.secrets에서 자동 로드."""
    if "GEMINI_API_KEY" in st.secrets:
        st.session_state.gemini_api_key = st.secrets["GEMINI_API_KEY"]
        if GEMINI_AVAILABLE:
            genai.configure(api_key=st.session_state.gemini_api_key)

    st.sidebar.header("학습 장소 선택")
    st.sidebar.caption("Select a Scenario")
    scenario_options = list(SCENARIOS.keys())
    scenario_labels = [f"{SCENARIOS[k].get('emoji', '')} {SCENARIOS[k]['name']} — {SCENARIOS[k]['situation']}" for k in scenario_options]
    current = st.session_state.get("current_scenario", "restaurant")
    choice_idx = scenario_options.index(current) if current in scenario_options else 0
    choice = st.sidebar.selectbox(
        "시나리오",
        options=range(len(scenario_options)),
        format_func=lambda i: scenario_labels[i],
        index=choice_idx,
        key="sidebar_scenario_select",
    )
    selected_key = scenario_options[choice]
    if selected_key != current:
        st.session_state["current_scenario"] = selected_key
        if "roleplay_seed" in st.session_state:
            del st.session_state["roleplay_seed"]
        if "last_seed" in st.session_state:
            del st.session_state["last_seed"]
        if "roleplay_history" in st.session_state:
            del st.session_state["roleplay_history"]
        st.rerun()


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
    """선택된 시나리오의 추천 문장을 보여주고, 선택한 표현으로 AI 역할놀이 연결."""
    scenario_key = st.session_state.get("current_scenario", "restaurant")
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["restaurant"])
    lines = scenario["lines"]
    situation = scenario["situation"]
    role = scenario["role"]

    st.header("표현 익히기")
    st.caption(f"**{situation}** — {role}와(과) 쓸 수 있는 표현을 골라 보세요.")

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

    if st.button("AI와 역할놀이 시작", type="primary"):
        st.session_state.roleplay_seed = {"kr": item.kr, "en": item.en}
        add_history("roleplay_start", {"kr": item.kr})
        st.success("→ **AI와 역할놀이** 탭에서 선택한 시나리오의 역할로 대화해 보세요.")


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
    """Chat Pattern: 선택된 시나리오의 역할로 AI가 대화. 헤더 → 과거 대화 → 입력 처리 → chat_input 하단 고정."""
    if "roleplay_seed" not in st.session_state:
        st.info("👋 먼저 **표현 익히기** 탭에서 표현을 골라 **AI와 역할놀이 시작** 버튼을 눌러 주세요.")
        return

    seed = st.session_state["roleplay_seed"]
    scenario_key = st.session_state.get("current_scenario", "restaurant")
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["restaurant"])
    greeting = scenario["greeting"]
    persona = scenario["persona"]
    role = scenario["role"]
    situation = scenario["situation"]
    st.session_state.setdefault("pending_prompt", None)

    if "last_seed" not in st.session_state or st.session_state.last_seed != seed["kr"]:
        st.session_state.roleplay_history = [{"role": "model", "content": greeting}]
        st.session_state.last_seed = seed["kr"]

    # ─── 1. 헤더/미션 출력 ───────────────────────────────────────────────
    st.header("AI와 역할놀이")
    st.success(f"🎯 **{situation}** — 연습 문장: **{seed['kr']}** (상대 역할: {role})")

    # 퀵 답장: 채팅창 내 표현 고르기 버튼
    st.caption("💬 빠른 표현 (클릭하면 입력창에 넣어짐)")
    quick_lines = scenario["lines"][:5]
    cols = st.columns(min(len(quick_lines), 5))
    for i, line in enumerate(quick_lines):
        with cols[i % len(cols)]:
            if st.button(line.kr[:20] + ("…" if len(line.kr) > 20 else ""), key=f"quick_reply_{scenario_key}_{i}", use_container_width=True):
                st.session_state.pending_prompt = line.kr
                st.rerun()

    # ─── 2. st.chat_input 호출 전에 과거 대화(history) 전부 출력 + AI 답변에 TTS 플레이어 ─────────
    for msg in st.session_state.roleplay_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "model" and msg.get("content"):
                audio_bytes = text_to_speech_korean(msg["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

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
            fallback_msg = "잠시 답변이 어려워요. 다시 한 번 말씀해 주세요."
            try:
                current_time_str = get_current_kst_str()
                role_label = role  # 입국 심사관, 식당 이모님 등
                full_prompt = f"""
                당신은 **{persona}**
                상대방은 한국어를 배우는 학습자이며, 지금 '{situation}' 상황을 연습 중이다. 당신은 이 상황에서의 **{role_label}** 역할만 수행한다. 다른 앱/상황의 캐릭터가 아니라, **선택된 이 시나리오의 역할에 완전히 충실**하라.

                [시점·장소]
                Current Date: {current_time_str}
                Current Scenario: {scenario.get('name_en', scenario.get('name', 'Roleplay'))} — {situation}

                [역할 유지 (필수)]
                - **공항(입국 심사관)**이면: 깐깐하고 무뚝뚝하며, 질문은 짧고 명확하게. 불필요한 친절이나 수다 금지.
                - **식당(이모님)**이면: 친절하고 말걸기 좋게, 반말 섞인 존댓말로 편하게.
                - **편의점(알바생)**이면: 말 짧고 무난하게, 필요한 말만.
                - **K-드라마(재벌 2세)**이면: 차갑고 단호한 말투, 감정은 묵직하게. 짧은 문장과 침묵 활용.
                - 매 답변 끝에 미션 문장을 똑같이 반복하지 마라. 대화 흐름상 적절할 때만 가볍게 "아까 연습하시던 '…' 한 번 써보세요" 정도로 언급.
                - 연습 문장(미션)은 "{seed['kr']}"이지만, 상대가 다른 말을 꺼내면 그에 맞춰 **역할에 맞게** 답하라.

                [대화 우선순위]
                - 상대의 질문·말에 **역할에 맞는 태도로** 최우선 답변. 이미 상대가 미션 문장을 썼으면 미션을 반복하지 말고 자연스럽게 대화만 이어가라.

                [역할 고정 및 정치/일반 방어]
                - 너는 오직 **{role_label}**이지, 정치·뉴스 전문가가 아니다. 정치/재판 등 깊은 이야기가 나오면 "그런 건 잘 모르겠어요. (현재 상황으로) 돌아가자." 식으로 짧게 넘기고, 현재 시나리오(입국/주문/편의점/이별 등)로 화제를 돌려라.
                - 모르는 사실은 지어내지 말고, "그건 잘 모르겠어요." 하고 넘겨라.

                현재 시각: {current_time_str}. 시간·날짜 질문은 위 정보 기준으로 짧게만 답하라.
                대화 내역 (마지막 말에 **역할에 맞게** 한국어로 한 번만 답하세요):
                """
                history_lines = []
                recent = st.session_state.roleplay_history[-8:]
                for m in recent:
                    speaker = "상대(학습자)" if m["role"] == "user" else role_label
                    history_lines.append(f"{speaker}: {m['content']}")
                full_prompt += "\n".join(history_lines)
                full_prompt += f"\n위 맥락에 맞춰 상대의 마지막 말에 **{role_label}** 역할로 자연스럽게 한국어로 한 번만 답하세요."
                try:
                    response_text = try_generate_content(full_prompt, use_grounding=False)
                except Exception as api_err:
                    err_str = str(api_err)
                    st.error(f"AI 연결 오류: {err_str}")
                    response_text = f"⚠️ **연결 오류:** {err_str}\n\n배포 시 **st.secrets**에 **GEMINI_API_KEY**를 설정해 주세요."
                if not (response_text and response_text.strip()):
                    response_text = fallback_msg
                placeholder.markdown(response_text)
                st.session_state.roleplay_history.append({"role": "model", "content": response_text})
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
                err_hint = " (배포 시 st.secrets에 GEMINI_API_KEY를 설정해 주세요.)"
                placeholder.markdown(fallback_msg + err_hint)
                st.session_state.roleplay_history.append({"role": "model", "content": fallback_msg + err_hint})

        st.rerun()

    # ─── 4. 입력창은 항상 맨 마지막에 호출 → 화면 하단 고정, Thinking 중에도 움직이지 않음 ───
    if prompt := st.chat_input("메시지 입력..."):
        st.session_state.pending_prompt = prompt
        st.rerun()


def _inject_app_styles() -> None:
    """프리미엄 모바일 앱 스타일. CSS는 모두 <style> 내부에 넣어 화면에 텍스트로 노출되지 않음."""
    css = (
        "<link href='https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap' rel='stylesheet'>"
        "<style>"
        "*{font-family:'Noto Sans KR',sans-serif !important;letter-spacing:-0.02em;}"
        ".block-container{padding-top:1rem !important;padding-bottom:5rem !important;}"
        ".main .block-container{max-width:700px !important;margin:0 auto !important;position:relative !important;}"
        "header[data-testid='stHeader']{background:transparent !important;z-index:1;}"
        "[data-testid='stToolbar']{display:none !important;}"
        ".main{background-color:#F9FAFB !important;}"
        "section[data-testid='stSidebar']{background:#FFF !important;box-shadow:2px 0 16px rgba(0,0,0,0.04) !important;}"
        ".header-container{display:flex;align-items:center;background:#FFF !important;padding:0.85rem 1.2rem !important;border-radius:16px !important;margin-bottom:0.6rem !important;box-shadow:0 2px 16px rgba(0,0,0,0.06) !important;}"
        ".header-text{font-size:1.05rem !important;font-weight:600 !important;color:#111 !important;margin-left:0.75rem !important;line-height:1.5 !important;}"
        ".scenario-badge{display:inline-flex;align-items:center;background:#FFF;border-radius:999px;padding:0.5rem 1rem;box-shadow:0 2px 10px rgba(0,0,0,0.06);margin-bottom:0.5rem;font-size:0.9rem;color:#374151;}"
        ".scenario-emoji{font-size:1.2rem;margin-right:0.4rem;}"
        ".scenario-label{font-weight:500;line-height:1.5;}"
        ".main .block-container > div:not(:first-child){background:#FFF !important;border-radius:16px !important;padding:1.35rem !important;box-shadow:0 2px 16px rgba(0,0,0,0.06) !important;margin-bottom:1rem !important;}"
        ".daily-sentence-card{background:#FFF !important;border:1px solid #E5E7EB !important;border-radius:16px !important;padding:1rem 1.25rem !important;box-shadow:0 2px 10px rgba(0,0,0,0.04) !important;margin-bottom:0.5rem !important;}"
        ".daily-sentence-title{font-size:0.85rem !important;font-weight:600 !important;color:#6B7280 !important;margin-bottom:0.4rem !important;line-height:1.5 !important;}"
        ".daily-sentence-kr{font-size:1.2rem !important;font-weight:700 !important;color:#111 !important;line-height:1.6 !important;}"
        ".daily-sentence-roman{font-size:0.85rem !important;color:#6B7280 !important;margin-top:0.25rem !important;line-height:1.5 !important;}"
        ".daily-sentence-en{font-size:0.95rem !important;color:#374151 !important;margin-top:0.25rem !important;line-height:1.5 !important;}"
        ".slang-card{background:#FFF !important;border:1px solid #E5E7EB !important;border-radius:14px !important;padding:1rem 1.2rem !important;box-shadow:0 2px 10px rgba(0,0,0,0.04) !important;margin-bottom:0.75rem !important;}"
        ".slang-word{font-size:1.1rem !important;font-weight:700 !important;color:#111 !important;margin-bottom:0.35rem !important;line-height:1.5 !important;}"
        ".slang-meaning,.slang-usage{font-size:0.9rem !important;color:#374151 !important;line-height:1.65 !important;}"
        ".slang-usage{margin-top:0.25rem !important;}"
        "[data-testid='stChatMessage']{border-radius:20px !important;padding:0.75rem 1rem !important;box-shadow:0 1px 6px rgba(0,0,0,0.06) !important;}"
        "[data-testid='stChatMessage'] > div:last-child{border-radius:20px !important;padding:0.65rem 1rem !important;}"
        "div[data-testid='stChatMessage']{background:#F0F0F0 !important;color:#111 !important;}"
        "div[data-testid='stChatMessage']:nth-of-type(even){background:#007AFF !important;color:#FFF !important;}"
        "div[data-testid='stChatMessage']:nth-of-type(even) p,div[data-testid='stChatMessage']:nth-of-type(even) .stMarkdown{color:#FFF !important;}"
        "[data-testid='stTabs']{padding:0.5rem 0 1rem 0 !important;border-bottom:none !important;}"
        "[data-testid='stTabs'] button,[data-testid='stTabs'] [role='tab']{font-size:0.95rem !important;font-weight:600 !important;padding:0.65rem 1.1rem !important;border-radius:12px !important;color:#6B7280 !important;transition:all 0.2s ease !important;}"
        "[data-testid='stTabs'] button:hover,[data-testid='stTabs'] [role='tab']:hover{color:#111 !important;background:#F3F4F6 !important;}"
        "[data-testid='stTabs'] button[aria-selected='true'],[data-testid='stTabs'] [role='tab'][aria-selected='true'],div[data-baseweb='tab-list'] button[aria-selected='true']{font-weight:700 !important;background:#111 !important;color:#FFF !important;border-radius:12px !important;border:none !important;}"
        "button[kind='primary'],.stButton > button{border-radius:12px !important;transition:transform 0.15s ease,box-shadow 0.15s ease !important;}"
        "button[kind='primary']:hover,.stButton > button:hover{transform:scale(1.02);}"
        "footer,[data-testid='stManageAppButton'],[data-testid='stDecoration']{display:none !important;visibility:hidden !important;}"
        "footer a[href*='manage']{display:none !important;}"
        "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)


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
    st.set_page_config(page_title=APP_TITLE, page_icon="🇰🇷", layout="wide")
    init_state()
    _inject_hide_footer_early()
    # 상단 헤더: 선택된 시나리오에 따라 제목·설명이 동적으로 바뀜
    render_header(st.session_state.get("current_scenario", "restaurant"))
    # 테마 뱃지 (사진 없이 아이콘 + 상황 설명만)
    scenario_key = st.session_state.get("current_scenario", "restaurant")
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["restaurant"])
    emo = scenario.get("emoji", "🇰🇷")
    st.markdown(
        f'<div class="scenario-badge">'
        f'<span class="scenario-emoji">{emo}</span> '
        f'<span class="scenario-label">지금 당신은 <strong>{scenario["name"]}</strong> — {scenario["situation"]}에 있습니다.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.write("")
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

    sidebar_scenario()

    _inject_app_styles()

    tabs = st.tabs(["표현 익히기", "요즘 한국어 (K-Slang)", "AI와 역할놀이"])
    with tabs[0]:
        tab_menu_learn()
    with tabs[1]:
        tab_slang()
    with tabs[2]:
        tab_roleplay()


if __name__ == "__main__":
    main()