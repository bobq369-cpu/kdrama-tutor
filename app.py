import streamlit as st
import time

# --- 1. 초기 설정 및 세션 상태 관리 ---
st.set_page_config(layout="wide", page_title="K-Tutor Global")

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_scenario" not in st.session_state:
    st.session_state.selected_scenario = None

# --- 2. CSS 스타일링 (스크린샷 디자인 구현 핵심) ---
# Streamlit 기본 버튼을 '카드' 형태로 변형시키는 CSS입니다.
st.markdown("""
<style>
    /* 전체 배경색 조정 (선택사항, 스크린샷의 밝은 배경) */
    .stApp {
        background-color: #FAFAFA;
    }

    /* 메인 타이틀 스타일 */
    .main-title {
        font-size: 3rem !important;
        font-weight: 700 !important;
        color: #4A4A4A !important;
        text-align: center;
        margin-bottom: 3rem !important;
        padding-top: 2rem;
    }

    /* 버튼(카드) 스타일 커스터마이징 */
    /* Streamlit의 st.button은 div.stButton > button 구조를 가집니다 */
    div.stButton > button {
        width: 100%;
        height: auto;
        min-height: 200px; /* 카드 높이 확보 */
        background-color: white;
        color: #31333F;
        border: 1px solid #E5E7EB;
        border-radius: 20px; /* 둥근 모서리 */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* 그림자 */
        padding: 30px;
        text-align: left; /* 텍스트 왼쪽 정렬 */
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        transition: all 0.3s ease; /* 호버 애니메이션 */
        white-space: pre-wrap; /* 줄바꿈 허용 */
    }

    /* 버튼 호버 효과 (마우스 올렸을 때 살짝 떠오름) */
    div.stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: #3B82F6; /* 호버 시 테두리 색상 변경 (옵션) */
        color: #31333F; /* 글자색 유지 */
    }
    
    /* 버튼 내부 텍스트 스타일 조정 */
    div.stButton > button p {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 데이터 (시나리오 정보) ---
scenarios = [
    {
        "id": "airport",
        "icon": "✈️",
        "title": "공항 입국 심사 (Airport Immigration)",
        "desc": "사용자가 한국에 막 도착해서 입국 심사를 받고 있습니다."
    },
    {
        "id": "restaurant",
        "icon": "🍜",
        "title": "식당 주문하기 (Ordering at a Restaurant)",
        "desc": "사용자가 식당에 들어와서 메뉴를 고르고 주문을 하려고 합니다."
    },
    {
        "id": "market",
        "icon": "🍎",
        "title": "전통시장 쇼핑 (Traditional Market Shopping)",
        "desc": "사용자가 활기찬 시장에서 물건을 구경하고 가격을 물어봅니다."
    }
]

# --- 4. 화면 로직 함수 ---

def go_home():
    st.session_state.page = "home"
    st.session_state.selected_scenario = None
    st.rerun()

def start_chat(scenario_id):
    st.session_state.page = "chat"
    st.session_state.selected_scenario = scenario_id
    st.rerun()

def render_home():
    # 타이틀 출력 (커스텀 CSS 클래스 적용)
    st.markdown('<h1 class="main-title">오늘 어디서 연습할까요?</h1>', unsafe_allow_html=True)

    # 그리드 레이아웃 생성 (2열)
    # 화면 크기에 따라 반응형으로 동작하도록 Streamlit 컬럼 사용
    # 스크린샷처럼 2열 배치를 위해 col1, col2 생성 후 인덱스로 분배
    cols = st.columns(2)
    
    for idx, scenario in enumerate(scenarios):
        # 짝수/홀수 인덱스에 따라 컬럼 배정
        col = cols[idx % 2]
        
        with col:
            # 버튼 텍스트 구성: 아이콘 + 제목 + (줄바꿈) + 설명
            # \n\n을 사용하여 제목과 설명 사이에 공백을 둠
            label = f"{scenario['icon']} {scenario['title']}\n\n{scenario['desc']}"
            
            # 버튼 생성 (CSS에 의해 카드로 변신)
            if st.button(label, key=f"btn_{scenario['id']}"):
                start_chat(scenario["id"])

def render_chat():
    # (기존 기능 유지) 채팅 화면 예시
    scenario = next((s for s in scenarios if s["id"] == st.session_state.selected_scenario), None)
    
    # 상단 네비게이션
    with st.container():
        c1, c2 = st.columns([1, 10])
        with c1:
            if st.button("← 뒤로"):
                go_home()
        with c2:
            st.subheader(f"{scenario['icon']} {scenario['title']}")
    
    st.divider()
    
    # 채팅 영역 (플레이스홀더)
    st.info(f"'{scenario['title']}' 상황에서 AI 튜터와 대화를 시작합니다.\n\n(여기에 채팅 UI, 교정 기능, TTS 플레이어가 들어갑니다.)")
    
    # 입력창 (UI 확인용)
    st.chat_input("한국어로 대화해 보세요...")

# --- 5. 메인 실행 로직 ---
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "chat":
    render_chat()
