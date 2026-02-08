import streamlit as st
import folium
from streamlit_folium import st_folium
from dataclasses import dataclass
from typing import List
import html as html_lib

# --- 1. 설정 및 스타일링 ---
st.set_page_config(layout="wide", page_title="Malaysia Trip 2026 Dashboard")

st.markdown("""
    <style>
    .timeline-card {
        padding: 15px;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin-bottom: 10px;
        border-left: 5px solid #4B8BBE;
    }
    .timeline-time { font-weight: bold; color: #4B8BBE; font-size: 0.9em; }
    .timeline-title { font-size: 1.1em; font-weight: bold; margin: 5px 0; }
    .timeline-note { font-size: 0.9em; color: #555; }
    div.stButton > button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 구조 및 데이터 ---
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

# Folium Glyphicon에 없는 아이콘 이름 매핑
ICON_MAP = {
    "car": "road", "ship": "glass", "bicycle": "road", "apple": "gift",
    "map-marker": "camera", "shopping-cart": "gift", "tree": "tree-conifer",
}

def get_icon(name: str) -> str:
    return ICON_MAP.get(name, name)

travel_plan = [
    DailyPlan(1, "5/4 (월)", "KL (쿠알라룸푸르)", [
        Location("KLIA 공항 도착", 2.7456, 101.7072, "14:00", "가족 5명 입국 심사", "plane", "red"),
        Location("KL 시내 호텔", 3.1478, 101.7089, "16:00", "체크인 & 짐 풀기", "home", "green"),
        Location("부킷 빈탕", 3.1466, 101.7115, "19:00", "야경 & 저녁 식사", "camera", "purple")
    ]),
    DailyPlan(2, "5/5 (화)", "KL (쿠알라룸푸르)", [
        Location("바투 동굴", 3.2379, 101.6840, "10:00", "거대 황금 불상", "camera", "blue"),
        Location("메르데카 광장", 3.1485, 101.6946, "14:00", "역사 지구 산책", "camera", "blue"),
        Location("페트로나스 트윈 타워", 3.1579, 101.7116, "19:00", "KLCC 공원 야경", "star", "orange")
    ]),
    DailyPlan(3, "5/6 (수)", "Langkawi (랑카위)", [
        Location("KL 공항 이동", 3.1478, 101.7089, "09:00", "체크아웃", "home", "gray"),
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "도착 & 렌터카 인수", "plane", "red"),
        Location("체낭 해변", 6.2917, 99.7287, "16:00", "자유 시간", "tint", "blue")
    ]),
    DailyPlan(4, "5/7 (목)", "Langkawi (랑카위)", [
        Location("스카이캡 (케이블카)", 6.3711, 99.6716, "10:00", "전망대 관람", "cloud", "blue"),
        Location("선셋 요트 크루즈", 6.2917, 99.7287, "17:00", "가족 추천 코스", "glass", "orange")
    ]),
    DailyPlan(5, "5/8 (금)", "Langkawi (랑카위)", [
        Location("킬림 지질공원", 6.4056, 99.8569, "10:00", "맹그로브 투어", "tree-conifer", "green"),
        Location("탄중 루 해변", 6.4534, 99.8257, "15:00", "북쪽 해변 힐링", "tint", "blue")
    ]),
    DailyPlan(6, "5/9 (토)", "Langkawi -> KL", [
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "렌터카 반납 & 출국", "plane", "red"),
        Location("KLIA 인근 숙소", 2.7456, 101.7072, "16:00", "공항 근처 숙박", "home", "green")
    ]),
    DailyPlan(7, "5/10 (일)", "KL -> Malacca", [
        Location("KLIA 공항", 2.7456, 101.7072, "10:00", "👋 아들 1명 귀국 배웅", "user", "red"),
        Location("말라카 이동", 2.1954, 102.2466, "14:00", "차로 1.5시간 이동", "road", "blue"),
        Location("존커 스트리트", 2.1954, 102.2466, "19:00", "야시장 투어", "cutlery", "orange")
    ]),
    DailyPlan(8, "5/11 (월)", "Malacca (말라카)", [
        Location("네덜란드 광장", 2.1938, 102.2486, "10:00", "붉은 벽돌 건물", "camera", "blue"),
        Location("세인트 폴 교회", 2.1925, 102.2494, "14:00", "유적지 탐방", "book", "blue"),
        Location("에이 파모사", 2.1917, 102.2505, "16:00", "요새 관람", "camera", "blue")
    ]),
    DailyPlan(9, "5/12 (화)", "Malacca (말라카)", [
        Location("리버 크루즈", 2.1944, 102.2482, "10:00", "강변 유람", "glass", "blue"),
        Location("트라이쇼 체험", 2.1938, 102.2486, "14:00", "자전거 택시", "road", "purple"),
        Location("맛집 투어", 2.1954, 102.2466, "18:00", "뇨냐 요리", "cutlery", "orange")
    ]),
    DailyPlan(10, "5/13 (수)", "Ipoh (이포)", [
        Location("말라카 출발", 2.1954, 102.2466, "09:00", "장거리 이동 (3.5h)", "road", "gray"),
        Location("이포 도착", 4.5975, 101.0772, "13:00", "미식의 도시", "flag", "green"),
        Location("올드타운 화이트커피", 4.5947, 101.0772, "15:00", "본점 방문", "cutlery", "orange")
    ]),
    DailyPlan(11, "5/14 (목)", "Cameron (카메론)", [
        Location("이포 동굴 사원", 4.5630, 101.1187, "10:00", "삼포통 관람", "camera", "blue"),
        Location("카메론 하일랜드", 4.4721, 101.3803, "15:00", "고산지대 이동 (2h)", "road", "green")
    ]),
    DailyPlan(12, "5/15 (금)", "Cameron (카메론)", [
        Location("BOH 티 밭", 4.5152, 101.4137, "10:00", "차 밭 산책", "leaf", "green"),
        Location("딸기 농장", 4.4935, 101.3917, "14:00", "체험 활동", "gift", "red")
    ]),
    DailyPlan(13, "5/16 (토)", "Penang (페낭)", [
        Location("카메론 출발", 4.4721, 101.3803, "09:00", "페낭 이동 (3h)", "road", "gray"),
        Location("조지타운 벽화", 5.4144, 100.3364, "15:00", "예술 거리", "camera", "blue"),
        Location("조지타운 야경", 5.4164, 100.3327, "19:00", "야시장 & 미식", "star", "purple")
    ]),
    DailyPlan(14, "5/17 (일)", "Penang (페낭)", [
        Location("페낭 힐", 5.4085, 100.2770, "09:00", "푸니쿨라 전망대", "cloud", "green"),
        Location("켁록시 사원", 5.3995, 100.2736, "14:00", "거대 불상", "camera", "blue"),
        Location("거니 드라이브", 5.4398, 100.3093, "19:00", "대형 야시장", "cutlery", "orange")
    ]),
    DailyPlan(15, "5/18 (월)", "Penang (페낭)", [
        Location("바투 페링기", 5.4667, 100.2458, "11:00", "해변 휴식 & 카페", "tint", "blue")
    ]),
    DailyPlan(16, "5/19 (화)", "Penang (페낭)", [
        Location("조지타운", 5.4164, 100.3327, "10:00", "마지막 명소 관람", "camera", "blue"),
        Location("로컬 쇼핑", 5.4144, 100.3364, "14:00", "기념품 구매", "gift", "purple")
    ]),
    DailyPlan(17, "5/20 (수)", "KL (쿠알라룸푸르)", [
        Location("페낭 출발", 5.4164, 100.3327, "09:00", "KL 이동 (4h)", "road", "gray"),
        Location("파빌리온 KL", 3.1489, 101.7133, "16:00", "쇼핑 & 마지막 밤", "gift", "orange")
    ]),
    DailyPlan(18, "5/21 (목)", "Departure", [
        Location("체크아웃", 3.1478, 101.7089, "11:00", "짐 정리", "home", "gray"),
        Location("KLIA 공항", 2.7456, 101.7072, "14:00", "✈️ 출국 수속", "plane", "red")
    ])
]

# --- 3. 메인 로직 ---
st.title("🇲🇾 Malaysia Trip 2026")

days_list = [f"Day {p.day} ({p.date})" for p in travel_plan]
selected_day_idx = st.select_slider(
    "일정을 선택하세요",
    options=range(len(travel_plan)),
    value=0,
    format_func=lambda x: days_list[x]
)

selected_plan = travel_plan[selected_day_idx]
st.markdown(f"### 📍 {selected_plan.region}")

col_map, col_details = st.columns([6.5, 3.5])

with col_map:
    if selected_plan.locations:
        start_loc = selected_plan.locations[0]
        m = folium.Map(location=[start_loc.lat, start_loc.lon], zoom_start=12)
        route_coords = []
        for loc in selected_plan.locations:
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
            folium.PolyLine(route_coords, color="#3388ff", weight=5, opacity=0.7).add_to(m)
        st_folium(m, width="100%", height=600, key=f"travel_map_day_{selected_plan.day}")
    else:
        st.info("이 날짜에는 표시할 위치 정보가 없습니다.")

with col_details:
    st.subheader(f"📅 {selected_plan.date}")
    st.divider()
    for loc in selected_plan.locations:
        safe_name = html_lib.escape(loc.name)
        safe_note = html_lib.escape(loc.note) if loc.note else "—"
        st.markdown(f"""
        <div class="timeline-card">
            <div class="timeline-time">⏰ {html_lib.escape(loc.time)}</div>
            <div class="timeline-title">{safe_name}</div>
            <div class="timeline-note">{safe_note}</div>
        </div>
        """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 옵션")
    show_all = st.checkbox("전체 경로 한눈에 보기")
    if show_all:
        st.info("전체 18일간의 여정을 지도에 표시합니다.")
        m_all = folium.Map(location=[4.2105, 101.9758], zoom_start=7)
        for plan in travel_plan:
            for loc in plan.locations:
                folium.CircleMarker(
                    location=[loc.lat, loc.lon],
                    radius=5,
                    color="red",
                    fill=True,
                    popup=f"Day {plan.day}: {html_lib.escape(loc.name)}"
                ).add_to(m_all)
        st_folium(m_all, width="100%", height=400, key="travel_map_all")
