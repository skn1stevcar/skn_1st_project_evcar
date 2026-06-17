# etl/load_car_num.py
"""general_num.csv + ev_num.csv 를 정제·병합해 car_ev_status 테이블에 적재한다.

- 일반 자동차(general_num.csv, cp949) 와 전기차(ev_num.csv, utf-8) 를
  (연월, 지역) 기준으로 합쳐 지역·월별 전기차 비중(ev_ratio)을 계산한다.
- 공용 모듈(common) 사용. 재실행해도 중복되지 않도록 적재 전 테이블을 비운다.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # etl/ → 프로젝트 루트

import pandas as pd
from sqlalchemy import text

from common.config import settings
from common.db import get_engine


def build_dataframe() -> pd.DataFrame:
    """CSV 두 개를 읽어 (연월, 지역) 단위로 병합한 DataFrame 을 만든다."""
    general_data = {}

    # [일반 자동차] 헤더 2줄 건너뜀, 천 단위 쉼표로 쪼개진 마지막 두 조각 결합
    with open(settings.DATA_DIR / "general_num.csv", encoding="cp949") as f:
        reader = csv.reader(f)
        next(reader)
        next(reader)
        for row in reader:
            if not row or len(row) < 4:
                continue
            연월, 지역 = row[0].strip(), row[1].strip()
            try:
                진짜총계 = int(row[-2].strip() + row[-1].strip())
            except ValueError:
                진짜총계 = int(row[-1].strip()) if row[-1].strip().isdigit() else 0
            general_data[(연월, 지역)] = general_data.get((연월, 지역), 0) + 진짜총계

    # [전기차] 헤더 1줄, 컬럼별(지역) 값을 일반 자동차와 매칭
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
                clean_val = row[idx].replace(",", "").strip()
                if not clean_val.isdigit():
                    continue
                전기차대수 = int(clean_val)
                전체대수 = general_data.get((연월, 지역))
                if 전체대수 is None:
                    continue
                비율 = round((전기차대수 / 전체대수) * 100, 2) if 전체대수 > 0 else 0.0
                rows.append({
                    "base_month": 연월,
                    "region": 지역,
                    "total_cars": 전체대수,
                    "ev_cars": 전기차대수,
                    "ev_ratio": 비율,
                })

    return pd.DataFrame(rows, columns=["base_month", "region", "total_cars", "ev_cars", "ev_ratio"])


def main():
    df = build_dataframe()
    engine = get_engine()

    # 재실행 시 중복 방지: schema.sql 로 만든 테이블 구조는 유지하고 데이터만 갈아끼움
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE car_ev_status"))
    df.to_sql("car_ev_status", con=engine, if_exists="append", index=False)

    print(f"적재 완료: ev_infra.car_ev_status ({len(df)}건)")
    print(df.head(10))


if __name__ == "__main__":
    main()
