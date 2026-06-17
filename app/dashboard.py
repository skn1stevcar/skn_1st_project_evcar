# -*- coding: utf-8 -*-
"""
dashboard.py — Streamlit 대시보드

ev_infra.faq 테이블을 읽어 FAQ 검색 페이지를 제공한다.
DB 접속이 안 되면 data/faq.json 으로 자동 폴백한다.

실행:
    streamlit run app/dashboard.py
"""

import json
import re
import sys
from pathlib import Path

# 공용 모듈(common) import 를 위해 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common.config import settings  # noqa: E402
from common.db import get_engine  # noqa: E402

JSON_PATH = settings.DATA_DIR / "faq.json"

st.set_page_config(page_title="ev_infra · FAQ 검색", page_icon="🚗", layout="wide")


# ----------------------------------------------------------------- 데이터 로드
@st.cache_data(ttl=600)
def load_faq():
    """DB(ev_infra.faq) 우선, 실패 시 data/faq.json 폴백."""
    try:
        df = pd.read_sql("SELECT id, source, category, question, answer, modified FROM faq", get_engine())
        df["modified"] = df["modified"].astype(str).replace("NaT", "")
        return df.to_dict("records"), "MySQL(ev_infra.faq)"
    except Exception:
        if JSON_PATH.exists():
            with open(JSON_PATH, encoding="utf-8") as f:
                return json.load(f), "data/faq.json (폴백)"
        return [], "없음"


def highlight(text, keyword):
    safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if keyword:
        safe = re.compile(re.escape(keyword), re.IGNORECASE).sub(
            lambda m: f"<mark>{m.group(0)}</mark>", safe)
    return safe.replace("\n", "<br>")


def match(item, keyword, scope, sources, categories):
    if sources and item.get("source") not in sources:
        return False
    if categories and item.get("category") not in categories:
        return False
    if not keyword:
        return True
    kw = keyword.lower()
    in_q = kw in str(item.get("question", "")).lower()
    in_a = kw in str(item.get("answer", "")).lower()
    return {"제목": in_q, "내용": in_a}.get(scope, in_q or in_a)


# ----------------------------------------------------------------- 스타일
st.markdown(
    """
    <style>
      .faq-card-q { font-size:1.02rem; font-weight:600; line-height:1.5; }
      .faq-cate { display:inline-block; padding:2px 10px; border-radius:12px;
        background:#eef4ff; color:#2563eb; font-size:0.78rem; font-weight:600; margin-right:8px; }
      .faq-source { display:inline-block; padding:2px 10px; border-radius:12px;
        background:#f0fdf4; color:#16a34a; font-size:0.78rem; font-weight:600; margin-right:8px; }
      .faq-meta { color:#888; font-size:0.78rem; }
      .faq-answer { background:#fafafa; border-left:3px solid #2563eb; border-radius:6px;
        padding:14px 16px; line-height:1.7; font-size:0.93rem; color:#1a1a2e; }
      .faq-answer *, .faq-card-q * { color:inherit; }
      mark { background:transparent; color:#d97706; font-weight:700;
        border-bottom:2px solid #fcd34d; padding:0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- 헤더
st.title("🚗 한국교통안전공단 FAQ 검색")
data, source = load_faq()
st.caption(f"일반분야 자주하는 질문(FAQ) · 데이터 출처: {source}")

if not data:
    st.error("데이터가 없습니다. `python etl/extract.py && python etl/transform.py` 후 "
             "DB 적재(`python etl/load.py`) 하거나 data/faq.json 을 준비하세요.")
    st.stop()

# ----------------------------------------------------------------- 검색 입력
all_sources = sorted({d["source"] for d in data if d.get("source")})
c1, c2 = st.columns([3, 1])
with c1:
    keyword = st.text_input("🔎 검색어", placeholder="예: 자동차검사, 과태료, 유효기간 …")
with c2:
    scope = st.radio("검색 범위", ["제목+내용", "제목", "내용"], horizontal=True)

sel_sources = st.multiselect("출처 사이트 필터", all_sources, default=[])

filtered_by_source = [d for d in data if not sel_sources or d.get("source") in sel_sources]
all_categories = sorted({d["category"] for d in filtered_by_source if d.get("category")})
sel_categories = st.multiselect("카테고리 필터", all_categories, default=[])

results = [d for d in data if match(d, keyword, scope, sel_sources, sel_categories)]

left, right = st.columns([1, 1])
left.markdown(f"**검색 결과: {len(results)}건** / 전체 {len(data)}건")
view = right.radio("보기", ["카드형", "슬라이드형"], horizontal=True, label_visibility="collapsed")
st.divider()

if not results:
    st.info("검색 결과가 없습니다. 다른 키워드나 카테고리로 시도해 보세요.")
    st.stop()


# ----------------------------------------------------------------- 렌더링
def render_card(item):
    cate = item.get("category") or "기타"
    src = item.get("source") or ""
    date = item.get("modified") or "-"
    with st.expander(f"[{cate}] {item['question']}"):
        st.markdown(
            f"<span class='faq-cate'>{cate}</span>"
            f"<span class='faq-source'>{src}</span>"
            f"<span class='faq-meta'>마지막 수정일 {date} · No.{item['id']}</span>"
            f"<div class='faq-card-q' style='margin-top:8px'>Q. {highlight(item['question'], keyword)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<div class='faq-answer'>A. {highlight(item['answer'], keyword)}</div>",
                    unsafe_allow_html=True)


if view == "카드형":
    PAGE_SIZE = 10
    total_pages = (len(results) - 1) // PAGE_SIZE + 1
    page = st.number_input("페이지", 1, total_pages, 1) if total_pages > 1 else 1
    for item in results[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]:
        render_card(item)
    if total_pages > 1:
        st.caption(f"{page} / {total_pages} 페이지")

else:  # 슬라이드형
    st.session_state.setdefault("slide_idx", 0)
    st.session_state.slide_idx = max(0, min(st.session_state.slide_idx, len(results) - 1))
    n1, n2, n3 = st.columns([1, 3, 1])
    if n1.button("⬅ 이전", use_container_width=True, disabled=st.session_state.slide_idx == 0):
        st.session_state.slide_idx -= 1
    if n3.button("다음 ➡", use_container_width=True,
                 disabled=st.session_state.slide_idx >= len(results) - 1):
        st.session_state.slide_idx += 1
    n2.markdown(f"<div style='text-align:center;color:#888'>"
                f"{st.session_state.slide_idx + 1} / {len(results)}</div>", unsafe_allow_html=True)

    item = results[st.session_state.slide_idx]
    cate = item.get("category") or "기타"
    src = item.get("source") or ""
    date = item.get("modified") or "-"
    st.markdown(
        f"<span class='faq-cate'>{cate}</span>"
        f"<span class='faq-source'>{src}</span>"
        f"<span class='faq-meta'>마지막 수정일 {date} · No.{item['id']}</span>"
        f"<div class='faq-card-q' style='margin:10px 0 14px'>Q. {highlight(item['question'], keyword)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='faq-answer'>A. {highlight(item['answer'], keyword)}</div>",
                unsafe_allow_html=True)
