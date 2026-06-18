# -*- coding: utf-8 -*-
"""dashboard.py — 프로젝트 메인(랜딩) 페이지.

4개 분석 페이지를 간단히 소개하고 각 페이지로 이동할 수 있는 진입점이다.
사이드바 구성: 1) 전기차 비중 트렌드  2) 충전 수요  3) 화재 현황  4) FAQ

실행:
    streamlit run app/dashboard.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ → 프로젝트 루트

import streamlit as st  # noqa: E402

from common.ui import inject_theme  # noqa: E402

st.set_page_config(page_title="EV Infra 분석 대시보드", page_icon="⚡", layout="wide")
inject_theme()

# ----------------------------------------------------------------- 랜딩 전용 스타일
st.markdown(
    """
    <style>
      .lp-hero {
        background: linear-gradient(135deg,#2563EB 0%,#1E40AF 55%,#0891B2 100%);
        border-radius: 22px; padding: 38px 42px; color: #fff; margin-bottom: 26px;
        box-shadow: 0 16px 40px rgba(37,99,235,0.28);
      }
      .lp-hero h1 { color:#fff !important; font-size:2.25rem; margin:0; letter-spacing:-0.5px; }
      .lp-hero p  { margin:12px 0 0; opacity:0.94; font-size:1.0rem; line-height:1.6; }
      .lp-card {
        border: 1px solid #E5E7EB; border-radius: 16px; background:#FFFFFF;
        padding: 22px 22px 8px; height: 100%;
        box-shadow: 0 6px 18px rgba(17,24,39,0.06); transition: all .18s ease;
      }
      .lp-card:hover { transform: translateY(-2px); box-shadow: 0 14px 30px rgba(37,99,235,0.14);
        border-color:#DBE4FF; }
      .lp-card .ico { font-size: 2.0rem; }
      .lp-card .tag { display:inline-block; font-size:0.72rem; font-weight:700; color:#2563EB;
        background:#EFF6FF; border:1px solid #DBE4FF; border-radius:999px; padding:2px 10px;
        margin-left:6px; vertical-align:middle; }
      .lp-card h3 { margin:8px 0 4px; color:#111827; }
      .lp-card p  { color:#6B7280; font-size:0.9rem; line-height:1.6; min-height:3.0rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- 히어로
st.markdown(
    """
    <div class="lp-hero">
      <h1>⚡ 전기차 인프라 통합 분석 대시보드</h1>
      <p>전기차 보급 추이부터 충전 수요, 화재 안전, 제도 FAQ까지 — 네 가지 관점의 분석을 한 곳에서 살펴봅니다.<br>
      왼쪽 사이드바 또는 아래 카드에서 원하는 분석을 선택하세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- 페이지 소개 카드
PAGES = [
    {
        "icon": "📈", "no": "1",
        "title": "전기차 비중 트렌드",
        "desc": "전국 자동차 대비 전기차 등록 비중의 월별 추이와 신규 전환율을 이중 축으로 분석합니다.",
        "path": "pages/1_EV_Share_Trend.py",
    },
    {
        "icon": "🔌", "no": "2",
        "title": "충전 수요 분석",
        "desc": "고속도로 충전소 위치·통행량·충전 수요를 지도와 차트로 함께 살펴봅니다.",
        "path": "pages/2_EV_Charging_Demand.py",
    },
    {
        "icon": "🔥", "no": "3",
        "title": "화재 발생 현황",
        "desc": "전기차 화재 통계를 지역·발화요인·차량상태별로 다각도로 교차 분석합니다.",
        "path": "pages/3_EV_Fire_Incidents.py",
    },
    {
        "icon": "❓", "no": "4",
        "title": "자동차 FAQ 검색",
        "desc": "한국교통안전공단·자동차365·무공해차 통합누리집의 FAQ를 한 번에 검색합니다.",
        "path": "pages/4_FAQ.py",
    },
]

cols = st.columns(2)
for idx, page in enumerate(PAGES):
    with cols[idx % 2]:
        st.markdown(
            f"""
            <div class="lp-card">
              <div class="ico">{page['icon']}<span class="tag">{page['no']}페이지</span></div>
              <h3>{page['title']}</h3>
              <p>{page['desc']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(page["path"], label=f"{page['title']} 바로가기  →", use_container_width=True)
        st.write("")

st.divider()
st.caption("데이터 출처: 한국교통안전공단 · 자동차365 · 무공해차 통합누리집 · KOSIS · 소방청 · 한국도로공사 · 한국환경공단")
