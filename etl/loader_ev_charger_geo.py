import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # etl/ → 프로젝트 루트

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from common.db import get_engine


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# 처음엔 True로 10~30개만 테스트
TEST_MODE = False
TEST_ROWS = 30


def log(message):
    print(f"[INFO] {message}", flush=True)


def get_kakao_key():
    load_dotenv(ENV_PATH)

    key = os.getenv("KAKAO_REST_API_KEY")

    if not key:
        raise ValueError(".env 파일에 KAKAO_REST_API_KEY가 없습니다.")

    return key

def test_kakao_api(kakao_key):
    headers = {
        "Authorization": f"KakaoAK {kakao_key}"
    }

    params = {
        "query": "서울특별시 중구 세종대로 110"
    }

    response = requests.get(
        KAKAO_ADDRESS_URL,
        headers=headers,
        params=params,
        timeout=10
    )

    print("[DEBUG] Kakao status:", response.status_code)
    print("[DEBUG] Kakao response:", response.text[:500])

    if response.status_code != 200:
        raise RuntimeError("카카오 API 인증 실패. REST API KEY를 확인하세요.")


def load_station_address(engine):
    query = """
        SELECT
            station_name,
            MIN(address) AS address
        FROM ev_charging_analysis
        WHERE station_name IS NOT NULL
          AND station_name <> ''
          AND address IS NOT NULL
          AND address <> ''
        GROUP BY station_name
        ORDER BY station_name;
    """

    df = pd.read_sql(query, engine)

    if TEST_MODE:
        df = df.head(TEST_ROWS)

    return df


def geocode_address(address, kakao_key):
    if not address or str(address).lower() == "nan":
        return None, None, "fail", "empty address"

    headers = {
        "Authorization": f"KakaoAK {kakao_key}"
    }

    params = {
        "query": address
    }

    try:
        response = requests.get(
            KAKAO_ADDRESS_URL,
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None, None, "fail", f"HTTP {response.status_code}: {response.text[:100]}"

        data = response.json()
        documents = data.get("documents", [])

        if not documents:
            return None, None, "fail", "검색 결과 없음"

        first = documents[0]

        longitude = first.get("x")
        latitude = first.get("y")

        return latitude, longitude, "success", "성공"

    except Exception as e:
        return None, None, "fail", str(e)


def save_result(engine, result_df):
    with engine.begin() as conn:
        for _, row in result_df.iterrows():
            sql = text("""
                INSERT INTO ev_charger_geo (
                    station_name,
                    address,
                    latitude,
                    longitude,
                    api_status,
                    api_message
                )
                VALUES (
                    :station_name,
                    :address,
                    :latitude,
                    :longitude,
                    :api_status,
                    :api_message
                )
                ON DUPLICATE KEY UPDATE
                    address = VALUES(address),
                    latitude = VALUES(latitude),
                    longitude = VALUES(longitude),
                    api_status = VALUES(api_status),
                    api_message = VALUES(api_message);
            """)

            conn.execute(sql, {
                "station_name": none_if_nan(row["station_name"]),
                "address": none_if_nan(row["address"]),
                "latitude": none_if_nan(row["latitude"]),
                "longitude": none_if_nan(row["longitude"]),
                "api_status": none_if_nan(row["api_status"]),
                "api_message": none_if_nan(row["api_message"]),
            })


def main():
    log("충전소 주소 → 위도/경도 변환 시작")

    engine = get_engine()
    kakao_key = get_kakao_key()

    test_kakao_api(kakao_key)

    station_df = load_station_address(engine)

    log(f"API 호출 대상 충전소 수: {len(station_df)}")

    results = []

    for idx, row in station_df.iterrows():
        station_name = row["station_name"]
        address = row["address"]

        log(f"{idx + 1}/{len(station_df)} | {station_name} | {address}")

        latitude, longitude, api_status, api_message = geocode_address(
            address,
            kakao_key
        )

        results.append({
            "station_name": station_name,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "api_status": api_status,
            "api_message": api_message,
        })

        # API 과호출 방지
        time.sleep(0.2)

    result_df = pd.DataFrame(results)

    save_result(engine, result_df)

    log("좌표 저장 완료")
    print(result_df["api_status"].value_counts(dropna=False))

def none_if_nan(value):
    if pd.isna(value):
        return None
    return value

if __name__ == "__main__":
    main()