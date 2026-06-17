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
from collections import Counter
from pathlib import Path

# 공용 모듈(common) import 를 위해 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from common.config import settings  # noqa: E402
from common.db import get_engine  # noqa: E402

JSON_PATH = settings.DATA_DIR / "faq.json"

st.set_page_config(page_title="ev_infra · FAQ 검색", page_icon="🚗", layout="wide")

# 출처별 배지 색상 (글자색, 배경색). 새 출처는 회색 폴백.
SOURCE_COLORS = {
    "한국교통안전공단": ("#2563eb", "#eff6ff"),
    "자동차365": ("#16a34a", "#f0fdf4"),
    "무공해차 통합누리집": ("#0891b2", "#ecfeff"),
}

# 출처별 크롤링 원본 사이트 링크
SOURCE_URLS = {
    "한국교통안전공단": "https://main.kotsa.or.kr/portal/bbs/faq_list.do",
    "자동차365": "https://www.car365.go.kr/ccpt/comm/ntcn/faqView.do?bbsId=124",
    "무공해차 통합누리집": "https://www.ev.or.kr/nportal/partcptn/initFaqAction.do",
}


def source_color(src):
    return SOURCE_COLORS.get(src, ("#6b7280", "#f3f4f6"))


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
    if item.get("source") not in sources:
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
      /* 히어로 헤더 */
      .hero { background: linear-gradient(135deg,#2563eb 0%,#1e40af 55%,#0891b2 100%);
        border-radius:20px; padding:30px 36px; color:#fff; margin-bottom:18px;
        box-shadow:0 12px 32px rgba(37,99,235,0.28); }
      .hero h1 { font-size:2.05rem; font-weight:800; margin:0; letter-spacing:-0.5px; }
      .hero p { margin:10px 0 0; opacity:0.92; font-size:0.97rem; }
      .hero .src-line { margin-top:16px; font-size:0.8rem; opacity:0.9; }
      .hero .src-line .lbl { font-weight:700; margin-right:6px; }
      .hero .src-line a { color:#fff; text-decoration:none; padding:3px 10px; border-radius:999px;
        background:rgba(255,255,255,0.16); margin-right:6px; font-weight:600;
        transition:background .15s ease; }
      .hero .src-line a:hover { background:rgba(255,255,255,0.34); text-decoration:underline; }
      /* 지표 카드 */
      .metric-card { background:#fff; border:1px solid #eef0f4; border-radius:16px;
        padding:18px 16px; text-align:center; box-shadow:0 4px 14px rgba(0,0,0,0.04);
        height:100%; }
      .metric-card .ico { font-size:1.5rem; }
      .metric-card .label { color:#94a3b8; font-size:0.78rem; font-weight:700; margin-top:2px; }
      .metric-card .value { color:#0f172a; font-size:1.75rem; font-weight:800; margin-top:2px;
        line-height:1.1; }
      /* FAQ 카드(expander) 꾸미기 */
      [data-testid="stExpander"] { border:1px solid #eef0f4 !important; border-radius:14px !important;
        box-shadow:0 2px 10px rgba(0,0,0,0.03); margin-bottom:10px; transition:all .18s ease; }
      [data-testid="stExpander"]:hover { box-shadow:0 8px 22px rgba(37,99,235,0.13);
        border-color:#dbe4ff !important; transform:translateY(-1px); }
      .faq-card-q { font-size:1.02rem; font-weight:600; line-height:1.5; }
      .badge { display:inline-block; padding:3px 11px; border-radius:999px;
        font-size:0.76rem; font-weight:700; margin-right:7px; }
      .faq-meta { color:#94a3b8; font-size:0.77rem; }
      .faq-answer { background:#f8fafc; border-left:4px solid #2563eb; border-radius:8px;
        padding:15px 18px; line-height:1.75; font-size:0.93rem; color:#1a1a2e; margin-top:6px; }
      .faq-answer *, .faq-card-q * { color:inherit; }
      mark { background:transparent; color:#d97706; font-weight:700;
        border-bottom:2px solid #fcd34d; padding:0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- 데이터
data, source = load_faq()
all_sources = sorted({d["source"] for d in data if d.get("source")})

# 크롤링 원본 사이트 링크 (데이터에 존재하는 출처만)
src_links = " ".join(
    f"<a href='{SOURCE_URLS[s]}' target='_blank' rel='noopener'>{s} ↗</a>"
    for s in all_sources if s in SOURCE_URLS
)

# ----------------------------------------------------------------- 헤더(히어로)
st.markdown(
    f"""
    <div class="hero">
      <h1>🚗 자동차 FAQ 통합 검색</h1>
      <p>한국교통안전공단 · 자동차365 · 무공해차 통합누리집의 자주 묻는 질문을 한 곳에서 검색하세요.</p>
      <div class="src-line"><span class="lbl">🔗 크롤링 출처</span>{src_links}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not data:
    st.error("데이터가 없습니다. `python etl/extract.py && python etl/transform.py` 후 "
             "DB 적재(`python etl/load.py`) 하거나 data/faq.json 을 준비하세요.")
    st.stop()

# ----------------------------------------------------------------- 요약 지표
all_cats_global = sorted({d["category"] for d in data if d.get("category")})
src_counts = Counter(d.get("source") for d in data if d.get("source"))

m1, m2, m3, m4 = st.columns(4)
metric_defs = [
    (m1, "📚", "전체 질문", f"{len(data):,}"),
    (m2, "🏛️", "출처 사이트", f"{len(all_sources)}"),
    (m3, "🗂️", "카테고리", f"{len(all_cats_global)}"),
    (m4, "🔥", "최다 출처", f"{src_counts.most_common(1)[0][1]:,}" if src_counts else "0"),
]
for col, ico, label, value in metric_defs:
    col.markdown(
        f"<div class='metric-card'><div class='ico'>{ico}</div>"
        f"<div class='label'>{label}</div><div class='value'>{value}</div></div>",
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------- 데이터 분포(접이식)
with st.expander("📊 데이터 한눈에 보기 (출처·카테고리 분포)"):
    g1, g2 = st.columns(2)
    with g1:
        sc = pd.DataFrame(src_counts.items(), columns=["출처", "건수"]).sort_values("건수")
        fig_src = px.pie(sc, names="출처", values="건수", hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Set2,
                         title="출처 사이트별 비중")
        fig_src.update_traces(textinfo="label+percent", textposition="inside")
        fig_src.update_layout(height=320, margin=dict(t=50, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig_src, use_container_width=True)
    with g2:
        cat_counts = Counter(d.get("category") for d in data if d.get("category"))
        cc = (pd.DataFrame(cat_counts.items(), columns=["카테고리", "건수"])
              .sort_values("건수", ascending=False).head(10).sort_values("건수"))
        fig_cat = px.bar(cc, x="건수", y="카테고리", orientation="h", text="건수",
                         color="건수", color_continuous_scale="Blues",
                         title="카테고리 Top 10")
        fig_cat.update_layout(height=320, margin=dict(t=50, b=10, l=10, r=10),
                              coloraxis_showscale=False, yaxis_title=None, xaxis_title=None)
        st.caption("💡 막대를 클릭하면 해당 카테고리로 아래 결과가 필터링됩니다.")
        cat_event = st.plotly_chart(fig_cat, use_container_width=True,
                                    on_select="rerun", key="cat_chart")

        # 막대 클릭 → 카테고리 필터에 반영 (새 클릭일 때만)
        pts = (cat_event.selection.points if cat_event and cat_event.selection else []) or []
        clicked = [p.get("y") or p.get("label") for p in pts]
        clicked = [c for c in clicked if c]
        if clicked and st.session_state.get("_last_cat_click") != clicked:
            st.session_state["_last_cat_click"] = clicked
            st.session_state["cat_filter"] = clicked
            st.rerun()

st.divider()

# ----------------------------------------------------------------- 검색 입력
c1, c2 = st.columns([3, 1])
with c1:
    keyword = st.text_input("🔎 검색어", placeholder="예: 자동차검사, 과태료, 유효기간 …")
with c2:
    scope = st.radio("검색 범위", ["제목+내용", "제목", "내용"], horizontal=True)

# 출처 사이트 토글 (사이트가 3개뿐이라 멀티셀렉트 대신 누르면 켜지고/꺼지는 칩)
sel_sources = st.pills(
    "출처 사이트 (클릭해서 켜고 끄기)",
    all_sources,
    selection_mode="multi",
    default=all_sources,  # 처음엔 전부 활성화
)
sel_sources = sel_sources or []

filtered_by_source = [d for d in data if d.get("source") in sel_sources]
all_categories = sorted({d["category"] for d in filtered_by_source if d.get("category")})

# 차트 클릭 등으로 선택된 값 중 현재 선택 가능한 카테고리만 남김(없는 값이면 오류 방지)
if "cat_filter" in st.session_state:
    st.session_state["cat_filter"] = [c for c in st.session_state["cat_filter"] if c in all_categories]
sel_categories = st.multiselect("카테고리 필터", all_categories, key="cat_filter")

results = [d for d in data if match(d, keyword, scope, sel_sources, sel_categories)]

left, right = st.columns([1, 1])
left.markdown(f"**검색 결과: {len(results)}건** / 전체 {len(data)}건")
view = right.radio("보기", ["카드형", "슬라이드형"], horizontal=True, label_visibility="collapsed")
st.divider()

if not results:
    if not sel_sources:
        st.info("표시할 출처 사이트가 모두 꺼져 있습니다. 위 버튼을 눌러 하나 이상 켜 주세요.")
    else:
        st.info("검색 결과가 없습니다. 다른 키워드나 카테고리로 시도해 보세요.")
    st.stop()


# ----------------------------------------------------------------- 렌더링
def badges_html(item):
    """카테고리·출처 배지 + 메타 정보 HTML."""
    cate = item.get("category") or "기타"
    src = item.get("source") or ""
    date = item.get("modified") or "-"
    fg, bg = source_color(src)
    return (
        f"<span class='badge' style='background:#eef4ff;color:#2563eb'>{cate}</span>"
        f"<span class='badge' style='background:{bg};color:{fg}'>{src}</span>"
        f"<span class='faq-meta'>마지막 수정일 {date} · No.{item['id']}</span>"
    )


def render_card(item):
    cate = item.get("category") or "기타"
    with st.expander(f"[{cate}]　{item['question']}"):
        st.markdown(
            badges_html(item) +
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
    st.markdown(
        badges_html(item) +
        f"<div class='faq-card-q' style='margin:10px 0 14px'>Q. {highlight(item['question'], keyword)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='faq-answer'>A. {highlight(item['answer'], keyword)}</div>",
                unsafe_allow_html=True)
