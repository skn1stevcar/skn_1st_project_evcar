import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # etl/ → 프로젝트 루트

import pandas as pd
from sqlalchemy import text

from common.config import settings
from common.db import get_engine


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = settings.DATA_DIR / "고속도로_전기차_통행_및_충전데이터.xlsx"

TEST_MODE = False
TEST_ROWS = 100


def log(message):
    print(f"[INFO] {message}", flush=True)


def normalize_column_name(col):
    col = str(col).strip()
    col = col.replace("\n", "")
    col = col.replace("\r", "")
    col = re.sub(r"\s+", "", col)
    return col


def clean_columns(df):
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    return df


def load_excel():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {DATA_PATH}")

    excel_file = pd.ExcelFile(DATA_PATH)
    log(f"시트 목록: {excel_file.sheet_names}")

    if TEST_MODE:
        log(f"TEST_MODE=True: 각 시트 {TEST_ROWS}행만 읽습니다.")
        charger_df = pd.read_excel(excel_file, sheet_name=1, nrows=TEST_ROWS)
        traffic_df = pd.read_excel(excel_file, sheet_name=2, nrows=TEST_ROWS)
    else:
        log("전체 데이터를 읽습니다.")
        charger_df = pd.read_excel(excel_file, sheet_name=1)
        traffic_df = pd.read_excel(excel_file, sheet_name=2)

    return charger_df, traffic_df


def prepare_raw_charger(df):
    df = clean_columns(df)

    log("충전소 raw 컬럼명")
    print(df.columns.tolist())

    df = df.rename(columns={
        "충전시작일": "charge_start_date",
        "충전소명": "station_name",
        "주소": "address",
        "충전기ID": "charger_id",
        "충전기타입": "charger_type",
        "충전건수": "charge_count",
        "충전용량_합계": "total_charge_kwh",
        "충전시간_합계": "total_charge_time",
    })

    cols = [
        "charge_start_date",
        "station_name",
        "address",
        "charger_id",
        "charger_type",
        "charge_count",
        "total_charge_kwh",
        "total_charge_time",
    ]

    missing = [col for col in cols if col not in df.columns]
    if missing:
        raise KeyError(f"충전소 raw 누락 컬럼: {missing}")

    return df[cols].astype(str)


def prepare_raw_traffic(df):
    df = clean_columns(df)

    log("통행량 raw 컬럼명")
    print(df.columns.tolist())

    df = df.rename(columns={
        "입구영업소코드": "entry_toll_code",
        "입구영업소": "entry_toll_name",
        "입구영업소주소": "entry_address",
        "입구영업소_주소": "entry_address",
        "출구영업소코드": "exit_toll_code",
        "출구영업소": "exit_toll_name",
        "출구영업소주소": "exit_address",
        "출구영업소_주소": "exit_address",
        "상하행_구분": "direction",
        "출구진출일자": "exit_date",
        "구간전기차이용대수": "ev_count",
        "구간전체이용대수": "total_vehicle_count",
        "영업소간거리": "distance_km",
    })

    cols = [
        "entry_toll_code",
        "entry_toll_name",
        "entry_address",
        "exit_toll_code",
        "exit_toll_name",
        "exit_address",
        "direction",
        "exit_date",
        "ev_count",
        "total_vehicle_count",
        "distance_km",
    ]

    missing = [col for col in cols if col not in df.columns]
    if missing:
        raise KeyError(f"통행량 raw 누락 컬럼: {missing}")

    return df[cols].astype(str)


def truncate_raw_tables(engine):
    log("raw 테이블 초기화")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE raw_ev_charger_daily"))
        conn.execute(text("TRUNCATE TABLE raw_highway_traffic"))


def main():
    log("raw 적재 시작")

    engine = get_engine()
    charger_raw, traffic_raw = load_excel()

    charger_raw = prepare_raw_charger(charger_raw)
    traffic_raw = prepare_raw_traffic(traffic_raw)

    truncate_raw_tables(engine)

    charger_raw.to_sql(
        name="raw_ev_charger_daily",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi",
    )

    traffic_raw.to_sql(
        name="raw_highway_traffic",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi",
    )

    log(f"raw_ev_charger_daily 적재 완료: {charger_raw.shape}")
    log(f"raw_highway_traffic 적재 완료: {traffic_raw.shape}")


if __name__ == "__main__":
    main()