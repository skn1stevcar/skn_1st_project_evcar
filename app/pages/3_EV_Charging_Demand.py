# app/pages/3_EV_Charging_Demand.py
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
import pydeck as pdk
import streamlit as st

from common.db import get_engine

st.set_page_config(page_title="EV 충전 수요 대시보드", layout="wide")


def read_sql(query, params=None):
    return pd.read_sql(query, get_engine(), params=params)


@st.cache_data(ttl=600)
def load_kpis():
    charging = read_sql(
        """
        SELECT
            SUM(charge_count) AS total_charge_count,
            SUM(total_charge_kwh) AS total_charge_kwh,
            SUM(total_charge_time) AS total_charge_time
        FROM ev_charging_analysis
        """
    ).iloc[0]

    traffic = read_sql(
        """
        SELECT
            SUM(ev_count) AS total_ev_count,
            ROUND(SUM(ev_count) / NULLIF(SUM(total_vehicle_count), 0) * 100, 4) AS avg_ev_ratio
        FROM ev_traffic_analysis
        """
    ).iloc[0]

    return {
        "total_ev_count": traffic["total_ev_count"],
        "avg_ev_ratio": traffic["avg_ev_ratio"],
        "total_charge_count": charging["total_charge_count"],
        "total_charge_kwh": charging["total_charge_kwh"],
        "total_charge_time": charging["total_charge_time"],
    }


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
        GROUP BY traffic_date
        ORDER BY traffic_date
        """
    )
    df["traffic_date"] = pd.to_datetime(df["traffic_date"])
    return df


@st.cache_data(ttl=600)
def load_traffic_destination_daily():
    df = read_sql(
        """
        SELECT
            traffic_date,
            exit_toll_name,
            SUM(ev_count) AS ev_count,
            SUM(total_vehicle_count) AS total_vehicle_count,
            ROUND(SUM(ev_count) / NULLIF(SUM(total_vehicle_count), 0) * 100, 4) AS ev_ratio
        FROM ev_traffic_analysis
        GROUP BY traffic_date, exit_toll_name
        ORDER BY traffic_date, exit_toll_name
        """
    )
    df["traffic_date"] = pd.to_datetime(df["traffic_date"])
    return df


@st.cache_data(ttl=600)
def load_traffic_destination():
    return read_sql(
        """
        SELECT
            exit_toll_name,
            SUM(ev_count) AS ev_count,
            SUM(total_vehicle_count) AS total_vehicle_count,
            ROUND(SUM(ev_count) / NULLIF(SUM(total_vehicle_count), 0) * 100, 4) AS ev_ratio
        FROM ev_traffic_analysis
        GROUP BY exit_toll_name
        ORDER BY ev_ratio DESC
        """
    )


@st.cache_data(ttl=600)
def load_traffic_section():
    return read_sql(
        """
        SELECT
            section_name,
            SUM(ev_count) AS ev_count,
            SUM(total_vehicle_count) AS total_vehicle_count,
            ROUND(SUM(ev_count) / NULLIF(SUM(total_vehicle_count), 0) * 100, 4) AS ev_ratio
        FROM ev_traffic_analysis
        GROUP BY section_name
        ORDER BY ev_count DESC
        """
    )


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
        GROUP BY station_name
        ORDER BY charge_count DESC
        """
    )


@st.cache_data(ttl=600)
def load_map_data():
    return read_sql(
        """
        SELECT
            station_name,
            address,
            latitude,
            longitude,
            total_charge_count,
            total_charge_kwh,
            total_charge_time,
            avg_charge_kwh,
            avg_charge_time
        FROM ev_charging_map_analysis
        ORDER BY total_charge_count DESC
        """
    )


@st.cache_data(ttl=600)
def load_station_detail(station_name):
    detail = read_sql(
        """
        SELECT
            charge_date,
            station_name,
            SUM(charge_count) AS charge_count,
            SUM(total_charge_kwh) AS total_charge_kwh,
            SUM(total_charge_time) AS total_charge_time
        FROM ev_charging_analysis
        WHERE station_name = %(station_name)s
        GROUP BY charge_date, station_name
        ORDER BY charge_date
        """,
        params={"station_name": station_name},
    )
    detail["charge_date"] = pd.to_datetime(detail["charge_date"])
    return detail


def format_number(value, suffix=""):
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}{suffix}"


def metric_row(kpis):
    cols = st.columns(5)
    cols[0].metric("총 전기차 통행량", format_number(kpis["total_ev_count"]))
    cols[1].metric("평균 전기차 이용비율", f"{kpis['avg_ev_ratio']:.2f}%")
    cols[2].metric("총 충전건수", format_number(kpis["total_charge_count"]))
    cols[3].metric("총 충전용량", format_number(kpis["total_charge_kwh"], " kWh"))
    cols[4].metric("총 충전시간", format_number(kpis["total_charge_time"], " 분"))


