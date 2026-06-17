# app/pages/3_전기차 화재 발생 현황.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pages/는 parents[2]

import pandas as pd
import streamlit as st
import plotly.express as px
from common.config import settings
from common.db import get_engine

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="전기차 화재 분석 대시보드", page_icon="🔥", layout="wide")
st.title("🔥 전기차 화재 발생 현황 멀티 분석 대시보드")
st.markdown("소방청 데이터를 기반으로 한 대한민국 전기차 화재 통계입니다.")
st.markdown("사이드바의 필터를 변경하면 전체 대시보드의 데이터가 실시간으로 필터링 됩니다.")

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    try:
        query = "select * from ev_fire_records"
        return pd.read_sql(query, get_engine())
    except Exception as e:
        # DB 연결 실패 시 에러 메시지를 화면에 살짝 출력하고 CSV로 파일 읽기
        st.sidebar.warning(f"⚠️ DB 접속 실패 (로컬 CSV 파일로 대체합니다.): {e}")

        return pd.read_csv(settings.DATA_DIR / "신가을_전기차 화재 발생 현황_20241231.csv", encoding="utf-8-sig")

# 데이터 불러오기
df_raw = load_data()

# --------------------------------------------
# 3. 사이드바 대화형 필터 (Interactive Filters) 구성
# --------------------------------------------
st.sidebar.header("🔎 데이터 상세 필터링")

# (1) 화재발생연도 & 월 필터
all_years = sorted(df_raw['fire_year'].unique().tolist())
all_months = sorted(df_raw['fire_month'].unique().tolist())

selected_years = st.sidebar.multiselect("📆 발생 연도 선택", all_years, default=all_years)
selected_months = st.sidebar.multiselect("📆 발생 월 선택", all_months, default=all_months)

# (2) 시도(지역) 필터
all_sido = sorted(df_raw['sido'].unique().tolist())
selected_sido = st.sidebar.multiselect("📍 지역(시도) 선택", all_sido, default=all_sido)

# (3) 발화요인 대분류 필터
all_causes = sorted(df_raw['ignition_main_category'].dropna().unique().tolist())
selected_causes = st.sidebar.multiselect("⚡ 발화요인 대분류 선택", all_causes, default=all_causes)

# 사용자가 선택한 조건에 따라 데이터를 실시간 필터링
df = df_raw[
    (df_raw['fire_year'].isin(selected_years)) &
    (df_raw['fire_month'].isin(selected_months)) &
    (df_raw['sido'].isin(selected_sido)) &
    (df_raw['ignition_main_category'].isin(selected_causes))
]

# 데이터가 텅 비었을 경우를 대비한 예외 안내
if df.empty:
    st.warning("선택하신 필터 조건에 일치하는 화재 데이터가 없습니다. 사이드바 조건을 다시 조정해 주세요.")
    st.stop()

# --------------------------------------------
# 4. 상단 요약 지표 (Metrics) 구역 생성
# --------------------------------------------
st.subheader("📊 필터링된 데이터 요약")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="🚨 총 화재 발생", value=f"{len(df)} 건", delta=f"전체 {len(df_raw)}건 중")

with col2:
    top_reg = df['sido'].value_counts().idxmax() if not df.empty else "데이터 없음"
    st.metric(label="📍 최다 발생 지역", value=top_reg)

with col3:
    top_cause = df['ignition_main_category'].value_counts().idxmax() if not df.empty else "데이터 없음"
    st.metric(label="⚡ 주요 발화 원인", value=top_cause)

with col4:
    # 가장 화재가 많이 발생한 차량 상태 (주차, 충전, 운행 등)
    top_status = df['vehicle_status'].value_counts().idxmax() if not df.empty else "데이터 없음"
    st.metric(label="🚗 최다 화재 시 차량 상태", value=top_status)

# # 요약 지표 바로 아래에 시각적 분석을 돕는 미니 차트 2종 배치
# if not df.empty:
#     st.write("")  # 약간의 공백 시각적 배치
#     sub_col1, sub_col2 = st.columns(2)
#
#     with sub_col1:
#         st.markdown("##### 🗺️ 지역별 화재 발생 순위 (Top 5)")
#         # 시도별 건수 집계 후 상위 5개 추출
#         df_sido = df['sido'].value_counts().reset_index(name='건수').head(5)
#
#         fig_sido = px.bar(df_sido,
#                           x='건수',
#                           y='sido',
#                           orientation='h',  # 가로 막대 그래프
#                           color='건수',
#                           color_continuous_scale='Reds',
#                           custom_data=['sido'])
#
#         # 툴팁 및 레이아웃 깔끔하게 정리
#         fig_sido.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>화재 건수: %{x}건<extra></extra>")
#         fig_sido.update_layout(yaxis={'categoryorder': 'total ascending'},
#                                xaxis_title=None, yaxis_title=None,
#                                coloraxis_showscale=False, height=200, margin=dict(l=0, r=0, t=10, b=10))
#         st.plotly_chart(fig_sido, use_container_width=True)
#
#     with sub_col2:
#         st.markdown("##### 📆 월별 화재 발생 추이️")
#         # 월별 건수 집계 및 정렬 (1~12월 순서 보장)
#         df_month = df['fire_month'].value_counts().reset_index(name='건수')
#         df_month = df_month.sort_values(by='fire_month')
#         df_month['fire_month'] = df_month['fire_month'].astype(str) + "월"
#
#         fig_month = px.line(df_month,
#                             x='fire_month',
#                             y='건수',
#                             markers=True,  # 꺾은 선에 점 표시
#                             color_discrete_sequence=['#FF4B4B'])
#
#         fig_month.update_traces(hovertemplate="<b>%{x}</b><br>화재 건수: %{y}건<extra></extra>")
#         fig_month.update_layout(xaxis_title=None, yaxis_title=None, height=200, margin=dict(l=0, r=0, t=10, b=10))
#         st.plotly_chart(fig_month, use_container_width=True)

