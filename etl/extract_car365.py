# -*- coding: utf-8 -*-
"""
extract_car365.py — 데이터 수집(Extract) · 자동차365(car365)

데이터셋: 자동차365 자주하는질문(FAQ)
원본 페이지: https://www.car365.go.kr/ccpt/comm/ntcn/faqView.do?bbsId=124

목록이 AJAX(POST /ccpt/comm/ntcn/selectFaqList.do)로 렌더링되므로
해당 엔드포인트를 페이지 단위로 호출해 원본을 data/faq_car365_raw.json 으로 저장한다.
정제·병합은 transform.py 가 맡는다. 외부 의존성은 requests 뿐.

car365 는 항목별 고유번호를 노출하지 않으므로, 질문 텍스트의 CRC32 해시로
출처 내에서 안정적인(재수집해도 동일한) id 를 생성한다.

실행:
    python etl/extract_car365.py                 # 전체 수집
    python etl/extract_car365.py --max-pages 2   # 앞 2페이지만(테스트)
"""

import argparse
import html
import json
import re
import sys
import time
import zlib
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_PATH = DATA_DIR / "faq_car365_raw.json"

SOURCE = "자동차365"
LIST_URL = "https://www.car365.go.kr/ccpt/comm/ntcn/selectFaqList.do"
DEFAULT_PARAMS = {"perPage": "10", "srchGubun": "1", "srchText": "", "pstClsfCd": "", "bbsId": "124"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.car365.go.kr/ccpt/comm/ntcn/faqView.do?bbsId=124",
}

# 한 FAQ 항목(<li class="pstTtlFaq">) 단위로 카테고리/질문/답변 추출
ITEM_RE = re.compile(
    r'<span class="category">(?P<cate>.*?)</span>'
    r'.*?<span class="question">(?P<q>.*?)</span>'
    r'.*?<div class="qna-view">(?P<answer>.*?)</div>',
    re.DOTALL,
)
TOTAL_PAGE_RE = re.compile(r'id="totalPageCnt"[^>]*>\s*(\d+)')
TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = TAG_RE.sub("", text)
    text = html.unescape(text).replace("\xa0", " ")
    return "\n".join(ln.rstrip() for ln in text.splitlines()).strip()


def _make_id(category: str, question: str) -> int:
    """카테고리+질문으로 출처 내 안정적 정수 id 생성(부호 있는 INT 범위).

    같은 질문이 서로 다른 카테고리에 별개 항목으로 존재하므로
    질문만으로는 충돌한다 → 카테고리를 함께 해시한다.
    """
    return zlib.crc32(f"{category}|{question}".encode("utf-8")) & 0x7FFFFFFF


def _parse_page(htmltext: str):
    rows = []
    for m in ITEM_RE.finditer(htmltext):
        category = _clean(m.group("cate"))
        question = _clean(m.group("q"))
        rows.append({
            "id": _make_id(category, question),
            "source": SOURCE,
            "category": category,
            "question": question,
            "answer": _clean(m.group("answer")),
            "modified": "",  # 목록에 수정일 미제공
        })
    return rows


def fetch_faq(max_pages=None, delay=0.5):
    session = requests.Session()
    rows, seen, page, total_pages = [], set(), 1, None
    while not (max_pages and page > max_pages):
        params = dict(DEFAULT_PARAMS, pageNo=str(page))
        try:
            resp = session.post(LIST_URL, data=params, headers=HEADERS, verify=False, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[!] {page}페이지 실패: {e}", file=sys.stderr)
            break

        text = resp.content.decode("utf-8", errors="replace")
        if total_pages is None:
            mt = TOTAL_PAGE_RE.search(text)
            total_pages = int(mt.group(1)) if mt else None

        items = _parse_page(text)
        new = [it for it in items if it["id"] not in seen]
        if not new:
            break
        for it in new:
            seen.add(it["id"])
        rows.extend(new)
        print(f"[+] {page}페이지: {len(new)}건 (누적 {len(rows)})")

        if total_pages and page >= total_pages:
            break
        page += 1
        time.sleep(delay)
    return rows


def main():
    ap = argparse.ArgumentParser(description="자동차365 FAQ 수집(Extract)")
    ap.add_argument("--max-pages", type=int, default=None)
    args = ap.parse_args()

    rows = fetch_faq(max_pages=args.max_pages)
    DATA_DIR.mkdir(exist_ok=True)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n원본 저장: {RAW_PATH} ({len(rows)}건)")


if __name__ == "__main__":
    main()