def render_map_tab(map_data):
    st.subheader("충전소별 충전 수요 지도")

    if map_data.empty:
        st.info("지도에 표시할 좌표 데이터가 없습니다.")
        return

    filtered = map_data.dropna(subset=["latitude", "longitude"]).copy()
    if filtered.empty:
        st.info("지도에 표시할 유효한 좌표 데이터가 없습니다.")
        return

    filtered["latitude"] = filtered["latitude"].astype(float)
    filtered["longitude"] = filtered["longitude"].astype(float)
    filtered["radius"] = filtered["total_charge_count"].clip(lower=1) ** 0.5 * 90

    left, right = st.columns([3, 1])
    with right:
        min_count = 1 if len(filtered) < 5 else 5
        top_n = st.slider(
            "표시 충전소 수",
            min_count,
            len(filtered),
            min(35, len(filtered)),
        )
        table = filtered.head(top_n)[
            [
                "station_name",
                "address",
                "total_charge_count",
                "total_charge_kwh",
                "total_charge_time",
                "avg_charge_kwh",
                "avg_charge_time",
            ]
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    visible = filtered.head(top_n)
    center_lat = visible["latitude"].mean()
    center_lon = visible["longitude"].mean()

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=visible,
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_fill_color="[35, 118, 255, 170]",
        get_line_color="[12, 45, 90]",
        line_width_min_pixels=1,
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
        layers=[layer],
        tooltip={
            "html": """
            <b>{station_name}</b><br/>
            충전건수: {total_charge_count}<br/>
            충전용량: {total_charge_kwh} kWh<br/>
            충전시간: {total_charge_time} 분
            """,
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )

    with left:
        st.pydeck_chart(deck, use_container_width=True)


def render_compare_tab(traffic_daily, charging_daily):
    st.subheader("통행량 vs 충전 수요 비교")

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

    st.markdown("**일자별 전기차 통행량과 충전 수요**")
    st.line_chart(
        merged.set_index("date")[
            ["ev_count", "charge_count", "total_charge_kwh", "total_charge_time"]
        ],
        use_container_width=True,
    )

    st.markdown("**통행량 vs 충전건수 상관**")
    st.scatter_chart(
        merged,
        x="ev_count",
        y="charge_count",
        use_container_width=True,
    )

    st.dataframe(
        merged.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def render_traffic_tab(
    traffic_daily,
    traffic_destination_daily,
    traffic_destination,
    traffic_section,
):
    st.subheader("전기차 통행량 분석")

    st.markdown("**일자별 전체 통행량 추이**")
    st.line_chart(
        traffic_daily.set_index("traffic_date")[["ev_count", "total_vehicle_count"]],
        use_container_width=True,
    )

    destinations = (
        traffic_destination_daily.groupby("exit_toll_name")["ev_count"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .index
        .tolist()
    )
    selected = st.multiselect(
        "목적지 선택",
        destinations,
        default=destinations[:5],
    )

    if selected:
        pivot = (
            traffic_destination_daily[
                traffic_destination_daily["exit_toll_name"].isin(selected)
            ]
            .pivot_table(
                index="traffic_date",
                columns="exit_toll_name",
                values="ev_count",
                aggfunc="sum",
            )
            .fillna(0)
        )
        st.markdown("**일자별 + 목적지별 통행량 추이**")
        st.line_chart(pivot, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**목적지별 전기차 이용비율 TOP 10**")
        st.dataframe(
            traffic_destination.head(10),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        st.markdown("**구간별 통행량 TOP 10**")
        st.dataframe(
            traffic_section.head(10),
            use_container_width=True,
            hide_index=True,
        )


def render_charging_tab(charging_daily, station_summary):
    st.subheader("충전 수요 상세 분석")

    st.markdown("**일별 충전건수/충전용량/충전시간 추이**")
    st.line_chart(
        charging_daily.set_index("charge_date")[
            ["charge_count", "total_charge_kwh", "total_charge_time"]
        ],
        use_container_width=True,
    )

    st.markdown("**충전건수 TOP 10 충전소**")
    top_count = station_summary.sort_values("charge_count", ascending=False).head(10)
    st.bar_chart(
        top_count.set_index("station_name")["charge_count"],
        use_container_width=True,
    )

    st.markdown("**충전소별 Drill-down**")
    stations = station_summary["station_name"].dropna().tolist()
    if not stations:
        st.info("선택할 충전소 데이터가 없습니다.")
        return

    selected_station = st.selectbox("충전소 선택", stations, index=0)

    if selected_station:
        detail = load_station_detail(selected_station)
        summary = station_summary[station_summary["station_name"] == selected_station].iloc[0]

        m1, m2, m3 = st.columns(3)
        m1.metric("충전건수", format_number(summary["charge_count"]))
        m2.metric("충전용량", format_number(summary["total_charge_kwh"], " kWh"))
        m3.metric("충전시간", format_number(summary["total_charge_time"], " 분"))

        st.line_chart(
            detail.set_index("charge_date")[
                ["charge_count", "total_charge_kwh", "total_charge_time"]
            ],
            use_container_width=True,
        )


def main():
    st.title("EV 통행량과 충전 수요 분석")
    st.caption("충전소 위치, 일자별 통행량, 충전 수요를 함께 보는 분석 대시보드")

    try:
        kpis = load_kpis()
    except Exception as exc:
        st.error("DB에서 데이터를 불러오지 못했습니다.")
        st.exception(exc)
        st.stop()

    metric_row(kpis)
    st.divider()

    selected_tab = st.radio(
        "분석 탭",
        [
            "1. 충전 수요 지도",
            "2. 통행량 vs 충전 수요 비교",
            "3. 전기차 통행량 분석",
            "4. 충전 수요 상세 분석",
        ],
        horizontal=True,
    )

    try:
        if selected_tab.startswith("1."):
            render_map_tab(load_map_data())
        elif selected_tab.startswith("2."):
            render_compare_tab(load_traffic_daily(), load_charging_daily())
        elif selected_tab.startswith("3."):
            render_traffic_tab(
                load_traffic_daily(),
                load_traffic_destination_daily(),
                load_traffic_destination(),
                load_traffic_section(),
            )
        else:
            render_charging_tab(
                load_charging_daily(),
                load_station_summary(),
            )
    except Exception as exc:
        st.error("선택한 분석 화면을 불러오지 못했습니다.")
        st.exception(exc)


if __name__ == "__main__":
    main()
