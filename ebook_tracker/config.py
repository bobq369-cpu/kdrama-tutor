"""서점별 설정 (Store configurations).

각 서점의 로그인 URL, 구매내역 URL, 그리고 데이터 추출에 사용하는
선택자(selector) 정보를 한 곳에 모아둡니다.

⚠️ 중요: 한국 서점들은 로그인 후에만 접근 가능한 영역이라, 아래 선택자/엔드포인트는
실제 로그인된 세션에서 한 번 확인(F12 → Network 탭)한 뒤 미세 조정이 필요할 수 있습니다.
sync.py 의 네트워크 캡처 기능이 실제 응답을 자동으로 기록해 주므로, 그 로그를 보고
`order_api_keywords` 와 선택자를 맞추면 됩니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StoreConfig:
    key: str                      # 내부 식별자 (kyobo, yes24, aladin)
    name: str                     # 화면에 표시할 이름
    color: str                    # UI 배지 색상
    login_url: str                # 로그인 페이지
    orders_url: str               # 구매/주문 내역 페이지
    # 로그인 성공을 감지할 때 사용하는 URL 조각 (이 중 하나라도 만나면 로그인 완료로 간주)
    login_success_markers: list[str] = field(default_factory=list)
    # 주문 내역을 JSON 으로 내려주는 API 응답을 식별할 키워드 (URL 에 포함된 문자열)
    order_api_keywords: list[str] = field(default_factory=list)
    # HTML 파싱이 필요할 때 쓰는 CSS 선택자 (API 가 없을 경우의 대비책)
    row_selector: str = ""
    title_selector: str = ""
    author_selector: str = ""
    date_selector: str = ""
    price_selector: str = ""


KYOBO = StoreConfig(
    key="kyobo",
    name="교보문고",
    color="#2E7D32",
    login_url="https://mmbr.kyobobook.co.kr/login",
    orders_url="https://mypage.kyobobook.co.kr/order/orderList",
    login_success_markers=["kyobobook.co.kr", "mypage", "main"],
    order_api_keywords=["order", "orderList", "purchase", "ebook", "myRoom"],
    row_selector="table tbody tr",
    title_selector=".title, .prod_name, a.tit",
    author_selector=".author, .prod_author",
    date_selector=".date, .order_date",
    price_selector=".price, .amount",
)

YES24 = StoreConfig(
    key="yes24",
    name="Yes24",
    color="#0B5FA5",
    login_url="https://www.yes24.com/Templates/FTLogin.aspx",
    orders_url="https://ssl.yes24.com/MyPage/MyOrderList",
    login_success_markers=["yes24.com", "MyPage", "Main"],
    order_api_keywords=["Order", "MyOrder", "ebook", "Purchase", "viewer"],
    row_selector="table tbody tr, .order_list li",
    title_selector=".goods_name, .gd_name, a.tit",
    author_selector=".goods_pubGrp, .author",
    date_selector=".order_date, .date",
    price_selector=".price, .sale_price",
)

ALADIN = StoreConfig(
    key="aladin",
    name="알라딘",
    color="#C2185B",
    login_url="https://www.aladin.co.kr/login/wlogin.aspx",
    orders_url="https://www.aladin.co.kr/order/oditemall.aspx",
    login_success_markers=["aladin.co.kr", "Order", "usermain"],
    order_api_keywords=["order", "oditem", "ebook", "myebook", "Purchase"],
    row_selector="table tbody tr, .order_box",
    title_selector=".bo3, .title, a.tit",
    author_selector=".author, .pub",
    date_selector=".date, .order_date",
    price_selector=".price, .amount",
)

STORES: dict[str, StoreConfig] = {
    KYOBO.key: KYOBO,
    YES24.key: YES24,
    ALADIN.key: ALADIN,
}


def get_store(key: str) -> StoreConfig:
    return STORES[key]


def store_choices() -> list[tuple[str, str]]:
    """(key, name) 목록 — UI 드롭다운용."""
    return [(s.key, s.name) for s in STORES.values()]
