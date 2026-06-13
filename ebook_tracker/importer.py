"""CSV / 엑셀 가져오기.

자동 동기화가 막히거나 직접 정리한 목록을 올리고 싶을 때 사용하는 안정적인 경로입니다.
서점마다 컬럼 이름이 달라서, 흔히 쓰이는 한국어/영어 컬럼명을 폭넓게 매핑합니다.
"""

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

# 표준 필드 ← 가능한 컬럼명들 (소문자/공백제거 후 비교)
COLUMN_ALIASES: dict[str, list[str]] = {
    "title": ["제목", "도서명", "상품명", "책제목", "title", "bookname", "productname", "name"],
    "author": ["저자", "지은이", "작가", "author", "writer"],
    "publisher": ["출판사", "publisher", "pub"],
    "purchase_date": ["구매일", "구매일자", "주문일", "주문일자", "결제일", "date",
                      "orderdate", "purchasedate"],
    "price": ["가격", "금액", "결제금액", "판매가", "price", "amount", "paid"],
    "order_id": ["주문번호", "주문id", "orderid", "ordernumber", "orderno"],
    "product_id": ["상품번호", "상품id", "productid", "isbn", "barcode"],
    "book_url": ["url", "링크", "주소", "link", "bookurl"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s)).strip().lower()


def _build_reverse_map(columns: list[str]) -> dict[str, str]:
    """실제 컬럼명 → 표준 필드명."""
    norm_to_actual = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _norm(alias)
            if key in norm_to_actual:
                mapping[norm_to_actual[key]] = field
                break
    return mapping


def _parse_price(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def _parse_date(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    # YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD / YYYYMMDD 등 → YYYY-MM-DD
    m = re.search(r"(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return text


def read_table(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """CSV 또는 엑셀 파일을 DataFrame 으로 읽기. 한글 인코딩 자동 감지."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))

    # CSV: UTF-8 → UTF-8-SIG → CP949(euc-kr) 순으로 시도
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    # 마지막 수단: 오류 무시
    return pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", encoding_errors="ignore")


def rows_from_dataframe(df: pd.DataFrame, store: str) -> list[dict[str, Any]]:
    """DataFrame → 표준 구매 레코드 목록."""
    reverse = _build_reverse_map(list(df.columns))
    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        rec: dict[str, Any] = {"store": store, "is_ebook": 1}
        for actual_col, field in reverse.items():
            rec[field] = row[actual_col]

        if not rec.get("title") or pd.isna(rec.get("title")):
            continue

        rec["title"] = str(rec["title"]).strip()
        rec["author"] = str(rec["author"]).strip() if rec.get("author") and not pd.isna(rec.get("author")) else None
        rec["publisher"] = str(rec["publisher"]).strip() if rec.get("publisher") and not pd.isna(rec.get("publisher")) else None
        rec["price"] = _parse_price(rec.get("price"))
        rec["purchase_date"] = _parse_date(rec.get("purchase_date"))
        rec["order_id"] = str(rec["order_id"]).strip() if rec.get("order_id") and not pd.isna(rec.get("order_id")) else None
        rec["product_id"] = str(rec["product_id"]).strip() if rec.get("product_id") and not pd.isna(rec.get("product_id")) else None
        records.append(rec)

    return records


def import_csv(file_bytes: bytes, filename: str, store: str) -> tuple[list[dict[str, Any]], list[str]]:
    """파일을 읽어 표준 레코드 목록과 인식된 컬럼 정보를 반환."""
    df = read_table(file_bytes, filename)
    reverse = _build_reverse_map(list(df.columns))
    recognized = [f"{actual} → {field}" for actual, field in reverse.items()]
    records = rows_from_dataframe(df, store)
    return records, recognized
