# skn_1st_project_evcar

전기차 / 교통 인프라 공공데이터 수집 → MySQL 적재 → Streamlit 시각화 팀 프로젝트.

---

## 디렉토리 구조

```
skn_1st_project_evcar/
│
├── common/                 ← 팀 공용 모듈 (DB 연결·설정·모델)
│   ├── config.py           ← .env 읽어서 DB 접속 정보 제공
│   ├── db.py               ← get_engine() / get_session()
│   └── models.py           ← SQLAlchemy ORM 모델 (테이블 정의)
│
├── data/                   ← 데이터 파일 보관
│   ├── faq.json            ← [안정민] FAQ 정제본 (커밋 O)
│   ├── faq.csv             ← [안정민] FAQ 정제본 (커밋 O)
│   └── *_raw.json/csv      ← 수집 원본 (커밋 X, gitignore)
│
├── etl/                    ← [안정민 전용] 데이터 수집·정제·적재
│   ├── extract.py          ← 한국교통안전공단 FAQ 크롤링
│   ├── extract_car365.py   ← 자동차365 FAQ 크롤링
│   ├── extract_ev.py       ← 무공해차 통합누리집 FAQ 크롤링
│   ├── transform.py        ← 3개 출처 정제 후 faq.json/csv 저장
│   └── load.py             ← faq.json → MySQL ev_infra.faq 적재
│
├── sql/
│   └── schema.sql          ← DB 테이블 DDL (팀원 테이블 여기에 추가)
│
├── app/
│   ├── dashboard.py        ← [안정민] FAQ 검색 대시보드 (메인)
│   └── pages/              ← 팀원 대시보드 페이지 추가 위치
│       └── 예) 2_충전소현황.py
│
├── .env                    ← DB 비밀번호 등 (커밋 X, gitignore)
├── .env.example            ← .env 템플릿 (커밋 O)
├── requirements.txt
└── README.md
```

---

## 기능 설명

### 공용 모듈 (`common/`)

모든 팀원이 DB에 접근할 때 공통으로 쓰는 모듈입니다.
자신의 파일 상단에서 아래와 같이 가져다 씁니다.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 루트 경로 등록

from common.config import settings   # DB 접속 정보, 경로
from common.db import get_engine     # DB 엔진 (싱글턴)
```

| 파일 | 역할 |
|---|---|
| `config.py` | `.env` 값을 읽어 `settings.database_url` 등 제공 |
| `db.py` | `get_engine()` — SQLAlchemy 엔진 싱글턴, 커넥션 자동 복구 |
| `models.py` | `Faq` ORM 모델. 팀원 테이블 모델도 여기에 추가 가능 |

> `app/pages/` 하위 파일은 루트까지 두 단계 올라가야 하므로 `parents[2]` 로 씁니다.

---

### 안정민 — FAQ 파이프라인 (`etl/`)

크롤링부터 DB 적재까지 아래 순서로 실행합니다.

```
1. 수집  python etl/extract.py           # 한국교통안전공단
         python etl/extract_car365.py    # 자동차365
         python etl/extract_ev.py        # 무공해차 통합누리집

2. 정제  python etl/transform.py         # 3개 원본 → faq.json / faq.csv

3. 적재  python etl/load.py              # faq.json → MySQL ev_infra.faq
```

수집된 FAQ 현황 (2025년 기준):

| 출처 | 건수 | 카테고리 예시 |
|---|---|---|
| 한국교통안전공단 | 295건 | 자동차검사, 도로안전 등 |
| 자동차365 | 93건 | 중고차등록, 자동차검사 등 |
| 무공해차 통합누리집 | 37건 | 충전소 이용, 수소충전소 인프라 등 |
| **합계** | **425건** | |

> **크롤링은 안정민 님만 실행**합니다. 팀원은 `load.py`만 실행하거나, `faq.json`을 그대로 사용합니다.

---

### FAQ 대시보드 (`app/dashboard.py`)

```bash
streamlit run app/dashboard.py
```

- DB 연결 성공 시 MySQL에서 데이터 읽음
- DB 없을 때는 `data/faq.json`으로 자동 폴백
- **출처 → 카테고리 2단계 필터** 지원
- 키워드 검색 (제목 / 내용 / 전체), 카드형 / 슬라이드형 보기

---

## 처음 시작하기 (팀원 공통)

```bash
# 1. 클론
git clone https://github.com/AhnJung-min/skn_1st_project_evcar.git
cd skn_1st_project_evcar

