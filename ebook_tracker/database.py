"""SQLite 데이터 계층.

구매 내역을 저장하고, 중복을 제거하며, 검색/필터를 제공합니다.
모든 함수는 호출 시점에 연결을 열고 닫으므로 Streamlit 의 재실행에도 안전합니다.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "ebook_data.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS purchases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    store         TEXT NOT NULL,
    title         TEXT NOT NULL,
    author        TEXT,
    publisher     TEXT,
    purchase_date TEXT,
    price         INTEGER,
    order_id      TEXT,
    product_id    TEXT,
    book_url      TEXT,
    cover_url     TEXT,
    is_ebook      INTEGER DEFAULT 1,
    raw           TEXT,
    fingerprint   TEXT UNIQUE,
    created_at    TEXT,
    updated_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_purchases_title ON purchases(title);
CREATE INDEX IF NOT EXISTS idx_purchases_author ON purchases(author);
CREATE INDEX IF NOT EXISTS idx_purchases_store ON purchases(store);

CREATE TABLE IF NOT EXISTS sync_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    store     TEXT,
    synced_at TEXT,
    found     INTEGER,
    added     INTEGER,
    status    TEXT,
    message   TEXT
);
"""


@contextmanager
def get_conn(db_path: Path | str = DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def make_fingerprint(store: str, title: str, order_id: str = "",
                     product_id: str = "", purchase_date: str = "") -> str:
    """중복 판별용 지문. 주문/상품 ID 가 있으면 그것을, 없으면 제목+날짜를 사용."""
    if order_id or product_id:
        basis = f"{store}|{order_id}|{product_id}"
    else:
        basis = f"{store}|{title.strip().lower()}|{purchase_date}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def upsert_purchase(record: dict[str, Any], db_path: Path | str = DB_PATH) -> bool:
    """구매 1건 저장. 새로 추가되면 True, 이미 있으면 False(중복)."""
    store = record.get("store", "")
    title = (record.get("title") or "").strip()
    if not title:
        return False

    fingerprint = make_fingerprint(
        store, title,
        record.get("order_id", "") or "",
        record.get("product_id", "") or "",
        record.get("purchase_date", "") or "",
    )

    with get_conn(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM purchases WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        if existing:
            return False

        now = _now()
        conn.execute(
            """INSERT INTO purchases
               (store, title, author, publisher, purchase_date, price,
                order_id, product_id, book_url, cover_url, is_ebook, raw,
                fingerprint, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                store, title,
                record.get("author"),
                record.get("publisher"),
                record.get("purchase_date"),
                record.get("price"),
                record.get("order_id"),
                record.get("product_id"),
                record.get("book_url"),
                record.get("cover_url"),
                int(record.get("is_ebook", 1)),
                record.get("raw"),
                fingerprint, now, now,
            ),
        )
    return True


def bulk_upsert(records: Iterable[dict[str, Any]], db_path: Path | str = DB_PATH) -> int:
    """여러 건 저장. 새로 추가된 건수를 반환."""
    added = 0
    for rec in records:
        if upsert_purchase(rec, db_path):
            added += 1
    return added


def search_purchases(
    keyword: str = "",
    store: Optional[str] = None,
    sort_by: str = "purchase_date",
    descending: bool = True,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    """제목/저자/출판사 키워드 + 서점 필터로 검색."""
    query = "SELECT * FROM purchases WHERE 1=1"
    params: list[Any] = []

    if keyword:
        like = f"%{keyword.strip()}%"
        query += " AND (title LIKE ? OR author LIKE ? OR publisher LIKE ?)"
        params += [like, like, like]

    if store and store != "all":
        query += " AND store = ?"
        params.append(store)

    allowed_sort = {"purchase_date", "title", "author", "store", "price", "created_at"}
    if sort_by not in allowed_sort:
        sort_by = "purchase_date"
    direction = "DESC" if descending else "ASC"
    query += f" ORDER BY {sort_by} {direction}"

    with get_conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_stats(db_path: Path | str = DB_PATH) -> dict[str, Any]:
    """전체/서점별 통계."""
    with get_conn(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM purchases").fetchone()["c"]
        by_store = conn.execute(
            "SELECT store, COUNT(*) AS c, SUM(price) AS total_price "
            "FROM purchases GROUP BY store"
        ).fetchall()
    return {
        "total": total,
        "by_store": {r["store"]: {"count": r["c"], "total_price": r["total_price"] or 0}
                     for r in by_store},
    }


def delete_purchase(purchase_id: int, db_path: Path | str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))


def clear_store(store: str, db_path: Path | str = DB_PATH) -> int:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM purchases WHERE store = ?", (store,))
        return cur.rowcount


def log_sync(store: str, found: int, added: int, status: str,
             message: str = "", db_path: Path | str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO sync_log (store, synced_at, found, added, status, message) "
            "VALUES (?,?,?,?,?,?)",
            (store, _now(), found, added, status, message),
        )


def recent_syncs(limit: int = 10, db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
