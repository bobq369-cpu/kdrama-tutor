"""📚 E북 구매 추적기 (E-book Purchase Tracker)

교보문고·Yes24·알라딘에서 산 전자책을 한 곳에서 검색·관리합니다.

실행:
    streamlit run ebook_app.py

주요 기능
  • 🔍 검색/필터: 제목·저자·출판사·서점별로 찾기
  • 🔄 자동 동기화: 서점 로그인(브라우저 직접 로그인, OTP 지원) 후 구매내역 자동 수집
  • 📥 CSV 가져오기: 직접 정리한 목록이나 서점 내려받기 파일 업로드
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ebook_tracker import config, database as db, importer, sync

st.set_page_config(page_title="E북 구매 추적기", page_icon="📚", layout="wide")

# DB 준비
db.init_db()

STORE_NAMES = {s.key: s.name for s in config.STORES.values()}
STORE_COLORS = {s.key: s.color for s in config.STORES.values()}


def store_badge(store_key: str) -> str:
    name = STORE_NAMES.get(store_key, store_key)
    color = STORE_COLORS.get(store_key, "#777")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8em;">{name}</span>'


# ---------------------------------------------------------------------------
# 사이드바: 통계
# ---------------------------------------------------------------------------
def render_sidebar():
    st.sidebar.title("📚 내 전자책 서재")
    stats = db.get_stats()
    st.sidebar.metric("전체 구매 도서", f"{stats['total']:,} 권")

    if stats["by_store"]:
        st.sidebar.markdown("**서점별 보유**")
        for key, info in stats["by_store"].items():
            name = STORE_NAMES.get(key, key)
            price = info["total_price"]
            price_txt = f" · {price:,}원" if price else ""
            st.sidebar.markdown(f"- {name}: **{info['count']}권**{price_txt}")

    st.sidebar.divider()
    st.sidebar.caption("최근 동기화")
    for s in db.recent_syncs(limit=3):
        icon = "✅" if s["status"] == "ok" else "⚠️"
        st.sidebar.caption(f"{icon} {STORE_NAMES.get(s['store'], s['store'])} · "
                           f"+{s['added']} ({s['synced_at'][:16]})")


# ---------------------------------------------------------------------------
# 탭 1: 검색
# ---------------------------------------------------------------------------
def render_search_tab():
    st.subheader("🔍 책 검색")

    col1, col2, col3 = st.columns([3, 1.2, 1.2])
    with col1:
        keyword = st.text_input("제목 · 저자 · 출판사", placeholder="예: 미드나잇 라이브러리, 김영하…",
                                label_visibility="collapsed")
    with col2:
        store_options = ["all"] + list(STORE_NAMES.keys())
        store_filter = st.selectbox(
            "서점", store_options,
            format_func=lambda k: "전체 서점" if k == "all" else STORE_NAMES[k],
            label_visibility="collapsed",
        )
    with col3:
        sort_label = st.selectbox(
            "정렬", ["최신 구매순", "제목순", "저자순", "가격높은순"],
            label_visibility="collapsed",
        )

    sort_map = {
        "최신 구매순": ("purchase_date", True),
        "제목순": ("title", False),
        "저자순": ("author", False),
        "가격높은순": ("price", True),
    }
    sort_by, descending = sort_map[sort_label]

    results = db.search_purchases(keyword=keyword, store=store_filter,
                                  sort_by=sort_by, descending=descending)

    st.caption(f"검색 결과: **{len(results)}권**")

    if not results:
        st.info("아직 등록된 책이 없거나 검색 결과가 없습니다. "
                "오른쪽 탭에서 **자동 동기화** 또는 **CSV 가져오기**로 책을 추가해 보세요.")
        return

    # 표 형태로 깔끔하게
    df = pd.DataFrame(results)
    display = pd.DataFrame({
        "서점": [STORE_NAMES.get(r["store"], r["store"]) for r in results],
        "제목": df["title"],
        "저자": df["author"].fillna("-"),
        "출판사": df.get("publisher", pd.Series(["-"] * len(df))).fillna("-"),
        "구매일": df["purchase_date"].fillna("-"),
        "가격": df["price"].apply(lambda x: f"{int(x):,}원" if pd.notna(x) and x else "-"),
    })
    st.dataframe(display, use_container_width=True, hide_index=True,
                 height=min(600, 80 + len(display) * 36))

    with st.expander("📤 검색 결과 CSV 로 내보내기"):
        csv_bytes = display.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv_bytes,
                           file_name="내_전자책_목록.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# 탭 2: 자동 동기화
# ---------------------------------------------------------------------------
def render_sync_tab():
    st.subheader("🔄 서점 자동 동기화")

    if not sync.playwright_available():
        st.warning(
            "자동 동기화에는 **Playwright** 가 필요합니다. 터미널에서 아래 명령을 한 번 실행하세요:\n\n"
            "```\npip install playwright\nplaywright install chromium\n```"
        )

    st.markdown(
        "**동작 방식** — ① 서점 로그인 창이 열립니다(평소처럼 직접 로그인, OTP도 가능). "
        "② 로그인하면 세션이 저장됩니다. ③ 이후엔 **구매내역 가져오기** 버튼만 누르면 됩니다.\n\n"
        "🔒 비밀번호는 앱에 저장되지 않습니다. 로그인은 실제 브라우저 창에서 직접 하십니다."
    )

    for store_key, store_name in STORE_NAMES.items():
        cfg = config.get_store(store_key)
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1.3, 1.3])
            with c1:
                logged = sync.has_session(store_key)
                status = "🟢 로그인 세션 있음" if logged else "⚪ 로그인 필요"
                st.markdown(f"### {store_name}")
                st.caption(status)
            with c2:
                if st.button(f"1️⃣ 로그인", key=f"login_{store_key}", use_container_width=True):
                    status_box = st.empty()
                    with st.spinner(f"{store_name} 로그인 창을 여는 중…"):
                        result = sync.login_and_save_session(
                            store_key, on_status=lambda m: status_box.info(m))
                    if result["ok"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
            with c3:
                disabled = not sync.has_session(store_key)
                if st.button(f"2️⃣ 구매내역 가져오기", key=f"fetch_{store_key}",
                             use_container_width=True, disabled=disabled):
                    status_box = st.empty()
                    with st.spinner(f"{store_name} 구매내역을 가져오는 중…"):
                        result = sync.fetch_orders(
                            store_key, headless=True,
                            on_status=lambda m: status_box.info(m))
                    if result["ok"]:
                        added = db.bulk_upsert(result["records"])
                        db.log_sync(store_key, len(result["records"]), added,
                                    "ok", result["message"])
                        st.success(f"{store_name}: {len(result['records'])}권 발견, "
                                   f"**{added}권 새로 추가**")
                        if not result["records"]:
                            st.info("자동 추출이 비어 있습니다. `captures/` 폴더의 캡처 파일을 보고 "
                                    "`ebook_tracker/config.py` 의 키워드/선택자를 조정하면 됩니다.")
                        st.rerun()
                    else:
                        db.log_sync(store_key, 0, 0, "error", result["message"])
                        st.error(result["message"])


# ---------------------------------------------------------------------------
# 탭 3: CSV 가져오기
# ---------------------------------------------------------------------------
def render_import_tab():
    st.subheader("📥 CSV / 엑셀 가져오기")
    st.markdown(
        "직접 정리한 목록이나 서점에서 내려받은 파일을 올리세요. "
        "컬럼 이름(제목·저자·출판사·구매일·가격 등)은 자동으로 인식합니다."
    )

    store_key = st.selectbox(
        "어느 서점의 목록인가요?", list(STORE_NAMES.keys()),
        format_func=lambda k: STORE_NAMES[k],
    )
    uploaded = st.file_uploader("CSV 또는 엑셀 파일", type=["csv", "xlsx", "xls"])

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        try:
            records, recognized = importer.import_csv(file_bytes, uploaded.name, store_key)
        except Exception as e:
            st.error(f"파일을 읽지 못했습니다: {e}")
            return

        if recognized:
            st.caption("인식된 컬럼: " + ", ".join(recognized))
        else:
            st.warning("표준 컬럼을 인식하지 못했습니다. 컬럼명에 '제목/도서명', '저자', '구매일' 등이 있는지 확인하세요.")

        st.write(f"미리보기 — 총 **{len(records)}건**")
        if records:
            preview = pd.DataFrame(records)[["title", "author", "purchase_date", "price"]].head(20)
            preview.columns = ["제목", "저자", "구매일", "가격"]
            st.dataframe(preview, use_container_width=True, hide_index=True)

            if st.button("✅ 가져오기 실행", type="primary"):
                added = db.bulk_upsert(records)
                db.log_sync(store_key, len(records), added, "ok", "CSV 가져오기")
                st.success(f"{len(records)}건 중 **{added}건** 새로 추가했습니다 "
                           f"(중복 {len(records) - added}건 제외).")
                st.rerun()


# ---------------------------------------------------------------------------
# 탭 4: 관리
# ---------------------------------------------------------------------------
def render_manage_tab():
    st.subheader("⚙️ 관리")

    st.markdown("**직접 한 권 추가**")
    with st.form("add_book"):
        c1, c2 = st.columns(2)
        with c1:
            store_key = st.selectbox("서점", list(STORE_NAMES.keys()),
                                     format_func=lambda k: STORE_NAMES[k])
            title = st.text_input("제목 *")
            author = st.text_input("저자")
        with c2:
            publisher = st.text_input("출판사")
            purchase_date = st.text_input("구매일 (예: 2024-03-15)")
            price = st.text_input("가격 (숫자만)")
        if st.form_submit_button("추가", type="primary"):
            if not title.strip():
                st.error("제목은 필수입니다.")
            else:
                price_val = int("".join(filter(str.isdigit, price))) if price else None
                added = db.upsert_purchase({
                    "store": store_key, "title": title, "author": author or None,
                    "publisher": publisher or None,
                    "purchase_date": purchase_date or None, "price": price_val,
                })
                if added:
                    st.success(f"'{title}' 추가 완료")
                    st.rerun()
                else:
                    st.warning("이미 등록된 책입니다.")

    st.divider()
    st.markdown("**서점별 전체 삭제**")
    c1, c2 = st.columns([2, 1])
    with c1:
        del_store = st.selectbox("삭제할 서점", list(STORE_NAMES.keys()),
                                 format_func=lambda k: STORE_NAMES[k], key="del_store")
    with c2:
        st.write("")
        st.write("")
        if st.button("🗑️ 이 서점 기록 전체 삭제"):
            count = db.clear_store(del_store)
            st.success(f"{STORE_NAMES[del_store]} 기록 {count}건 삭제")
            st.rerun()


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    render_sidebar()
    st.title("📚 E북 구매 추적기")
    st.caption("교보문고 · Yes24 · 알라딘에서 산 전자책을 한 곳에서 찾아보세요.")

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 검색", "🔄 자동 동기화", "📥 CSV 가져오기", "⚙️ 관리"])
    with tab1:
        render_search_tab()
    with tab2:
        render_sync_tab()
    with tab3:
        render_import_tab()
    with tab4:
        render_manage_tab()


if __name__ == "__main__":
    main()
