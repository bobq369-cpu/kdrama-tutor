import streamlit as st
import folium
from streamlit_folium import st_folium
from dataclasses import dataclass
from typing import List
import pandas as pd
import html as html_lib

# --- 1. 설정 및 스타일링 ---
st.set_page_config(layout="wide", page_title="Malaysia Trip 2026")

st.markdown("""
    <style>
    .timeline-card {
        padding: 15px; border-radius: 10px; background-color: #f8f9fa;
        margin-bottom: 10px; border-left: 5px solid #FF4B4B;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .timeline-time { font-weight: bold; color: #FF4B4B; font-size: 0.9em; }
    .timeline-title { font-size: 1.1em; font-weight: bold; margin: 5px 0; color: #333; }
    .timeline-note { font-size: 0.9em; color: #666; }
    .day-header {
        font-size: 1.5em; font-weight: bold; text-align: center; color: #1E1E1E;
        padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;
    }
    div.stButton > button { width: 100%; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 구조 및 상세 데이터 ---
@dataclass
class Location:
    name: str
    lat: float
    lon: float
    time: str = ""
    note: str = ""
    icon: str = "info-sign"
    color: str = "blue"

@dataclass
class DailyPlan:
    day: int
    date: str
    region: str
    locations: List[Location]
    summary: str = ""

ICON_MAP = {
    "car": "road", "ship": "glass", "bicycle": "road", "apple": "gift",
    "map-marker": "camera", "shopping-cart": "gift", "tree": "tree-conifer",
    "coffee": "glass", "heart": "heart",
}

def get_icon(name: str) -> str:
    return ICON_MAP.get(name, name)

travel_plan = [
    DailyPlan(1, "5/4 (월)", "KL (쿠알라룸푸르)", [
        Location("KLIA 공항 도착", 2.7456, 101.7072, "오후", "입국 및 호텔 이동", "plane", "red"),
        Location("KL 호텔 (체크인)", 3.1478, 101.7089, "16:00", "짐 풀기", "home", "green"),
        Location("부킷 빈탕", 3.1466, 101.7115, "저녁", "야경 감상 및 현지식", "camera", "purple")
    ], "쿠알라룸푸르 도착 및 야경"),
    DailyPlan(2, "5/5 (화)", "KL (쿠알라룸푸르)", [
        Location("바투 동굴", 3.2379, 101.6840, "오전", "힌두 사원 (272 계단)", "camera", "blue"),
        Location("메르데카 광장", 3.1485, 101.6946, "오후", "독립 광장 역사 탐방", "flag", "blue"),
        Location("페트로나스 트윈 타워", 3.1579, 101.7116, "저녁", "KLCC 공원 관람", "star", "orange")
    ], "KL 핵심 랜드마크 투어"),
    DailyPlan(3, "5/6 (수)", "Langkawi (랑카위)", [
        Location("KL 호텔 체크아웃", 3.1478, 101.7089, "오전", "공항 이동", "home", "gray"),
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "✈️ 도착 & 렌터카 인수", "plane", "red"),
        Location("체낭 해변", 6.2917, 99.7287, "오후", "자유 시간 & 휴식", "tint", "blue")
    ], "국내선 이동 및 랑카위 도착"),
    DailyPlan(4, "5/7 (목)", "Langkawi (랑카위)", [
        Location("스카이캡 (케이블카)", 6.3711, 99.6716, "오전", "스카이 브리지 체험", "cloud", "blue"),
        Location("선셋 요트 크루즈", 6.2917, 99.7287, "17:00", "🌅 가족 추천 코스", "glass", "orange")
    ], "랑카위 섬 투어 (케이블카/요트)"),
    DailyPlan(5, "5/8 (금)", "Langkawi (랑카위)", [
        Location("맹그로브 투어/탄중루", 6.4056, 99.8569, "오전", "자연 생태 관찰 or 해변", "tree-conifer", "green"),
        Location("탄중 루 해변", 6.4534, 99.8257, "오후", "한적한 북쪽 해변 힐링", "tint", "blue")
    ], "자연 체험 및 힐링"),
    DailyPlan(6, "5/9 (토)", "Langkawi -> KL", [
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "렌터카 반납 & KL행", "plane", "red"),
        Location("KLIA 인근 숙소", 2.7456, 101.7072, "오후", "공항 근처 숙박 (내일 배웅)", "home", "green")
    ], "KL 복귀 (공항 근처 숙박)"),
    DailyPlan(7, "5/10 (일)", "KL -> Malacca", [
        Location("KLIA 공항", 2.7456, 101.7072, "오전", "👋 아들 1명 귀국 배웅", "user", "red"),
        Location("말라카 이동", 2.1954, 102.2466, "오후", "🚗 렌터카 이동 (1.5시간)", "road", "blue"),
        Location("존커 스트리트", 2.1954, 102.2466, "저녁", "야시장 & 현지식", "cutlery", "orange")
    ], "아들 배웅 후 말라카 이동"),
    DailyPlan(8, "5/11 (월)", "Malacca (말라카)", [
        Location("네덜란드 광장", 2.1938, 102.2486, "오전", "붉은 건물 (더치 스퀘어)", "camera", "blue"),
        Location("세인트 폴 교회", 2.1925, 102.2494, "오후", "언덕 위 유적지", "book", "blue"),
        Location("에이 파모사", 2.1917, 102.2505, "오후", "포르투갈 요새", "camera", "blue")
    ], "말라카 역사 지구 탐방"),
    DailyPlan(9, "5/12 (화)", "Malacca (말라카)", [
        Location("리버 크루즈", 2.1944, 102.2482, "오전", "강변 유람", "glass", "blue"),
        Location("트라이쇼", 2.1938, 102.2486, "오후", "자전거 인력거 체험", "road", "purple"),
        Location("맛집 투어", 2.1954, 102.2466, "저녁", "치킨 라이스 볼 등", "cutlery", "orange")
    ], "말라카 여유 일정"),
    DailyPlan(10, "5/13 (수)", "Malacca -> Ipoh", [
        Location("말라카 출발", 2.1954, 102.2466, "오전", "🚗 이포로 이동 (3.5시간)", "road", "gray"),
        Location("올드타운 화이트커피", 4.5947, 101.0772, "오후", "본점 체험", "cutlery", "orange"),
        Location("이포 맛집", 4.5975, 101.0772, "저녁", "타우거, 이포 호펀", "cutlery", "orange")
    ], "미식의 도시 이포 이동"),
    DailyPlan(11, "5/14 (목)", "Ipoh -> Cameron", [
        Location("이포 동굴 사원", 4.5630, 101.1187, "오전", "삼포통 관람", "camera", "blue"),
        Location("카메론 하이랜드", 4.4721, 101.3803, "오후", "🚗 고산지대 이동 (2시간)", "road", "green"),
        Location("호텔 휴식", 4.4721, 101.3803, "저녁", "시원한 기후 만끽", "home", "green")
    ], "카메론 하이랜드 이동"),
    DailyPlan(12, "5/15 (금)", "Cameron (카메론)", [
        Location("BOH 차 농장", 4.5152, 101.4137, "오전", "차 밭 산책 & 티타임", "leaf", "green"),
        Location("딸기 농장", 4.4935, 101.3917, "오후", "체험 활동", "gift", "red")
    ], "카메론 자연 힐링"),
    DailyPlan(13, "5/16 (토)", "Cameron -> Penang", [
        Location("카메론 출발", 4.4721, 101.3803, "오전", "🚗 페낭 이동 (3시간)", "road", "gray"),
        Location("벽화 거리", 5.4144, 100.3364, "오후", "아르메니아 스트리트", "camera", "blue"),
        Location("조지타운 야경", 5.4164, 100.3327, "저녁", "호커센터 식사", "star", "purple")
    ], "페낭 조지타운 이동"),
    DailyPlan(14, "5/17 (일)", "Penang (페낭)", [
        Location("페낭 힐", 5.4085, 100.2770, "오전", "푸니쿨라 전망대", "cloud", "green"),
        Location("켁 록 시 사원", 5.3995, 100.2736, "오후", "최대 불교 사원", "camera", "blue"),
        Location("거니 드라이브", 5.4398, 100.3093, "저녁", "야시장 먹거리", "cutlery", "orange")
    ], "페낭 명소 투어"),
    DailyPlan(15, "5/18 (월)", "Penang (페낭)", [
        Location("바투 페링기", 5.4667, 100.2458, "선택", "해변 휴양 & 수상 스포츠", "tint", "blue"),
        Location("카페 투어", 5.4164, 100.3327, "선택", "조지타운 감성 카페", "glass", "purple")
    ], "페낭 해변 휴양"),
    DailyPlan(16, "5/19 (화)", "Penang (페낭)", [
        Location("마지막 명소", 5.4204, 100.3439, "오전", "코른월리스 요새 등", "camera", "blue"),
        Location("로컬 쇼핑", 5.4144, 100.3364, "오후", "기념품 구매", "gift", "purple"),
        Location("맛집 재방문", 5.4164, 100.3327, "저녁", "좋아했던 음식", "heart", "red")
    ], "페낭 마지막 날"),
    DailyPlan(17, "5/20 (수)", "Penang -> KL", [
        Location("페낭 출발", 5.4164, 100.3327, "오전", "🚗 KL 이동 (4시간)", "road", "gray"),
        Location("렌터카 반납", 3.1478, 101.7089, "오후", "호텔 체크인", "home", "green"),
        Location("파빌리온 KL", 3.1489, 101.7133, "저녁", "마지막 쇼핑", "gift", "orange")
    ], "쿠알라룸푸르 복귀"),
    DailyPlan(18, "5/21 (목)", "Departure", [
        Location("호텔 체크아웃", 3.1478, 101.7089, "오전", "공항 이동", "home", "gray"),
        Location("KLIA 공항", 2.7456, 101.7072, "저녁", "✈️ 한국행 출국", "plane", "red")
    ], "여행 종료"),
]

# --- 3. 메인 로직 ---
st.title("🇲🇾 Malaysia Family Trip 2026")

with st.sidebar:
    st.header("메뉴 선택")
    view_mode = st.radio("보기 방식", ["🗺️ 지도 대시보드", "📄 전체 일정표 보기"])
    st.divider()
    st.caption(f"총 {len(travel_plan)}일간의 여정")

# ---------------- [모드 1] 지도 대시보드 ----------------
if view_mode == "🗺️ 지도 대시보드":
    if "day_index" not in st.session_state:
        st.session_state.day_index = 0
    if "day_select_idx" not in st.session_state:
        st.session_state.day_select_idx = 0

    def next_day():
        if st.session_state.day_index < len(travel_plan) - 1:
            st.session_state.day_index += 1
            st.session_state.day_select_idx = st.session_state.day_index

    def prev_day():
        if st.session_state.day_index > 0:
            st.session_state.day_index -= 1
            st.session_state.day_select_idx = st.session_state.day_index

    def jump_to_day():
        st.session_state.day_index = st.session_state.day_select_idx

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        st.button("◀ 이전", on_click=prev_day, use_container_width=True)
    with col_info:
        current_plan = travel_plan[st.session_state.day_index]
        st.markdown(f"""
            <div class="day-header">
                Day {current_plan.day}<br>
                <span style="font-size: 0.6em; color: #555;">{html_lib.escape(current_plan.date)} | {html_lib.escape(current_plan.region)}</span>
            </div>
        """, unsafe_allow_html=True)
        st.progress((st.session_state.day_index + 1) / len(travel_plan))
    with col_next:
        st.button("다음 ▶", on_click=next_day, use_container_width=True)

    with st.expander("📅 날짜 바로 이동하기"):
        st.selectbox(
            "날짜 선택",
            options=range(len(travel_plan)),
            format_func=lambda i: f"Day {travel_plan[i].day} ({travel_plan[i].date}) - {travel_plan[i].region}",
            index=st.session_state.day_index,
            key="day_select_idx",
            on_change=jump_to_day,
        )

    st.divider()
    col_map, col_details = st.columns([6.5, 3.5])

    with col_map:
        if current_plan.locations:
            start_loc = current_plan.locations[0]
            m = folium.Map(location=[start_loc.lat, start_loc.lon], zoom_start=12)
            route_coords = []
            for loc in current_plan.locations:
                icon_name = get_icon(loc.icon)
                popup_html = f"<b>{html_lib.escape(loc.name)}</b><br>{html_lib.escape(loc.note)}"
                folium.Marker(
                    [loc.lat, loc.lon],
                    popup=folium.Popup(popup_html, max_width=280),
                    tooltip=f"[{loc.time}] {loc.name}",
                    icon=folium.Icon(color=loc.color, icon=icon_name),
                ).add_to(m)
                route_coords.append([loc.lat, loc.lon])
            if len(route_coords) > 1:
                folium.PolyLine(route_coords, color="#FF4B4B", weight=5, opacity=0.7).add_to(m)
            st_folium(m, width="100%", height=600, key=f"travel_map_day_{current_plan.day}")
        else:
            st.info("위치 정보 없음")

    with col_details:
        st.subheader("📋 오늘의 일정")
        for loc in current_plan.locations:
            safe_time = html_lib.escape(loc.time)
            safe_name = html_lib.escape(loc.name)
            safe_note = html_lib.escape(loc.note) if loc.note else "—"
            st.markdown(f"""
            <div class="timeline-card">
                <div class="timeline-time">⏰ {safe_time}</div>
                <div class="timeline-title">{safe_name}</div>
                <div class="timeline-note">{safe_note}</div>
            </div>
            """, unsafe_allow_html=True)

    with st.sidebar:
        if st.checkbox("전체 경로 지도 보기", key="sidebar_full_map"):
            st.info("전체 18일간의 여정")
            m_all = folium.Map(location=[4.2105, 101.9758], zoom_start=7)
            for plan in travel_plan:
                for loc in plan.locations:
                    folium.CircleMarker(
                        location=[loc.lat, loc.lon],
                        radius=3,
                        color="blue",
                        fill=True,
                        popup=f"Day {plan.day}: {html_lib.escape(loc.name)}"
                    ).add_to(m_all)
            st_folium(m_all, width="100%", height=400, key="travel_map_all")

# ---------------- [모드 2] 전체 일정표 ----------------
else:
    st.header("📄 전체 여행 일정표")
    st.markdown("#### 2026.05.04 ~ 05.21 (18일간) | 부모님 + 아들 3명")

    st.subheader("1. 여행 루트 개요")
    summary_data = {
        "구간": ["5/6", "5/9", "5/10", "5/13", "5/14", "5/16", "5/20"],
        "이동 경로": ["KL → 랑카위", "랑카위 → KLIA", "공항 → 말라카", "말라카 → 이포", "이포 → 카메론", "카메론 → 페낭", "페낭 → KL"],
        "교통편": ["✈️ 국내선 (1h)", "✈️ 국내선 (1h)", "🚗 렌터카 (1.5h)", "🚗 렌터카 (3.5h)", "🚗 렌터카 (2h)", "🚗 렌터카 (3h)", "🚗 렌터카 (4h)"]
    }
    st.table(pd.DataFrame(summary_data))

    st.subheader("2. 상세 일정")
    for plan in travel_plan:
        with st.expander(f"Day {plan.day} | {plan.date} - {plan.region}", expanded=False):
            st.info(f"💡 요약: {plan.summary}")
            for loc in plan.locations:
                st.write(f"- **[{loc.time}]** {loc.name}: {loc.note}")

    st.divider()
    st.subheader("✅ 여행 준비 체크리스트")
    col_check1, col_check2 = st.columns(2)
    with col_check1:
        st.markdown("""
        **🚗 렌터카/교통**
        - [ ] 국제 운전 면허증 필수 지참
        - [ ] 랑카위 렌터카 (5/6~5/9) 확인
        - [ ] 본토 렌터카 (5/10~5/20) 확인
        - [ ] Grab 앱 설치 및 카드 등록
        """)
    with col_check2:
        st.markdown("""
        **🎒 필수 준비물**
        - [ ] 여권 (유효기간 6개월 이상)
        - [ ] 항공권/호텔 바우처 출력
        - [ ] 멀미약 (카메론/페낭 이동 대비)
        - [ ] 긴팔 옷 (모스크/에어컨 대비)
        """)
