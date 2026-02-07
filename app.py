import streamlit as st
import folium
from streamlit_folium import st_folium
from dataclasses import dataclass
from typing import List
import html as html_lib

# --- 1. 데이터 구조 정의 ---
@dataclass
class Location:
    name: str
    lat: float
    lon: float
    time: str = ""
    note: str = ""
    icon: str = "info-sign"  # glyphicon: plane, home, cutlery, camera, star, user, road, flag, etc.
    color: str = "blue"      # blue, red, green, orange, purple, gray

@dataclass
class DailyPlan:
    day: int
    date: str
    locations: List[Location]

# --- 2. Andrew 사장님 가족 여행 일정 (5/4 ~ 5/21) ---
travel_plan = [
    DailyPlan(1, "5/4 (월) - KL 입국", [
        Location("KLIA 공항 도착", 2.7456, 101.7072, "오후", "가족 5명 입국 심사", "plane", "red"),
        Location("KL 시내 호텔", 3.1478, 101.7089, "Check-in", "숙소 이동 및 짐 풀기", "home", "green"),
        Location("부킷 빈탕", 3.1466, 101.7115, "저녁", "야경 감상 및 저녁 식사", "camera", "purple")
    ]),
    DailyPlan(2, "5/5 (화) - KL 투어", [
        Location("바투 동굴", 3.2379, 101.6840, "오전", "거대 황금 불상 관람", "camera", "blue"),
        Location("메르데카 광장", 3.1485, 101.6946, "오후", "역사 지구 산책", "camera", "blue"),
        Location("페트로나스 트윈 타워", 3.1579, 101.7116, "저녁", "KLCC 공원 및 랜드마크", "star", "orange")
    ]),
    DailyPlan(3, "5/6 (수) - 랑카위 이동", [
        Location("KL 호텔 체크아웃", 3.1478, 101.7089, "오전", "공항으로 이동", "home", "gray"),
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "✈️ 도착 & 렌터카 인수", "plane", "red"),
        Location("체낭 해변", 6.2917, 99.7287, "오후", "자유 시간 및 휴식", "tint", "blue")
    ]),
    DailyPlan(4, "5/7 (목) - 랑카위 관광", [
        Location("스카이캡 (케이블카)", 6.3711, 99.6716, "오전", "오리엔탈 빌리지 & 전망대", "cloud", "blue"),
        Location("선셋 요트 크루즈", 6.2917, 99.7287, "17:00", "🌅 가족 추천 코스 (석양)", "glass", "orange")
    ]),
    DailyPlan(5, "5/8 (금) - 랑카위 힐링", [
        Location("킬림 지질공원", 6.4056, 99.8569, "오전", "맹그로브 투어 (선택)", "tree-conifer", "green"),
        Location("탄중 루 해변", 6.4534, 99.8257, "오후", "북쪽 해변 힐링", "tint", "blue")
    ]),
    DailyPlan(6, "5/9 (토) - 다시 KL로", [
        Location("랑카위 공항", 6.3297, 99.7316, "12:30", "렌터카 반납 & KL행 비행기", "plane", "red"),
        Location("KLIA 인근 숙소", 2.7456, 101.7072, "오후", "공항 근처 숙박 (다음날 배웅)", "home", "green")
    ]),
    DailyPlan(7, "5/10 (일) - 아들 귀국 & 말라카", [
        Location("KLIA 공항", 2.7456, 101.7072, "오전", "👋 아들 1명 귀국 배웅", "user", "red"),
        Location("말라카 이동", 2.1954, 102.2466, "오후", "🚗 차로 1.5시간 이동 (4인 가족)", "road", "blue"),
        Location("존커 스트리트", 2.1954, 102.2466, "저녁", "야시장 투어", "cutlery", "orange")
    ]),
    DailyPlan(8, "5/11 (월) - 말라카 역사", [
        Location("네덜란드 광장", 2.1938, 102.2486, "오전", "붉은 벽돌 건물들", "camera", "blue"),
        Location("세인트 폴 교회", 2.1925, 102.2494, "오후", "유네스코 문화유산 탐방", "book", "blue"),
        Location("에이 파모사", 2.1917, 102.2505, "오후", "포르투갈 요새", "camera", "blue")
    ]),
    DailyPlan(9, "5/12 (화) - 말라카 여유", [
        Location("말라카 리버 크루즈", 2.1944, 102.2482, "오전", "강변 유람", "glass", "blue"),
        Location("트라이쇼 체험", 2.1938, 102.2486, "오후", "화려한 자전거 택시", "road", "purple"),
        Location("현지 맛집 투어", 2.1954, 102.2466, "저녁", "뇨냐 요리 등", "cutlery", "orange")
    ]),
    DailyPlan(10, "5/13 (수) - 이포 이동", [
        Location("말라카 출발", 2.1954, 102.2466, "오전", "🚗 장거리 이동 (3.5시간)", "road", "gray"),
        Location("이포 (Ipoh)", 4.5975, 101.0772, "오후", "미식의 도시 도착", "flag", "green"),
        Location("올드타운 화이트 커피", 4.5947, 101.0772, "오후", "본점 커피 체험", "cutlery", "orange")
    ]),
    DailyPlan(11, "5/14 (목) - 카메론 이동", [
        Location("이포 동굴 사원", 4.5630, 101.1187, "오전", "삼포통(Sam Poh Tong) 등", "camera", "blue"),
        Location("카메론 하일랜드", 4.4721, 101.3803, "오후", "🚗 고산지대 이동 (2시간)", "road", "green")
    ]),
    DailyPlan(12, "5/15 (금) - 카메론 힐링", [
        Location("BOH 티 플랜테이션", 4.5152, 101.4137, "오전", "차 밭 산책 & 티타임", "leaf", "green"),
        Location("딸기 농장", 4.4935, 101.3917, "오후", "부모님 힐링 코스", "gift", "red")
    ]),
    DailyPlan(13, "5/16 (토) - 페낭 이동", [
        Location("카메론 출발", 4.4721, 101.3803, "오전", "🚗 페낭으로 이동 (3시간)", "road", "gray"),
        Location("조지타운 벽화거리", 5.4144, 100.3364, "오후", "예술의 거리 탐방", "camera", "blue"),
        Location("조지타운 야경", 5.4164, 100.3327, "저녁", "미식과 예술", "star", "purple")
    ]),
    DailyPlan(14, "5/17 (일) - 페낭 관광", [
        Location("페낭 힐", 5.4085, 100.2770, "오전", "푸니쿨라 탑승 & 전망", "cloud", "green"),
        Location("켁록시 사원", 5.3995, 100.2736, "오후", "거대 불상과 사원", "camera", "blue"),
        Location("거니 드라이브", 5.4398, 100.3093, "저녁", "대형 야시장 먹거리", "cutlery", "orange")
    ]),
    DailyPlan(15, "5/18 (월) - 페낭 휴양", [
        Location("바투 페링기 해변", 5.4667, 100.2458, "종일", "해변 휴식 또는 카페 투어", "tint", "blue")
    ]),
    DailyPlan(16, "5/19 (화) - 페낭 쇼핑", [
        Location("조지타운", 5.4164, 100.3327, "오전", "마지막 명소 관람", "camera", "blue"),
        Location("로컬 쇼핑", 5.4144, 100.3364, "오후", "기념품 구매 등 여유", "gift", "purple")
    ]),
    DailyPlan(17, "5/20 (수) - KL 복귀", [
        Location("페낭 출발", 5.4164, 100.3327, "오전", "🚗 KL로 이동 (4시간)", "road", "gray"),
        Location("파빌리온 KL", 3.1489, 101.7133, "오후", "대형 쇼핑몰 & 마지막 밤", "shopping-cart", "orange")
    ]),
    DailyPlan(18, "5/21 (목) - 한국 귀국", [
        Location("호텔 체크아웃", 3.1478, 101.7089, "오전", "짐 정리", "home", "gray"),
        Location("KLIA 공항", 2.7456, 101.7072, "오후", "✈️ 출국 수속 및 귀국", "plane", "red")
    ])
]

