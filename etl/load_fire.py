import os
import sys
import csv
from pathlib import Path

from datetime import datetime
import pymysql

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # etl/ → 프로젝트 루트

import pandas as pd
from common.config import settings
from common.db import get_engine

# 1. .env 파일 로드
load_dotenv()

# 2. DB 접속 정보 설정
engine = get_engine()
db_connection = engine.raw_connection()
# db_connection = pymysql.connect(
#     host=os.getenv("DB_HOST", "localhost"),
#     user=os.getenv("DB_USER", "root"),
#     password=os.getenv("DB_PASSWORD", "mysql"),
#     database=os.getenv("DB_NAME", "ev_infra"),  # DB명이 다르면 수정하세요
#     charset="utf8mb4",
#     cursorclass=pymysql.cursors.DictCursor
# )

csv_path = settings.DATA_DIR / "신가을_전기차 화재 발생 현황_20241231.csv"

try:
    with db_connection.cursor() as cursor:
        # 3. CSV 파일 읽기 (utf-8 처리)
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            insert_query = """
                INSERT INTO ev_fire_records 
                (fire_year, fire_month, sido, ignition_main_category, ignition_sub_category, vehicle_location, ground_level, vehicle_status, ignition_point)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data_to_insert = []

            for row in reader:
                # 화재발생년월일(YYYY-MM-DD) 분리 프로세스
                raw_date = row['화재발생년월일']  # 예: '2024-01-08'
                date_obj = datetime.strptime(raw_date, "%Y-%m-%d")

                fire_year = date_obj.year  # 연도 추출 (int)
                fire_month = date_obj.month  # 월 추출 (int)

                # 데이터 매핑
                record = (
                    fire_year,
                    fire_month,
                    row['시도'],
                    row['발화요인대분류'],
                    row['발화요인소분류'],  # 소분류 구분
                    row['차량장소'],
                    row['지상지하'],
                    row['차량상태'],
                    row['차량발화지점']
                )
                data_to_insert.append(record)

            # 4. 대량 데이터를 한 번에 안전하게 삽입 (Bulk Insert)
            if data_to_insert:
                # 재실행 시 중복 누적(예: 두 번 돌리면 146건) 방지 — 기존 데이터 비우고 새로 적재
                cursor.execute("TRUNCATE TABLE ev_fire_records")
                cursor.executemany(insert_query, data_to_insert)
                db_connection.commit()
                print(f"성공: 총 {len(data_to_insert)}건의 데이터가 DB에 정상 입력되었습니다.")

except Exception as e:
    print(f"오류 발생: {e}")
    db_connection.rollback()

finally:
    db_connection.close()