# app/pages/2_EV_Charging_Demand.py
"""EV 통행량과 충전 수요 분석 화면.

작성: 김혜리 (대시보드 설계·분석 로직)
정리: 공용 모듈(common) 적용 · 페이지 구조/위치 정비

ev_infra DB(ev_charging_analysis / ev_traffic_analysis / ev_charging_map_analysis)를
읽어 충전소 위치·통행량·충전 수요를 함께 본다. 공용 모듈(common)로 DB에 접속한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # app/pages/ → 프로젝트 루트

import pandas as pd
import altair as alt
import pydeck as pdk
import streamlit as st

from common.db import get_engine
from common.ui import inject_theme

st.set_page_config(page_title="EV 충전 수요 대시보드", layout="wide")
inject_theme()


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "고속도로_전기차_통행_및_충전데이터.xlsx"
RECENT_MONTHS = 3
WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
DISPLAY_LABELS = {
    "date": "일자",
    "charge_date": "일자",
    "traffic_date": "일자",
    "charge_count": "충전횟수",
    "ev_count": "통행량",
    "total_vehicle_count": "전체 통행량",
    "total_charge_kwh": "충전용량(kWh)",
    "total_charge_time": "충전시간",
    "ev_ratio": "전기차 이용비율(%)",
    "station_name": "충전소명",
    "address": "주소",
    "section_name": "구간명",
    "total_charge_count": "충전횟수",
    "avg_charge_kwh": "평균 충전용량(kWh)",
    "avg_charge_time": "평균 충전시간",
}
METRIC_COLORS = {
    "통행량": "#2563EB",
    "충전횟수": "#06B6D4",
    "충전용량(kWh)": "#22C55E",
    "충전시간": "#F97316",
}
REST_AREA_PIN_ICON = (
    "data:image/svg+xml;utf8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='128' viewBox='0 0 96 128'%3E"
    "%3Cpath d='M48 4C25.9 4 8 21.9 8 44c0 29.5 40 80 40 80s40-50.5 40-80C88 21.9 70.1 4 48 4z' fill='%2322c55e' stroke='%2315803d' stroke-width='6'/%3E"
    "%3Ccircle cx='48' cy='44' r='16' fill='white'/%3E"
    "%3C/svg%3E"
)


@st.cache_data(ttl=600)
def load_recent_window():
    return pd.read_sql(
        f"""
        SELECT
            DATE_SUB(MAX(max_date), INTERVAL {RECENT_MONTHS} MONTH) AS start_date,
            MAX(max_date) AS end_date
        FROM (
            SELECT MAX(charge_date) AS max_date FROM ev_charging_analysis
            UNION ALL
            SELECT MAX(traffic_date) AS max_date FROM ev_traffic_analysis
        ) AS dates
        """,
        get_engine(),
    ).iloc[0]


def read_sql(query, params=None):
    window = load_recent_window()
    params = {
        "start_date": window["start_date"],
        "end_date": window["end_date"],
        **(params or {}),
    }
    return pd.read_sql(query, get_engine(), params=params)


@st.cache_data(ttl=600)
def load_charging_daily():
    df = read_sql(
        """
        SELECT
            charge_date,
            SUM(charge_count) AS charge_count,
            SUM(total_charge_kwh) AS total_charge_kwh,
            SUM(total_charge_time) AS total_charge_time
        FROM ev_charging_analysis
        WHERE charge_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY charge_date
        ORDER BY charge_date
        """
    )
    df["charge_date"] = pd.to_datetime(df["charge_date"])
    return df


@st.cache_data(ttl=600)
def load_traffic_daily():
    df = read_sql(
        """
        SELECT
            traffic_date,
            SUM(ev_count) AS ev_count,
            SUM(total_vehicle_count) AS total_vehicle_count,
            ROUND(SUM(ev_count) / NULLIF(SUM(total_vehicle_count), 0) * 100, 4) AS ev_ratio
        FROM ev_traffic_analysis
        WHERE traffic_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY traffic_date
        ORDER BY traffic_date
        """
    )
    df["traffic_date"] = pd.to_datetime(df["traffic_date"])
    return df


@st.cache_data(ttl=600)
def load_station_summary():
    return read_sql(
        """
        SELECT
            station_name,
            MAX(address) AS address,
            SUM(charge_count) AS charge_count,
            SUM(total_charge_kwh) AS total_charge_kwh,
            SUM(total_charge_time) AS total_charge_time
        FROM ev_charging_analysis
        WHERE charge_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY station_name
        ORDER BY charge_count DESC
        """
    )


@st.cache_data(ttl=600)
def load_map_data():
    return read_sql(
        """
        SELECT
            c.station_name,
            MAX(c.address) AS address,
            MAX(m.latitude) AS latitude,
            MAX(m.longitude) AS longitude,
            SUM(c.charge_count) AS total_charge_count,
            SUM(c.total_charge_kwh) AS total_charge_kwh,
            SUM(c.total_charge_time) AS total_charge_time,
            ROUND(SUM(c.total_charge_kwh) / NULLIF(SUM(c.charge_count), 0), 2) AS avg_charge_kwh,
            ROUND(SUM(c.total_charge_time) / NULLIF(SUM(c.charge_count), 0), 2) AS avg_charge_time
        FROM ev_charging_analysis c
        LEFT JOIN ev_charging_map_analysis m
          ON c.station_name = m.station_name
        WHERE c.charge_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY c.station_name
        ORDER BY total_charge_count DESC
        """
    )


@st.cache_data(ttl=600)
def load_rest_area_data():
    df = pd.read_excel(DATA_PATH, sheet_name=0)
    df = df.rename(
        columns={
            "시설명": "facility_name",
            "노선": "route_name",
            "지역본부": "region",
            "관할지사": "branch",
            "구간_전체": "section_name",
            "주소": "address",
            "위도": "latitude",
            "경도": "longitude",
        }
    )
    cols = [
        "facility_name",
        "route_name",
        "region",
        "branch",
        "section_name",
        "address",
        "latitude",
        "longitude",
    ]
    df = df[cols].dropna(subset=["latitude", "longitude"]).copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df.dropna(subset=["latitude", "longitude"])


def format_number(value, suffix=""):
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}{suffix}"


def relabel_columns(df):
    return df.rename(columns=DISPLAY_LABELS)


def style_chart(chart):
    return (
        chart.configure_axis(
            labelColor="#6B7280",
            titleColor="#6B7280",
            gridColor="#E5E7EB",
            domainColor="#E5E7EB",
            tickColor="#E5E7EB",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor="#111827",
            titleColor="#6B7280",
            labelFontSize=12,
            titleFontSize=12,
            orient="top",
        )
        .configure_view(stroke="#E5E7EB")
    )


def standardize_columns(df, columns):
    standardized = df.copy()
    for col in columns:
        values = pd.to_numeric(standardized[col], errors="coerce")
        std = values.std(ddof=0)
        if pd.isna(std) or std == 0:
            standardized[col] = 0
        else:
            standardized[col] = (values - values.mean()) / std
    return standardized


def normalize_columns(df, columns, scale=100):
    normalized = df.copy()
    for col in columns:
        values = pd.to_numeric(normalized[col], errors="coerce")
        min_value = values.min()
        max_value = values.max()
        if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
            normalized[col] = 0
        else:
            normalized[col] = (values - min_value) / (max_value - min_value) * scale
    return normalized


def with_weekday(df, date_col):
    weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    result = df.copy()
    result["요일"] = result[date_col].dt.dayofweek.map(weekday_map)
    return result


def render_map_tab(map_data, rest_area_data, charging_daily, station_summary):
    st.subheader("🗺️ 충전소별 충전 수요 지도")

    if map_data.empty:
        st.info("지도에 표시할 좌표 데이터가 없습니다.")
        return

    filtered = map_data.dropna(subset=["latitude", "longitude"]).copy()
    if filtered.empty:
        st.info("지도에 표시할 유효한 좌표 데이터가 없습니다.")
        return

    filtered["latitude"] = filtered["latitude"].astype(float)
    filtered["longitude"] = filtered["longitude"].astype(float)
    count_min = filtered["total_charge_count"].min()
    count_max = filtered["total_charge_count"].max()
    if count_max == count_min:
        filtered["radius"] = 9000
    else:
        count_ratio = (filtered["total_charge_count"] - count_min) / (count_max - count_min)
        filtered["radius"] = 2500 + (count_ratio ** 1.8) * 28000

    visible = filtered.copy()
    visible["point_type"] = "충전소"
    visible["name"] = visible["station_name"]
    visible["line1"] = "충전횟수: " + visible["total_charge_count"].map(lambda v: f"{v:,.0f}")
    visible["line2"] = "충전용량: " + visible["total_charge_kwh"].map(lambda v: f"{v:,.0f}") + " kWh"
    visible["line3"] = "충전시간: " + visible["total_charge_time"].map(lambda v: f"{v:,.0f}") + " 분"
    center_lat = visible["latitude"].mean()
    center_lon = visible["longitude"].mean()

    demand_layer = pdk.Layer(
        "ScatterplotLayer",
        data=visible,
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_fill_color="[6, 182, 212, 145]",
        get_line_color="[37, 99, 235, 190]",
        line_width_min_pixels=1,
        pickable=True,
    )

    rest_areas = rest_area_data.copy()
    rest_areas["point_type"] = "휴게소"
    rest_areas["name"] = rest_areas["facility_name"]
    rest_areas["line1"] = "노선: " + rest_areas["route_name"].fillna("-").astype(str)
    rest_areas["line2"] = "구간: " + rest_areas["section_name"].fillna("-").astype(str)
    rest_areas["line3"] = "주소: " + rest_areas["address"].fillna("-").astype(str)
    rest_areas["icon_data"] = rest_areas.apply(
        lambda _: {
            "url": REST_AREA_PIN_ICON,
            "width": 96,
            "height": 128,
            "anchorY": 128,
        },
        axis=1,
    )
    pin_layer = pdk.Layer(
        "IconLayer",
        data=rest_areas,
        get_position="[longitude, latitude]",
        get_icon="icon_data",
        get_size=4,
        size_scale=6,
        size_min_pixels=10,
        size_max_pixels=24,
        pickable=True,
    )

    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=6.4,
            pitch=35,
        ),
        layers=[demand_layer, pin_layer],
        tooltip={
            "html": """
            <b>{point_type}: {name}</b><br/>
            {line1}<br/>
            {line2}<br/>
            {line3}
            """,
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )

    left, right = st.columns([1.1, 1])
    with left:
        st.pydeck_chart(deck, use_container_width=True)
    with right:
        st.markdown("**⚡ 충전횟수 TOP 10 충전소 그래프**")
        top_count = filtered.sort_values("total_charge_count", ascending=False).head(10)
        chart_data = top_count[["station_name", "total_charge_count"]].rename(
            columns={"station_name": "충전소명", "total_charge_count": "충전횟수"}
        )
        chart = (
            alt.Chart(chart_data)
            .mark_bar(color="#2563EB", cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("충전소명:N", sort=None, axis=alt.Axis(labelAngle=-90)),
                y=alt.Y("충전횟수:Q"),
                tooltip=["충전소명", alt.Tooltip("충전횟수:Q", format=",.0f")],
            )
            .properties(height=560)
        )
        st.altair_chart(style_chart(chart), use_container_width=True)

    st.divider()
    render_charging_tab(charging_daily, station_summary)


def render_weekday_ev_charge_chart(traffic_daily, charging_daily):
    weekday_traffic = (
        with_weekday(traffic_daily, "traffic_date")
        .groupby("요일")["ev_count"]
        .mean()
        .reindex(WEEKDAY_ORDER)
        .reset_index()
        .rename(columns={"ev_count": "전기차 통행량"})
    )
    weekday_charge = (
        with_weekday(charging_daily, "charge_date")
        .groupby("요일")["total_charge_kwh"]
        .mean()
        .reindex(WEEKDAY_ORDER)
        .reset_index()
        .rename(columns={"total_charge_kwh": "충전용량(kWh)"})
    )
    weekday_compare = pd.merge(weekday_traffic, weekday_charge, on="요일", how="outer")
    weekday_compare = normalize_columns(weekday_compare, ["전기차 통행량", "충전용량(kWh)"])
    st.markdown("**📅 요일별 전기차 통행량 및 충전용량 추이**")
    chart_data = weekday_compare.melt(
        id_vars="요일",
        value_vars=["전기차 통행량", "충전용량(kWh)"],
        var_name="지표",
        value_name="정규화 값",
    )
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True, strokeWidth=2.8)
        .encode(
            x=alt.X("요일:N", sort=WEEKDAY_ORDER, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("정규화 값:Q"),
            color=alt.Color("지표:N"),
            tooltip=["요일", "지표", alt.Tooltip("정규화 값:Q", format=".1f")],
        )
        .properties(height=320)
    )
    st.altair_chart(style_chart(chart), use_container_width=True)


def render_compare_tab(traffic_daily, charging_daily):
    st.subheader("📊 통행량-충전수요 비교")

    merged = pd.merge(
        traffic_daily,
        charging_daily,
        left_on="traffic_date",
        right_on="charge_date",
        how="inner",
    )
    if merged.empty:
        st.info("같은 일자를 가진 통행량/충전 데이터가 없습니다.")
        return

    merged = merged.rename(columns={"traffic_date": "date"})
    merged = merged[
        [
            "date",
            "ev_count",
            "charge_count",
            "total_charge_kwh",
            "total_charge_time",
        ]
    ]

    metric_options = {
        "통행량": "ev_count",
        "충전횟수": "charge_count",
        "충전용량(kWh)": "total_charge_kwh",
        "충전시간": "total_charge_time",
    }
    st.markdown("**✨ 그래프에 표시할 지표**")
    metric_cols = st.columns(len(metric_options))
    selected_metric_labels = []
    for col, metric_label in zip(metric_cols, metric_options.keys()):
        if col.checkbox(metric_label, value=True, key=f"compare_metric_{metric_label}"):
            selected_metric_labels.append(metric_label)
    selected_metrics = [metric_options[label] for label in selected_metric_labels]

    st.markdown("**📈 일자별 통행량과 충전 수요 추이 (표준화)**")
    if selected_metrics:
        standardized = standardize_columns(merged, selected_metrics)
        chart_df = relabel_columns(
            standardized[["date", *selected_metrics]]
        ).melt(
            id_vars="일자",
            var_name="지표",
            value_name="표준화 값",
        )
        chart = (
            alt.Chart(chart_df)
            .mark_line(strokeWidth=2.8)
            .encode(
                x=alt.X("일자:T"),
                y=alt.Y("표준화 값:Q"),
                color=alt.Color(
                    "지표:N",
                    scale=alt.Scale(
                        domain=list(METRIC_COLORS.keys()),
                        range=list(METRIC_COLORS.values()),
                    ),
                ),
                tooltip=[
                    alt.Tooltip("일자:T", format="%Y-%m-%d"),
                    "지표",
                    alt.Tooltip("표준화 값:Q", format=".2f"),
                ],
            )
            .properties(height=340)
        )
        st.altair_chart(style_chart(chart), use_container_width=True)
    else:
        st.info("표시할 지표를 하나 이상 선택해주세요.")

    render_weekday_ev_charge_chart(traffic_daily, charging_daily)

    st.markdown("**🔎 통행량 vs 충전횟수 상관**")
    scatter_data = relabel_columns(merged)
    scatter = (
        alt.Chart(scatter_data)
        .mark_circle(size=80, color="#2563EB", opacity=0.72)
        .encode(
            x=alt.X("통행량:Q"),
            y=alt.Y("충전횟수:Q"),
            tooltip=[
                alt.Tooltip("일자:T", format="%Y-%m-%d"),
                alt.Tooltip("통행량:Q", format=",.0f"),
                alt.Tooltip("충전횟수:Q", format=",.0f"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(style_chart(scatter), use_container_width=True)

    st.markdown("**🗓️ 일자별 상세 데이터 조회**")
    min_date = merged["date"].min().date()
    max_date = merged["date"].max().date()
    selected_range = st.date_input(
        "조회 날짜 구간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date, end_date = min_date, max_date

    table = merged[
        merged["date"].dt.date.between(start_date, end_date)
    ].sort_values("date", ascending=False)
    st.dataframe(
        relabel_columns(table),
        use_container_width=True,
        hide_index=True,
    )


def render_charging_tab(charging_daily, station_summary):
    st.subheader("🌟 충전 수요 상세 분석")

    if station_summary.empty:
        st.info("표시할 충전소 데이터가 없습니다.")
        return

    metric_options = {
        "충전횟수": "charge_count",
        "충전용량(kWh)": "total_charge_kwh",
        "충전시간": "total_charge_time",
    }
    selected_label = st.radio(
        "지표 선택",
        list(metric_options.keys()),
        horizontal=True,
    )
    selected_metric = metric_options[selected_label]

    chart_data = (
        station_summary.dropna(subset=["station_name"])
        .sort_values(selected_metric, ascending=False)
        .head(20)[["station_name", selected_metric]]
        .rename(columns={"station_name": "휴게소명", selected_metric: selected_label})
    )
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#2563EB", cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
        .encode(
            x=alt.X(f"{selected_label}:Q"),
            y=alt.Y("휴게소명:N", sort="-x"),
            tooltip=[
                "휴게소명",
                alt.Tooltip(f"{selected_label}:Q", format=",.0f"),
            ],
        )
        .properties(height=520)
    )
    st.altair_chart(style_chart(chart), use_container_width=True)


def main():
    st.title("🚗⚡ EV 충전 수요 대시보드")

    selected_tab = st.radio(
        "분석 탭",
        [
            "1. 🗺️ 충전 수요 지도",
            "2. 📊 통행량-충전수요 비교",
        ],
        horizontal=True,
    )

    try:
        if selected_tab.startswith("1."):
            render_map_tab(
                load_map_data(),
                load_rest_area_data(),
                load_charging_daily(),
                load_station_summary(),
            )
        elif selected_tab.startswith("2."):
            render_compare_tab(load_traffic_daily(), load_charging_daily())
    except Exception as exc:
        st.error("선택한 분석 화면을 불러오지 못했습니다.")
        st.exception(exc)


if __name__ == "__main__":
    main()
