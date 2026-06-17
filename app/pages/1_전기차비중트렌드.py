# app/pages/1_전기차비중트렌드.py
"""전국 전기차 비중 트렌드 분석 페이지.

ev_infra.car_ev_status 테이블(지역·월별)을 읽어 월별로 집계해 보여준다.
DB 접속 실패 시 data/general_num.csv + ev_num.csv 로 직접 계산해 폴백한다.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # app/pages/ → 프로젝트 루트

import pandas as pd
import streamlit as st
import plotly.express as px

from common.config import settings
from common.db import get_engine

st.set_page_config(page_title="대한민국 전기차 비중 트렌드", layout="wide")

TARGET_MONTHS = ['2024-08', '2024-09', '2024-10', '2024-11', '2024-12', '2025-01', '2025-02']


# ==========================================================
# 📊 1. 데이터 로드 (DB 우선, 실패 시 CSV 폴백)
# ==========================================================
def _region_df_from_csv() -> pd.DataFrame:
    """car_ev_status 와 동일한 컬럼 구조(지역·월별)를 CSV 에서 직접 만든다."""
    general_data = {}
    with open(settings.DATA_DIR / "general_num.csv", encoding="cp949") as f:
        reader = csv.reader(f)
        next(reader)
        next(reader)
        for row in reader:
            if not row or len(row) < 4:
                continue
            연월, 지역 = row[0].strip(), row[1].strip()
            try:
                총계 = int(row[-2].strip() + row[-1].strip())
            except ValueError:
                총계 = int(row[-1].strip()) if row[-1].strip().isdigit() else 0
            general_data[(연월, 지역)] = general_data.get((연월, 지역), 0) + 총계

    rows = []
    with open(settings.DATA_DIR / "ev_num.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if not row:
                continue
            연월 = row[0][:7].strip()
            for idx in range(1, len(row)):
                지역 = headers[idx].strip()
                clean = row[idx].replace(",", "").strip()
                if not clean.isdigit():
                    continue
                전체 = general_data.get((연월, 지역))
                if 전체 is None:
                    continue
                rows.append({"base_month": 연월, "total_cars": 전체, "ev_cars": int(clean)})
    return pd.DataFrame(rows, columns=["base_month", "total_cars", "ev_cars"])


@st.cache_data(ttl=600)
def load_monthly():
    """car_ev_status 를 월별로 집계해 반환. (df_result, 출처문자열)"""
    try:
        region_df = pd.read_sql(
            "SELECT base_month, total_cars, ev_cars FROM car_ev_status", get_engine())
        src = "MySQL(ev_infra.car_ev_status)"
    except Exception:
        region_df = _region_df_from_csv()
        src = "CSV (폴백)"

    g = region_df.groupby("base_month", as_index=False)[["total_cars", "ev_cars"]].sum()
    monthly = {r["base_month"]: r for _, r in g.iterrows()}

    df = pd.DataFrame([
        {
            '연월': m,
            '총 자동차 대수 (A)': int(monthly.get(m, {}).get("total_cars", 0)),
            '총 전기차 대수 (B)': int(monthly.get(m, {}).get("ev_cars", 0)),
            '전기차 비중 (%)': round(
                monthly.get(m, {}).get("ev_cars", 0) / monthly.get(m, {}).get("total_cars", 0) * 100, 2)
            if monthly.get(m, {}).get("total_cars", 0) else 0,
        }
        for m in TARGET_MONTHS
    ])
    return df, src


df_result, data_source = load_monthly()

# ==========================================================
# 🎨 2. 화면 구현
# ==========================================================
st.markdown("""
<style>
    div.stRadio > div { flex-direction: row; gap: 15px; justify-content: center; margin-bottom: 30px; }
    div.stRadio label {
        background-color: #ffffff; border: 2px solid #e0e0e0; border-radius: 50px;
        padding: 10px 30px; color: #666; font-weight: 700; cursor: pointer;
        transition: all 0.2s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stRadio [data-baseweb="radio"] div:has(input:checked) + label {
        background-color: #FF4B4B !important; border-color: #FF4B4B !important; color: white !important;
        transform: translateY(-2px); box-shadow: 0 6px 10px rgba(255, 75, 75, 0.3);
    }
    div.stRadio label:hover { border-color: #FF4B4B; color: #FF4B4B; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size: 2.2rem; margin-bottom: 20px;'>📊 전국 전기차 비중 트렌드 분석</h1>",
            unsafe_allow_html=True)
st.caption(f"데이터 출처: {data_source}")
st.divider()

month_labels = [f"{m.split('-')[0]}년 {int(m.split('-')[1])}월" for m in TARGET_MONTHS]
selected_label = st.radio("기간 선택", month_labels, label_visibility="collapsed")
i = month_labels.index(selected_label)
selected_data = df_result[df_result['연월'] == TARGET_MONTHS[i]].iloc[0]

st.write("")
left_col, right_col = st.columns([1, 3])

with left_col:
    card_style = ("background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 8px solid; "
                  "box-shadow: 3px 3px 15px rgba(0,0,0,0.05); margin-bottom: 20px;")
    st.markdown(f"""
    <div style="{card_style} border-color: #00CC96;">
        <p style="font-size: 0.95rem; font-weight: 600; color: #888; margin-bottom: 5px;">🚗 총 자동차 등록 대수</p>
        <p style="font-size: 2.0rem; font-weight: 800; color: #222;">{int(selected_data['총 자동차 대수 (A)']):,} <span style="font-size: 1.1rem; color: #6c757d;">대</span></p>
    </div>
    <div style="{card_style} border-color: #ffbc00;">
        <p style="font-size: 0.95rem; font-weight: 600; color: #888; margin-bottom: 5px;">⚡ 총 전기차 등록 대수</p>
        <p style="font-size: 2.0rem; font-weight: 800; color: #222;">{int(selected_data['총 전기차 대수 (B)']):,} <span style="font-size: 1.1rem; color: #6c757d;">대</span></p>
    </div>
    <div style="{card_style} border-color: #FF4B4B;">
        <p style="font-size: 0.95rem; font-weight: 600; color: #888; margin-bottom: 5px;">📈 전기차 비중</p>
        <p style="font-size: 2.0rem; font-weight: 800; color: #222;">{selected_data['전기차 비중 (%)']:.2f} <span style="font-size: 1.1rem; color: #6c757d;">%</span></p>
    </div>
    """, unsafe_allow_html=True)

with right_col:
    df_chart = df_result.copy()
    df_chart['is_selected'] = df_chart['연월'] == TARGET_MONTHS[i]
    fig = px.line(df_chart, x='연월', y='전기차 비중 (%)', title="📈 대한민국 전기차 비중 트렌드 변화 추이")
    fig.update_traces(line=dict(color='#FF4B4B', width=3))
    fig.add_scatter(x=df_chart['연월'], y=df_chart['전기차 비중 (%)'], mode='markers+text',
                    text=df_chart['전기차 비중 (%)'].map('{:.2f}%'.format), textposition='top center',
                    marker=dict(size=df_chart['is_selected'].map({True: 16, False: 7}),
                                color=df_chart['is_selected'].map({True: '#C0392B', False: '#FF8A8A'}),
                                line=dict(width=2, color='#FFFFFF')), showlegend=False)
    fig.update_layout(height=450, margin=dict(t=50, b=20, l=20, r=20),
                      transition=dict(duration=400, easing="cubic-in-out"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("📋 연월별 상세 데이터 (전체 기간)")
df_formatted = df_result.copy()
df_formatted['연월'] = df_formatted['연월'].apply(lambda x: f"{x.split('-')[0]}년 {int(x.split('-')[1])}월")
df_formatted['총 자동차 대수 (A)'] = df_formatted['총 자동차 대수 (A)'].map('{:,}대'.format)
df_formatted['총 전기차 대수 (B)'] = df_formatted['총 전기차 대수 (B)'].map('{:,}대'.format)
df_formatted['전기차 비중 (%)'] = df_formatted['전기차 비중 (%)'].map('{:.2f}%'.format)
st.dataframe(df_formatted, use_container_width=True)

st.divider()
st.subheader("🚗 신규 자동차 시장의 전기차 전환율 분석")
df_diff = df_result.copy()
df_diff['일반차 증가'] = df_diff['총 자동차 대수 (A)'].diff()
df_diff['전기차 증가'] = df_diff['총 전기차 대수 (B)'].diff()
df_diff['전기차 전환율 (%)'] = (df_diff['전기차 증가'] / df_diff['일반차 증가']) * 100
fig_conv = px.area(df_diff.dropna(), x='연월', y='전기차 전환율 (%)',
                   title="📈 매월 신규 자동차 유입 중 전기차 비중 (%)",
                   color_discrete_sequence=['#FF4B4B'])
fig_conv.update_layout(height=350, margin=dict(t=50, b=20, l=20, r=20))
st.plotly_chart(fig_conv, use_container_width=True)

st.info("""
**🔍 데이터 인사이트:**
신규로 등록되는 전체 자동차 대수 중 전기차가 차지하는 비율을 분석했습니다.
이 수치가 상승하고 있다면, 시장의 무게중심이 내연기관에서 전기차로 빠르게 이동하고 있음을 의미합니다.
""")
