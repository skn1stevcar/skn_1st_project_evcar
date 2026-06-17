# -*- coding: utf-8 -*-
"""
load.py — MySQL 적재(Load)

data/faq.json (transform.py 산출물) 을 ev_infra.faq 테이블에 적재한다.
DB 접속·설정·모델은 공용 모듈(common.*)을 사용한다.
테이블이 없으면 sql/schema.sql 의 DDL 로 먼저 생성해 둘 것.

  INSERT ... ON DUPLICATE KEY UPDATE 로 멱등(idempotent) 적재 → 재실행해도 중복 없음.

실행:
    python etl/load.py
"""

import json
import sys
from pathlib import Path

# 공용 모듈(common) import 를 위해 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.mysql import insert  # noqa: E402

from common.config import settings  # noqa: E402
from common.db import get_engine  # noqa: E402
from common.models import Faq  # noqa: E402

JSON_PATH = settings.DATA_DIR / "faq.json"


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        rows = json.load(f)

    # (source, id) 충돌 시 PK 외 컬럼만 갱신 → 멱등 적재
    stmt = insert(Faq).values(rows)
    upsert = stmt.on_duplicate_key_update(
        category=stmt.inserted.category,
        question=stmt.inserted.question,
        answer=stmt.inserted.answer,
        modified=stmt.inserted.modified,
    )

    with get_engine().begin() as conn:
        conn.execute(upsert)

    print(f"적재 완료: ev_infra.faq ← {JSON_PATH} ({len(rows)}건)")


if __name__ == "__main__":
    main()