# 2. 패키지 설치
pip install -r requirements.txt

# 3. DB 접속 정보 설정
copy .env.example .env   # Windows
# .env 파일을 열어 DB_PASSWORD 입력

# 4. DB·테이블 생성 (처음 한 번만)
mysql -u root -p < sql/schema.sql

# 5. FAQ 데이터 적재 (선택 — DB 사용 시)
python etl/load.py

# 6. 대시보드 실행
streamlit run app/dashboard.py
```

---

## 팀원 작업 순서

### 1. 최신 코드 받기
```bash
git pull origin main
```

### 2. 내 데이터 파일을 `data/`에 넣기

```
data/
├── faq.json          ← 안정민 (건드리지 말 것)
└── 홍길동_ev.csv     ← 본인 파일 추가
```

파일명에 `_raw`가 들어가면 gitignore가 자동으로 커밋에서 제외합니다.

### 3. 내 테이블 DDL을 `sql/schema.sql`에 추가

```sql
-- [홍길동] 충전소 테이블
CREATE TABLE IF NOT EXISTS ev_charger (
    id          INT           NOT NULL,
    station_nm  VARCHAR(200)  NOT NULL,
    addr        VARCHAR(300)  NULL,
    lat         DECIMAL(10,7) NULL,
    lng         DECIMAL(10,7) NULL,
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

로컬 DB에 반영:
```bash
mysql -u root -p < sql/schema.sql
```

### 4. 적재 스크립트 작성 (`etl/load_홍길동.py`)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import settings
from common.db import get_engine

def main():
    df = pd.read_csv(settings.DATA_DIR / "홍길동_ev.csv", encoding="utf-8-sig")
    df.rename(columns={"충전소명": "station_nm", "주소": "addr"}, inplace=True)
    df.to_sql("ev_charger", con=get_engine(), if_exists="append", index=False)
    print(f"적재 완료: {len(df)}건")

if __name__ == "__main__":
    main()
```

```bash
python etl/load_홍길동.py
```

### 5. 대시보드 페이지 추가 (`app/pages/2_충전소현황.py`)

파일명 앞 숫자가 사이드바 순서가 됩니다.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd, streamlit as st
from common.config import settings
from common.db import get_engine

st.set_page_config(page_title="충전소 현황", page_icon="⚡")
st.title("⚡ 전기차 충전소 현황")

@st.cache_data
def load_data():
    try:
        return pd.read_sql("SELECT * FROM ev_charger", get_engine())
    except Exception:
        return pd.read_csv(settings.DATA_DIR / "홍길동_ev.csv", encoding="utf-8-sig")

st.dataframe(load_data())
```

### 6. 커밋 & 푸시

**본인이 추가한 파일만** 명시적으로 add합니다.

```bash
git add data/홍길동_ev.csv etl/load_홍길동.py sql/schema.sql app/pages/2_충전소현황.py
git commit -m "feat: [홍길동] 충전소 데이터 적재 및 대시보드 추가"
git pull origin main   # push 전 최신화 (충돌 방지)
git push origin main
```

---

## 담당 현황

| 담당 | 데이터셋 | 주요 파일 | 테이블 | 진행 |
|---|---|---|---|---|
| 안정민 | 자동차 FAQ 3개 사이트 | `etl/extract*.py` `etl/load.py` | `faq` | ✅ |
| (팀원) | (본인 데이터셋) | `etl/load_<이름>.py` | (추가) | - |

---

## 자주 묻는 것들

**Q. `.env`를 커밋하면 안 되나요?**
`.gitignore`에 등록되어 있어 `git add .`해도 자동으로 제외됩니다. DB 비밀번호가 GitHub에 올라가면 안 되니 절대 강제 추가하지 마세요.

**Q. DB 없이 대시보드를 실행할 수 있나요?**
네. DB 연결 실패 시 `data/faq.json`으로 자동 폴백합니다. DB 없이도 FAQ 검색은 동작합니다.

**Q. `requirements.txt`에 패키지를 추가해도 되나요?**
필요한 패키지가 있으면 추가하고 같이 커밋해 주세요.

**Q. `schema.sql`에서 충돌이 났어요.**
여러 명이 수정할 수 있는 유일한 공유 파일입니다. push 전 반드시 `git pull`을 먼저 해서 최신화하세요.
