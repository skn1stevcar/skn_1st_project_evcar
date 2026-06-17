# snk_1st_project_evcar

전기차/교통 인프라 공공데이터 수집 → MySQL 적재 → Streamlit 시각화 팀 프로젝트.
공용 데이터베이스 이름은 **`ev_infra`** 로 통일한다. 각 팀원은 자신이 수집한
데이터셋을 같은 DB의 별도 테이블로 적재하고, 대시보드 페이지를 구성한다.

---

## 프로젝트 구조

```
project/
├── data/                        # 정제 완료된 데이터만 커밋 (*_raw.* 는 git 제외)
│   ├── faq.json / faq.csv       # [안정민] FAQ 정제본
│   └── <본인_데이터>.json       # 각자 정제본 추가
├── etl/
│   ├── extract.py               # [안정민] FAQ 수집
│   ├── transform.py             # [안정민] FAQ 정제
│   ├── load.py                  # [안정민] FAQ → ev_infra.faq 적재
│   ├── extract_ev_charger.py    # [안정민] 충전소 API 수집 참고
│   ├── extract_<이름>.py        # 팀원 추가 ▶ 수집
│   ├── transform_<이름>.py      # 팀원 추가 ▶ 정제
│   └── load_<이름>.py           # 팀원 추가 ▶ 적재
├── sql/
│   └── schema.sql               # ev_infra DDL — 팀원 테이블도 여기에 추가
├── app/
│   ├── dashboard.py             # [안정민] FAQ 대시보드 (메인 진입점)
│   └── pages/
│       └── <번호_이름>.py       # 팀원 추가 ▶ 본인 페이지 (Streamlit 멀티페이지)
├── .env.example                 # DB 접속 정보 템플릿
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 빠른 시작 (공통)

```bash
# 1) 저장소 클론
git clone https://github.com/AhnJung-min/snk_1st_project_evcar.git
cd snk_1st_project_evcar

# 2) 의존성 설치
pip install -r requirements.txt

# 3) DB 접속 정보 설정 (.env 는 git 제외 — 절대 커밋하지 말 것)
cp .env.example .env
# .env 파일을 열어 DB_HOST / DB_USER / DB_PASSWORD 값을 채운다

# 4) ev_infra DB + 테이블 생성 (처음 한 번만)
mysql -u root -p < sql/schema.sql

# 5) 대시보드 실행
streamlit run app/dashboard.py
```

> **DB 없이 화면만 보고 싶을 때** — DB 접속이 안 되면 `data/faq.json` 으로
> 자동 폴백하므로 MySQL 없이도 대시보드 확인이 가능하다.

---

## 팀원 작업 가이드

> 공용 저장소이므로 **같은 파일을 여러 명이 동시에 수정하면 충돌**이 발생한다.
> 아래 규칙을 따르면 각자 독립적으로 작업하면서 충돌을 피할 수 있다.

### 1단계 — 저장소 최신화

작업 시작 전 항상 pull 한다.

```bash
git pull origin main
```

---

### 2단계 — 데이터 수집 스크립트 추가 (`etl/`)

**이름 규칙: `etl/extract_<본인이름 또는 데이터셋명>.py`**

- 기존 `extract.py / transform.py / load.py` 는 FAQ 전용이므로 **수정 금지**.
- 각자의 파일을 새로 만든다.

```
etl/
├── extract.py          ← 건드리지 말 것 (안정민 FAQ 전용)
├── extract_<이름>.py   ← 본인이 추가 (수집)
├── transform_<이름>.py ← 본인이 추가 (정제)
└── load_<이름>.py      ← 본인이 추가 (DB 적재)
```

파일 내부에서 DB 연결이 필요하면 `load.py` 의 `get_engine()` 패턴을 그대로 복사해 쓴다.

```python
# 예시: etl/load_mydata.py 최소 골격
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def get_engine():
    user = os.getenv("DB_USER", "root")
    pw   = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "ev_infra")
    return create_engine(f"mysql+pymysql://{user}:{pw}@{host}:{port}/{name}?charset=utf8mb4")

