"""Playwright 기반 자동 동기화.

설계 원칙
=========
1. **비밀번호를 저장하지 않습니다.** 보이는 브라우저 창을 열어 사용자가 직접 로그인하고,
   OTP/2단계 인증도 평소처럼 처리합니다. 앱은 로그인 결과(세션 쿠키)만 파일로 보관합니다.
2. **첫 로그인 이후엔 클릭 한 번.** 저장된 세션을 다시 불러와 자동으로 구매내역을 가져옵니다.
3. **네트워크 응답 자동 캡처.** 구매내역 페이지가 부르는 JSON(API) 응답을 가로채서
   책 정보를 찾아냅니다. 실패 시 HTML 파싱으로 대비합니다.

세션 파일은 `sessions/<store>.json` 에 저장됩니다 (Playwright storage_state 형식).

⚠️ Playwright 가 설치되어 있어야 합니다:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .config import StoreConfig, get_store
from .paths import user_data_dir

SESSION_DIR = user_data_dir() / "sessions"
CAPTURE_DIR = user_data_dir() / "captures"

# 브라우저 채널 우선순위: 지인 PC에 이미 있는 Chrome → Edge(Windows 기본) → 번들 Chromium
BROWSER_CHANNELS = ["chrome", "msedge"]


def _ensure_dirs() -> None:
    SESSION_DIR.mkdir(exist_ok=True)
    CAPTURE_DIR.mkdir(exist_ok=True)


def session_path(store: str) -> Path:
    return SESSION_DIR / f"{store}.json"


def has_session(store: str) -> bool:
    return session_path(store).exists()


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# JSON 응답에서 책 정보를 뽑아내는 휴리스틱
# ---------------------------------------------------------------------------

# 책 제목/저자/가격으로 보이는 키 후보
_TITLE_KEYS = {"title", "prodname", "productname", "goodsname", "booktitle",
               "name", "cmdtname", "barcodeName".lower()}
_AUTHOR_KEYS = {"author", "writer", "authorname", "person"}
_PRICE_KEYS = {"price", "amount", "saleprice", "paidamount", "salePrice".lower(),
               "ordamt", "payamt"}
_DATE_KEYS = {"date", "orderdate", "purchasedate", " orderdt".strip(), "regdate",
              "paymentdate", "orddt"}
_ID_KEYS = {"orderid", "orderno", "ordernumber", "ordno"}
_PRODID_KEYS = {"productid", "prodid", "goodsno", "barcode", "isbn", "salecmdtid"}


def _norm_key(k: str) -> str:
    return re.sub(r"[_\s]", "", str(k)).lower()


def _find_book_dicts(data: Any, depth: int = 0) -> list[dict]:
    """중첩된 JSON 구조에서 '제목처럼 보이는 키'를 가진 dict 들을 수집."""
    found: list[dict] = []
    if depth > 8:
        return found
    if isinstance(data, dict):
        keys = {_norm_key(k) for k in data.keys()}
        if keys & _TITLE_KEYS:
            found.append(data)
        for v in data.values():
            found.extend(_find_book_dicts(v, depth + 1))
    elif isinstance(data, list):
        for item in data:
            found.extend(_find_book_dicts(item, depth + 1))
    return found


def _pick(d: dict, key_set: set[str]) -> Optional[Any]:
    for k, v in d.items():
        if _norm_key(k) in key_set:
            return v
    return None


def _to_record(d: dict, store: str) -> Optional[dict[str, Any]]:
    title = _pick(d, _TITLE_KEYS)
    if not title:
        return None
    title = str(title).strip()
    if not title or title.lower() in {"none", "null"}:
        return None

    price_raw = _pick(d, _PRICE_KEYS)
    price = None
    if price_raw is not None:
        digits = re.sub(r"[^\d]", "", str(price_raw))
        price = int(digits) if digits else None

    date_raw = _pick(d, _DATE_KEYS)
    date = None
    if date_raw:
        m = re.search(r"(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})", str(date_raw))
        if m:
            y, mo, dd = m.groups()
            date = f"{y}-{int(mo):02d}-{int(dd):02d}"

    return {
        "store": store,
        "title": title,
        "author": (str(_pick(d, _AUTHOR_KEYS)).strip() if _pick(d, _AUTHOR_KEYS) else None),
        "price": price,
        "purchase_date": date,
        "order_id": (str(_pick(d, _ID_KEYS)).strip() if _pick(d, _ID_KEYS) else None),
        "product_id": (str(_pick(d, _PRODID_KEYS)).strip() if _pick(d, _PRODID_KEYS) else None),
        "is_ebook": 1,
        "raw": json.dumps(d, ensure_ascii=False)[:2000],
    }


def records_from_json_payloads(payloads: list[Any], store: str) -> list[dict[str, Any]]:
    """캡처한 JSON 응답들에서 구매 레코드를 추출."""
    records: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for payload in payloads:
        for book in _find_book_dicts(payload):
            rec = _to_record(book, store)
            if rec:
                dedup = f"{rec['title']}|{rec.get('order_id')}|{rec.get('product_id')}"
                if dedup not in seen_titles:
                    seen_titles.add(dedup)
                    records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Playwright 흐름
# ---------------------------------------------------------------------------

def _launch_browser(p, headless: bool):
    """설치된 Chrome → Edge → 번들 Chromium 순서로 브라우저를 띄운다.

    Windows 에는 Edge 가 항상 설치돼 있으므로 별도 브라우저 다운로드 없이 동작한다.
    """
    last_err: Exception | None = None
    for channel in BROWSER_CHANNELS:
        try:
            return p.chromium.launch(headless=headless, channel=channel)
        except Exception as e:  # 해당 브라우저가 없으면 다음 후보로
            last_err = e
            continue
    # 마지막 수단: Playwright 번들 Chromium (playwright install chromium 필요)
    try:
        return p.chromium.launch(headless=headless)
    except Exception as e:
        raise RuntimeError(
            "사용할 브라우저를 찾지 못했습니다. Chrome 또는 Edge 가 설치돼 있어야 합니다."
        ) from (last_err or e)


def login_and_save_session(
    store: str,
    timeout_seconds: int = 300,
    on_status: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """보이는 브라우저를 열어 사용자가 로그인하게 하고, 세션을 저장한다.

    반환: {"ok": bool, "message": str}
    """
    _ensure_dirs()
    log = on_status or (lambda m: None)
    cfg = get_store(store)

    if not playwright_available():
        return {"ok": False, "message": "Playwright 가 설치되지 않았습니다. "
                "터미널에서 `pip install playwright && playwright install chromium` 실행 후 다시 시도하세요."}

    from playwright.sync_api import sync_playwright

    log(f"{cfg.name} 로그인 창을 엽니다. 브라우저에서 로그인(필요시 OTP)을 완료해 주세요…")
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(cfg.login_url, wait_until="domcontentloaded")

        # 로그인 성공 감지: URL 이 성공 마커를 포함하고 로그인 페이지를 벗어났을 때
        deadline = datetime.now().timestamp() + timeout_seconds
        logged_in = False
        while datetime.now().timestamp() < deadline:
            try:
                page.wait_for_timeout(1500)
                url = page.url
                left_login = "login" not in url.lower()
                hit_marker = any(m.lower() in url.lower() for m in cfg.login_success_markers)
                if left_login and hit_marker:
                    logged_in = True
                    break
            except Exception:
                break

        if not logged_in:
            # 사용자가 직접 로그인했을 수도 있으니 현재 상태라도 저장 시도
            log("로그인 자동 감지에 실패했지만 현재 세션을 저장합니다.")

        context.storage_state(path=str(session_path(store)))
        browser.close()

    log(f"{cfg.name} 세션을 저장했습니다.")
    return {"ok": True, "message": f"{cfg.name} 로그인 세션 저장 완료"}


def fetch_orders(
    store: str,
    headless: bool = True,
    save_capture: bool = True,
    on_status: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """저장된 세션으로 구매내역 페이지를 열고, 네트워크 응답을 캡처해 레코드를 추출.

    반환: {"ok": bool, "records": [...], "captured": int, "message": str}
    """
    _ensure_dirs()
    log = on_status or (lambda m: None)
    cfg = get_store(store)

    if not playwright_available():
        return {"ok": False, "records": [], "captured": 0,
                "message": "Playwright 가 설치되지 않았습니다."}

    if not has_session(store):
        return {"ok": False, "records": [], "captured": 0,
                "message": f"{cfg.name} 의 저장된 로그인 세션이 없습니다. 먼저 로그인하세요."}

    from playwright.sync_api import sync_playwright

    json_payloads: list[Any] = []

    log(f"{cfg.name} 구매내역을 불러옵니다…")
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=str(session_path(store)))
        page = context.new_page()

        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                url = response.url
                if "json" in ct or any(k.lower() in url.lower() for k in cfg.order_api_keywords):
                    if "json" in ct:
                        json_payloads.append(response.json())
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(cfg.orders_url, wait_until="networkidle", timeout=30000)
        except Exception:
            # networkidle 이 안 잡히면 일반 로드라도
            try:
                page.goto(cfg.orders_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                browser.close()
                return {"ok": False, "records": [], "captured": 0,
                        "message": f"구매내역 페이지 로드 실패: {e}"}

        page.wait_for_timeout(3000)

        # 페이지를 스크롤해 추가 로딩 유도
        try:
            for _ in range(3):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        html = page.content()
        browser.close()

    # 1순위: JSON 응답에서 추출
    records = records_from_json_payloads(json_payloads, store)

    # 2순위: HTML 파싱 (JSON 에서 아무것도 못 찾았을 때)
    if not records:
        records = _records_from_html(html, cfg)

    if save_capture:
        cap_file = CAPTURE_DIR / f"{store}_{datetime.now():%Y%m%d_%H%M%S}.json"
        cap_file.write_text(
            json.dumps({"json_payloads": json_payloads, "record_count": len(records)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    msg = f"{cfg.name}: JSON 응답 {len(json_payloads)}건 캡처, 도서 {len(records)}건 추출"
    log(msg)
    return {"ok": True, "records": records, "captured": len(json_payloads), "message": msg}


def _records_from_html(html: str, cfg: StoreConfig) -> list[dict[str, Any]]:
    """HTML 파싱 대비책. BeautifulSoup 가 있으면 사용."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    rows = soup.select(cfg.row_selector) if cfg.row_selector else []
    for row in rows:
        title_el = row.select_one(cfg.title_selector) if cfg.title_selector else None
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue
        author_el = row.select_one(cfg.author_selector) if cfg.author_selector else None
        date_el = row.select_one(cfg.date_selector) if cfg.date_selector else None
        price_el = row.select_one(cfg.price_selector) if cfg.price_selector else None

        price = None
        if price_el:
            digits = re.sub(r"[^\d]", "", price_el.get_text())
            price = int(digits) if digits else None

        date = None
        if date_el:
            m = re.search(r"(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})", date_el.get_text())
            if m:
                y, mo, dd = m.groups()
                date = f"{y}-{int(mo):02d}-{int(dd):02d}"

        records.append({
            "store": cfg.key,
            "title": title,
            "author": author_el.get_text(strip=True) if author_el else None,
            "price": price,
            "purchase_date": date,
            "is_ebook": 1,
        })
    return records
