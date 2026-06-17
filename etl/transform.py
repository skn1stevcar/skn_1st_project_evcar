# -*- coding: utf-8 -*-
"""
transform.py — 정제·정규화·병합(Transform)

각 출처의 원본(raw) JSON 을 읽어 공통 스키마로 정제하고,
기존 data/faq.json 에 (source, id) 기준으로 upsert(병합)한 뒤
data/faq.json, data/faq.csv 로 저장한다.

  - 한국교통안전공단(faq_raw.json): 제목에 박힌 [분류] 를 category/question 으로 분리
  - 자동차365(faq_car365_raw.json): category/question 이 이미 분리되어 있음

기존 faq.json 을 베이스로 삼으므로, 한 출처만 다시 수집·정제해도
다른 출처의 데이터는 그대로 보존된다.

실행:
    python etl/transform.py
"""

import csv
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
JSON_PATH = DATA_DIR / "faq.json"
CSV_PATH = DATA_DIR / "faq.csv"

# 정제 대상 원본 파일들(있는 것만 처리)
RAW_FILES = ["faq_raw.json", "faq_car365_raw.json", "faq_ev_raw.json"]

CATE_RE = re.compile(r"^\s*\[(?P<cate>[^\]]+)\]\s*(?P<q>.*)$", re.DOTALL)
COLUMNS = ["id", "source", "category", "question", "answer", "modified"]

DEFAULT_SOURCE = "한국교통안전공단"


def transform_row(r):
    """원본 1건을 공통 스키마로 정제.

    - title 키가 있으면(교통안전공단) 제목에서 [분류] 를 분리
    - 그 외(자동차365 등)는 category/question 이 이미 분리되어 있음
    """
    if "title" in r:
        title = (r.get("title") or "").strip()
        category, question = "", title
        m = CATE_RE.match(title)
        if m:
            category = m.group("cate").strip()
            question = m.group("q").strip()
    else:
        category = (r.get("category") or "").strip()
        question = (r.get("question") or "").strip()

    return {
        "id": int(r["id"]),
        "source": (r.get("source") or DEFAULT_SOURCE).strip(),
        "category": category,
        "question": question,
        "answer": (r.get("answer") or "").strip(),
        "modified": r.get("modified") or None,
    }


def load_existing():
    """기존 faq.json 을 (source, id) → row 딕셔너리로 로드(없으면 빈 dict)."""
    if not JSON_PATH.exists():
        return {}
    with open(JSON_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    return {(r.get("source", DEFAULT_SOURCE), r["id"]): r for r in rows}


def main():
    merged = load_existing()  # 삽입 순서 유지(기존 → 신규 순)

    processed = 0
    for fname in RAW_FILES:
        path = DATA_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            raw_rows = json.load(f)
        for r in raw_rows:
            row = transform_row(r)
            merged[(row["source"], row["id"])] = row
            processed += 1
        print(f"[+] {fname}: {len(raw_rows)}건 정제·병합")

    rows = list(merged.values())

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    by_source = {}
    for r in rows:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    summary = ", ".join(f"{s} {n}건" for s, n in by_source.items())
    print(f"\n정제 완료: {JSON_PATH}, {CSV_PATH} (총 {len(rows)}건 · {summary})")


if __name__ == "__main__":
    main()