st.write("---")

# --------------------------------------------
# 5. 시각화 파트 1: 시계열 트렌드 & 지역별 분석 (Top 2개 레이아웃)
# --------------------------------------------
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("📆 월별 화재 발생 추이 (시계열)")
    # 월별 건수 집계 및 정렬
    monthly_trend = df.groupby('fire_month').size().reset_index(name="화재건수")

    # 선 그래프(Line Chart) 시각화
    fig_line = px.line(monthly_trend, x='fire_month', y='화재건수',
                       labels={'fire_month': '발생 월', '화재건수': '발생 건수'},
                       markers=True, text='화재건수', title="월별 화재 추세선")
    fig_line.update_traces(textposition="top center", line_color="#EF553B")
    fig_line.update_layout(xaxis=dict(tickmode='linear', dtick=1)) # x축 1월단위 고정
    st.plotly_chart(fig_line, use_container_width=True)

with row1_col2:
    st.subheader("🗺️ 지역별(시도) 화재 발생 순위")
    # 시도별 화재 건수 정렬
    region_counts = df['sido'].value_counts().reset_index()
    region_counts.columns = ['지역', '화재건수']

    # 가로 막대 그래프(Horizontal Bar)로 가독성 상향
    fig_bar = px.bar(region_counts, x='화재건수', y='지역', orientation='h',
                     text='화재건수', color='화재건수',
                     color_continuous_scale='Oranges', title="지역별 화재 빈도")
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})  # 빈도 많은 순 정렬
    st.plotly_chart(fig_bar, use_container_width=True)

st.write("---")

# --------------------------------------------
# 6. 시각화 파트 2: 계층형 발화요인 & 특정인사이트 (지상/지하)
# --------------------------------------------
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("⚡ 발화요인 계층 분석 (대분류 → 소분류)")

    # 대분류 하위로 소분류 구분을 한눈에 보여주는 트리맵(Treemap) 차트
    fig_tree = px.treemap(df,
                          path=['ignition_main_category', 'ignition_sub_category'],
                          title="발화요인 대/소분류 비중 (네모 크기=발생 빈도)")

    # 툴팁(Hover) 커스텀 설정을 통해 불필요한 정보 제거 및 한글화 진행
    # %{label}: 현재 마우스가 올라간 항목의 이름 (대분류명 혹은 소분류명)
    # %{value}: 자동으로 집계된 해당 항목의 데이터 총 개수 (건수)
    # <extra></extra>: 우측에 따로 붙는 무미건조한 ID 라벨 박스를 제거
    fig_tree.update_traces(
        hovertemplate="<b>%{label}</b><br>화재 건수: %{value}건<extra></extra>"
    )

    st.plotly_chart(fig_tree, use_container_width=True)

with row2_col2:
    st.subheader("🏢 공간별 지상 / 지하 화재 비율")

    # 공간별 실제 합산 '건수' 계산
    df_ground = df.groupby('ground_level').size().reset_index(name='건수')

    # 도넛 차트 구성
    fig_donut = px.pie(df_ground,
                       names='ground_level',
                       values='건수',
                       hole=0.4,
                       title="공간구분별 비율",
                       color_discrete_sequence=px.colors.qualitative.Pastel)
    # textinfo: 차트 표면에 보일 정보 (라벨과 퍼센트 유지)
    # hovertemplate: 마우스를 올렸을 때 나타날 포맷 (건수 명시 + 우측 불필요한 라벨 박스 제거)
    fig_donut.update_traces(
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>화재 건수: %{value}건<extra></extra>"
    )
    st.plotly_chart(fig_donut, use_container_width=True)

st.write("---")

# --------------------------------------------
# 7. 시각화 파트 3: 차량 상태별 x 발화요인 복합 교차 분석
# --------------------------------------------
st.subheader("🔀 차량 상태별 발화요인 교차 분석")
st.markdown("차량이 특정 상태(충전중/주차/운행중)일 때 어떤 화재 원인이 주로 발생하는지 복합 비교합니다.")

# 차량 상태와 발화요인별로 그룹화하여 실제 합산 건수 데이터프래임
df_counts = df.groupby(['vehicle_status', 'ignition_main_category']).size().reset_index(name='건수')

# 누적 막대 그래프(Stacked Bar Chart) 구성
fig_stack = px.bar(df_counts,
                   x='vehicle_status',
                   y='건수',
                   color='ignition_main_category',
                   # 툴팁(hover)에서 사용할 데이터를 costom_data로 명시적으로 지정
                   custom_data=['ignition_main_category'],
                   labels={'vehicle_status': '차량 상태', 'ignition_main_category': '발화요인 대분류', '건수': '건수'},
                   barmode='stack',
                   text='건수')  # 막대 조각 내부에 숫자를 표시하는 옵션

# 막대 내부 숫자 포맷 및 위치 세부 설정
# hovertemplate을 추가하여 차량 상태(x축 데이터)를 제외하고 대분류와 건수만 노출
fig_stack.update_traces(
    texttemplate='%{text}',
    textposition='inside',
    hovertemplate="<b>%{customdata[0]}</b><br>화재 건수: %{y}<extra></extra>"
)

fig_stack.update_traces(texttemplate='%{text}', textposition='inside')

st.plotly_chart(fig_stack, use_container_width=True)

st.write("---")

# 8. 하단 원본 데이터 그리드 제공
with st.expander("🔎 필터링 된 원본 데이터 세부 확인"):
    st.dataframe(df, use_container_width=True)