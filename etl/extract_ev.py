# -*- coding: utf-8 -*-
"""
extract_ev.py — 데이터 수집(Extract) · 무공해차 통합누리집(ev.or.kr)

데이터셋: 무공해차 통합누리집 참여마당 FAQ
원본 페이지: https://www.ev.or.kr/nportal/partcptn/initFaqAction.do

이 사이트는 pnp4web 봇 차단 JS 로 보호되어, 첫 요청은 난독화된 JS 챌린지를
돌려준다. 같은 세션으로 initFaqAction.do 를 한 번 더 호출(쿠키 워밍)한 뒤
목록 JSON API(POST /nportal/infoGarden/selectBBSList.ajax)를 페이지 단위로
호출해 원본을 data/faq_ev_raw.json 으로 저장한다. 외부 의존성은 requests 뿐.

정제·병합은 transform.py 가 맡는다.

  - 고유 id : ARTC_ID(원본 게시글 번호)
  - 카테고리: SMLCLS10 (1·null→충전소 이용, 2→완속충전기 설치지원 사업, 3→수소충전소 인프라 사업)
  - 수정일 : INS_DT(등록일) 앞 10자리(YYYY-MM-DD)

실행:
    python etl/extract_ev.py                 # 전체 수집
    python etl/extract_ev.py --max-pages 1   # 앞 1페이지만(테스트)
"""

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_PATH = DATA_DIR / "faq_ev_raw.json"

SOURCE = "무공해차 통합누리집"
INIT_URL = "https://www.ev.or.kr/nportal/partcptn/initFaqAction.do"
LIST_URL = "https://www.ev.or.kr/nportal/infoGarden/selectBBSList.ajax"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Referer": INIT_URL, "X-Requested-With": "XMLHttpRequest"}
PER_PAGE = 10

# SMLCLS10 코드 → 카테고리명 (null·1: 충전소 이용)
CATE_MAP = {"1": "충전소 이용", "2": "완속충전기 설치지원 사업", "3": "수소충전소 인프라 사업"}

TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _clean(text: str) -> str:
    text = TAG_RE.sub("", text or "")
    text = html.unescape(text).replace("\xa0", " ")
    return "\n".join(ln.rstrip() for ln in text.splitlines()).strip()


def _category(smlcls10) -> str:
    return CATE_MAP.get(str(smlcls10 or "1"), "충전소 이용")


def _modified(ins_dt) -> str:
    m = DATE_RE.search(str(ins_dt or ""))
    return m.group(1) if m else ""


def _warm_session() -> requests.Session:
    """봇 차단 우회: 세션 쿠키(JSESSIONID)를 받기 위해 초기 페이지 1회 호출."""
    s = requests.Session()
    s.get(INIT_URL, headers={"User-Agent": UA}, verify=False, timeout=20)
    return s


def fetch_faq(max_pages=None, delay=0.5):
    s = _warm_session()
    rows, seen, page, total = [], set(), 1, None
    while not (max_pages and page > max_pages):
        data = {
            "title": "공지사항", "ARTC_ID": "", "BLBD_ID": "faq", "SMLCLS10": "",
            "replyYn": "N", "srecordCountPerPage": str(PER_PAGE),
            "spageNo": str(page), "spageSize": str(PER_PAGE),
            "searchType": "conAndtit", "searchValue": "",
        }
        try:
            resp = s.post(LIST_URL, data=data, headers=HEADERS, verify=False, timeout=20)
            resp.raise_for_status()
            obj = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"[!] {page}페이지 실패: {e}", file=sys.stderr)
            break

        if total is None:
            total = obj.get("page", {}).get("_listCount", 0)

        items = obj.get("list", []) or []
        new = []
        for it in items:
            aid = it.get("ARTC_ID")
            if aid is None or aid in seen:
                continue
            seen.add(aid)
            new.append({
                "id": int(aid),
                "source": SOURCE,
                "category": _category(it.get("SMLCLS10")),
                "question": _clean(it.get("TITL")),
                "answer": _clean(it.get("ARTC_CNTNS")),
                "modified": _modified(it.get("INS_DT")),
            })
        if not new:
            break
        rows.extend(new)
        print(f"[+] {page}페이지: {len(new)}건 (누적 {len(rows)} / 전체 {total})")

        if total and len(rows) >= total:
            break
        page += 1
        time.sleep(delay)
    return rows


def main():
    ap = argparse.ArgumentParser(description="무공해차 통합누리집 FAQ 수집(Extract)")
    ap.add_argument("--max-pages", type=int, default=None)
    args = ap.parse_args()

    rows = fetch_faq(max_pages=args.max_pages)
    DATA_DIR.mkdir(exist_ok=True)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n원본 저장: {RAW_PATH} ({len(rows)}건)")


if __name__ == "__main__":
    main()