def main():
    rows = json.load(open(ROOT / "data" / "mydata.json", encoding="utf-8"))
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO my_table ... ON DUPLICATE KEY UPDATE ..."), rows)

if __name__ == "__main__":
    main()
```

---

### 3단계 — 테이블 DDL 추가 (`sql/schema.sql`)

`schema.sql` 하단 "팀원 추가 영역" 에 본인 테이블의 `CREATE TABLE` 을 추가한다.

```sql
-- 예시
CREATE TABLE IF NOT EXISTS my_table (
    id         INT          NOT NULL,
    name       VARCHAR(200) NOT NULL,
    lat        DECIMAL(10,7) NULL COMMENT '위도',
    lng        DECIMAL(10,7) NULL COMMENT '경도',
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**주의**: 다른 사람 테이블(`faq` 등)은 수정하지 않는다.

---

### 4단계 — 정제 데이터 저장 (`data/`)

| 파일 | 커밋 여부 | 설명 |
|---|---|---|
| `data/<이름>.json` | ✅ 커밋 | 정제 완료된 데이터 |
| `data/<이름>.csv`  | ✅ 커밋 | 동일 데이터 CSV 버전 |
| `data/<이름>_raw.json` | ❌ 커밋 금지 | 원본(용량 크고 민감) — `.gitignore` 처리됨 |

---

### 5단계 — 대시보드 페이지 추가 (`app/pages/`)

Streamlit 멀티페이지 기능을 사용한다.  
`app/pages/` 폴더에 파일을 추가하면 사이드바에 자동으로 메뉴가 생긴다.

```
app/
├── dashboard.py          ← 메인 페이지 (수정 금지)
└── pages/
    ├── 2_충전소.py        ← 팀원 추가 예시
    └── 3_<본인주제>.py   ← 파일명 앞 숫자가 메뉴 순서
```

페이지 파일 최소 골격:

```python
# app/pages/2_충전소.py
import streamlit as st

st.set_page_config(page_title="충전소 현황", page_icon="⚡")
st.title("⚡ 전기차 충전소 현황")

# 여기에 본인 대시보드 내용 작성
```

---

### 6단계 — 커밋 & 푸시

```bash
# 본인이 추가/수정한 파일만 명시적으로 add (git add . 는 실수 위험)
git add etl/extract_<이름>.py etl/transform_<이름>.py etl/load_<이름>.py
git add sql/schema.sql
git add data/<이름>.json data/<이름>.csv
git add app/pages/<번호_이름>.py

git commit -m "feat: [<이름>] <데이터셋명> 수집·적재·대시보드 추가"
git push origin main
```

> push 전에 다시 `git pull origin main` 으로 최신화한 뒤 push 하면 충돌 가능성이 줄어든다.

---

## 담당 및 진행 현황

| 담당 | 데이터셋 | ETL 파일 | 테이블 | 페이지 | 진행 |
|---|---|---|---|---|---|
| 안정민 | 교통안전공단 FAQ | `extract.py` · `transform.py` · `load.py` | `faq` | `dashboard.py` | ✅ 완료 |
| (팀원) | (본인 데이터셋) | `extract_<이름>.py` 등 | (추가) | `pages/<번호_이름>.py` | - |

---

## 자주 묻는 것들

**Q. `.env` 파일을 커밋하면 안 되나요?**  
A. `.gitignore` 에 등록되어 있으므로 `git add .env` 해도 무시된다. DB 비밀번호가 GitHub에 올라가면 안 되니 절대 강제 추가하지 말 것.

**Q. DB가 없는데 대시보드를 실행할 수 있나요?**  
A. 가능하다. DB 연결에 실패하면 `data/faq.json` 을 자동으로 읽는다. 본인 데이터도 `data/<이름>.json` 을 준비해두면 같은 방식으로 폴백 처리하도록 페이지 코드를 작성하면 된다.

**Q. requirements.txt 에 패키지를 추가해도 되나요?**  
A. 본인 작업에 필요한 패키지가 있으면 `requirements.txt` 에 추가하고 커밋한다.  
단, 버전을 너무 고정(`==`)하면 다른 환경에서 충돌날 수 있으니 특별한 이유가 없으면 버전 없이 이름만 적는다.
