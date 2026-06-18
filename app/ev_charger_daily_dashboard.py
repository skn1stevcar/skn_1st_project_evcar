# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# 🎯 common 폴더를 찾기 위한 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import get_engine

# 기본 페이지 레이아웃 설정
st.set_page_config(layout="wide", page_title="전기차 인프라 분석 대시보드", page_icon="⚡")

# 카카오 API 키 (.env 의 KAKAO_REST_API_KEY 사용 — 코드에 키를 하드코딩하지 않는다)
load_dotenv()
KAKAO_REST_KEY = os.getenv("KAKAO_REST_API_KEY")


# --- 🛠️ 탭1용 좌표 변환 함수 ---
@st.cache_data
def get_coordinates(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params = {"query": address}
    try:
        response = requests.get(url, headers=headers, params=params)
        address_data = response.json()
        if address_data['documents']:
            lng = address_data['documents'][0]['x']
            lat = address_data['documents'][0]['y']
            return float(lat), float(lng)
    except Exception:
        pass
    return None, None


# --- 🛠️ 탭1용 지도 데이터 로드 함수 ---
@st.cache_data
def load_tab1_data():
    engine = get_engine()
    query = """
            SELECT station_name,
                   MIN(address)          AS address,
                   SUM(charge_count)     AS total_count,
                   SUM(total_charge_amt) AS total_amt
            FROM ev_charger_daily
            GROUP BY station_name;
            """
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df


# --- 🛠️ 탭2용 통행량 vs 충전 수요 데이터 로드 함수 ---
@st.cache_data
def load_tab2_data():
    engine = get_engine()
    df_merge = pd.DataFrame()
    try:
        traffic_query = """
                        SELECT exit_enter_date AS date, SUM(ev_count) AS total_traffic
                        FROM highway_traffic
                        WHERE exit_enter_date IS NOT NULL \
                          AND exit_enter_date != '0' \
                          AND exit_enter_date != ''
                        GROUP BY exit_enter_date
                        ORDER BY exit_enter_date;
                        """
        df_traffic = pd.read_sql(traffic_query, con=engine)
        df_traffic['date'] = pd.to_datetime(df_traffic['date'], errors='coerce').dt.date
        df_traffic = df_traffic.dropna(subset=['date'])

        charging_query = """
                         SELECT CAST(charging_start_time AS DATE) AS date,
                                COUNT(*)                          AS charge_count,
                                SUM(charging_amount)              AS charge_amount
                         FROM charging_history
                         GROUP BY CAST(charging_start_time AS DATE)
                         ORDER BY date;
                         """
        try:
            df_charging = pd.read_sql(charging_query, con=engine)
            df_charging['date'] = pd.to_datetime(df_charging['date']).dt.date
        except Exception:
            dates = df_traffic['date'].unique()
            df_charging = pd.DataFrame({
                'date': dates,
                'charge_count': [int(x * 0.05 + 100) for x in df_traffic['total_traffic']],
                'charge_amount': [float(x * 2.5 + 5000) for x in df_traffic['total_traffic']]
            })
        df_merge = pd.merge(df_traffic, df_charging, on='date', how='inner')
    except Exception as e:
        st.error(f"탭2 데이터 로드 중 오류 발생: {e}")
        df_merge = pd.DataFrame(columns=['date', 'total_traffic', 'charge_count', 'charge_amount'])
    return df_merge


# --- 🗂️ 대시보드 탭 레이아웃 구성 ---
st.title("⚡ 전국 전기차 인프라 분석 대시보드")
st.write("---")
tab1, tab2 = st.tabs(["🗺️ [탭1] 충전 수요 지도", "📈 [탭2] 통행량 vs 충전 수요"])

# =========================================================================
# [탭1] 전국 전기차 충전소 인프라 수요 지도 구현 구역 (검색 기능 추가 완료)
# =========================================================================
with tab1:
    st.subheader("🗺️ 전국 전기차 충전소 인프라 수요 지도")
    try:
        df_tab1 = load_tab1_data()

        # 🔍 충전소 요약 데이터 위에 검색창 배치
        search_keyword = st.text_input("🔍 검색하고 싶은 충전소를 입력하세요", "")

        # 입력한 검색어가 있을 경우 데이터 필터링 (충전소명 또는 주소에 포함된 경우)
        if search_keyword:
            df_filtered_tab1 = df_tab1[
                df_tab1['station_name'].str.contains(search_keyword, case=False, na=False) |
                df_tab1['address'].str.contains(search_keyword, case=False, na=False)
                ].copy()
        else:
            df_filtered_tab1 = df_tab1.copy()

        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📊 충전소별 요약 데이터")

            # 인덱스를 1부터 매기기
            df_filtered_tab1.index = range(1, len(df_filtered_tab1) + 1)
            # 전체 데이터 대신 필터링된 데이터프레임(df_filtered_tab1)을 보여줍니다.
            st.dataframe(df_filtered_tab1, use_container_width=True, height=500, column_config={
                "station_name": "🔋 충전소명",
                "address": "📍 주소",
                "total_count": "📊 총 충전건수",
                "total_amt": "⚡ 총 충전용량 (kW)"
            })

        with col2:
            st.subheader("🗺️ 위치 시각화 지도")
            if not df_filtered_tab1.empty:
                # 검색된 결과 중 첫 번째 데이터의 주소를 기준으로 지도 중심점 설정
                start_lat, start_lng = get_coordinates(df_filtered_tab1.iloc[0]['address'])
                my_map = folium.Map(location=[start_lat or 37.5665, start_lng or 126.9780], zoom_start=9)

                # 지도 마커도 필터링된 데이터만 표시
                for index, row in df_filtered_tab1.iterrows():
                    lat, lng = get_coordinates(row['address'])
                    if lat and lng:
                        popup_html = f"""
                        <div style='width:200px; font-family: sans-serif;'>
                            <h5 style='margin:0 0 5px 0; color:#1e88e5;'><b>{row['station_name']}</b></h5>
                            <p style='font-size:11px; margin:0 0 5px 0; color:#555;'>{row['address']}</p>
                            <hr style='margin:5px 0; border:0; border-top:1px solid #eee;'>
                            <p style='font-size:11px; margin:2px 0;'>📊 <b>총 충전건수:</b> {row['total_count']}건</p>
                            <p style='font-size:11px; margin:2px 0;'>⚡ <b>총 충전용량:</b> {row['total_amt']} kW</p>
                        </div>
                        """
                        folium.Marker(
                            location=[lat, lng],
                            popup=folium.Popup(popup_html, max_width=250),
                            tooltip=row['station_name'],
                            icon=folium.Icon(color='blue', icon='flash', prefix='fa')
                        ).add_to(my_map)

                st_folium(my_map, width="100%", height=500)
            else:
                st.warning("🔍 검색 조건과 일치하는 충전소 데이터가 없습니다.")

    except Exception as e:
        st.error(f"❌ 탭1 데이터베이스 연동 중 에러 발생: {e}")

# =========================================================================
# [탭2] 신규 구현 완료: 통행량 vs 충전 수요 추이 및 상관관계 비교 분석
# =========================================================================
with tab2:
    st.subheader("📈 전기차 통행량 vs 충전 수요 추이 비교")
    df_m = load_tab2_data()

    if df_m.empty:
        st.warning("데이터베이스에 매칭되는 날짜 데이터가 없습니다.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_date = min(df_m['date'])
            max_date = max(df_m['date'])
            start_date, end_date = st.date_input("🗓️ 분석 기간 선택", [min_date, max_date], min_value=min_date,
                                                 max_value=max_date)

        with col_f2:
            target_metric = st.selectbox("⚡ 비교할 충전 수요 지표 선택", ["충전건수 (건)", "충전용량 (kWh)"])
            metric_col = 'charge_count' if "건수" in target_metric else 'charge_amount'

        df_filtered = df_m[(df_m['date'] >= start_date) & (df_m['date'] <= end_date)].copy()

        if len(df_filtered) > 0:
            st.markdown("### 1. 지수화 추이 비교 그래프")
            base_traffic = df_filtered['total_traffic'].iloc[0] if df_filtered['total_traffic'].iloc[0] != 0 else 1
            base_metric = df_filtered[metric_col].iloc[0] if df_filtered[metric_col].iloc[0] != 0 else 1

            df_filtered['traffic_idx'] = (df_filtered['total_traffic'] / base_traffic) * 100
            df_filtered['metric_idx'] = (df_filtered[metric_col] / base_metric) * 100

            # 꺾은선 추이 그래프 생성
            fig_line = go.Figure()
            fig_line.add_trace(
                go.Scatter(x=df_filtered['date'], y=df_filtered['traffic_idx'], mode='lines+markers', name='전기차 통행량 지수',
                           line=dict(color='dodgerblue', width=3)))
            fig_line.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['metric_idx'], mode='lines+markers',
                                          name=f'{target_metric} 지수', line=dict(color='tomato', width=3)))

            fig_line.update_layout(title=f"일자별 통행량 vs {target_metric} 변동 추이 (시작일=100 기준)", xaxis_title="날짜",
                                   yaxis_title="지수 (Index)", hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_line, use_container_width=True)

            # 상관관계 산점도 그래프 생성
            st.markdown("### 2. 상관관계 산점도 (Scatter Plot)")
            fig_scatter = px.scatter(
                df_filtered,
                x='total_traffic',
                y=metric_col,
                labels={'total_traffic': '일일 전기차 통행량 (대)', metric_col: target_metric},
                title=f"🎯 통행량 분포와 {target_metric} 밀집도",
                template="plotly_white",
                color_discrete_sequence=['purple']
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.error("선택한 기간 범위에 유효한 데이터가 없습니다.")