# Folium 기본 아이콘(Glyphicon)에 없는 이름 매핑 (Bootstrap 3 glyphicon 기준)
ICON_MAP = {
    "ship": "glass", "bicycle": "road", "apple": "gift", "map-marker": "camera",
    "shopping-cart": "gift",
}
def get_icon(name: str) -> str:
    return ICON_MAP.get(name, name)

# --- 3. UI 및 지도 로직 ---
st.set_page_config(layout="wide", page_title="🇲🇾 Malaysia Family Trip 2026")

st.title("🇲🇾 2026 말레이시아 가족 여행 지도")
st.markdown("##### 🗓️ 2026.05.04 ~ 05.21 (17박 18일) | 👨‍👩‍👦‍👦 성인 5명 → 4명 (5/10부터)")

# 사이드바: 날짜 선택
with st.sidebar:
    st.header("📅 일정 선택")

    day_options = {f"Day {p.day} ({p.date})": p for p in travel_plan}
    selected_day_label = st.radio("날짜를 선택하세요:", list(day_options.keys()))
    selected_plan = day_options[selected_day_label]

    st.divider()
    st.subheader(f"📋 {selected_day_label}")
    for loc in selected_plan.locations:
        with st.expander(f"{loc.time} {loc.name}", expanded=True):
            st.write(loc.note if loc.note else "—")

# 지도 생성 (folium)
if selected_plan.locations:
    start_loc = selected_plan.locations[0]
    m = folium.Map(location=[start_loc.lat, start_loc.lon], zoom_start=11)

    route_coords = []

    for loc in selected_plan.locations:
        icon_name = get_icon(loc.icon)
        popup_html = f"<b>{html_lib.escape(loc.name)}</b><br>{loc.time}<br>{html_lib.escape(loc.note)}"
        folium.Marker(
            [loc.lat, loc.lon],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"[{loc.time}] {loc.name}",
            icon=folium.Icon(color=loc.color, icon=icon_name),
        ).add_to(m)
        route_coords.append([loc.lat, loc.lon])

    if len(route_coords) > 1:
        folium.PolyLine(
            route_coords,
            color="blue",
            weight=4,
            opacity=0.7,
            tooltip="이동 경로"
        ).add_to(m)

    # key: 날짜 변경 시 지도 컴포넌트를 새로 마운트 → removeChild 오류 방지
    st_folium(m, width="100%", height=600, key=f"travel_map_day_{selected_plan.day}")
else:
    st.warning("이 날짜에는 등록된 장소가 없습니다.")
