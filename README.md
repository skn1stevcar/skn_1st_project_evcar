# skn_1st_project_evcar

전기차 / 교통 인프라 공공데이터 수집 → MySQL 적재 → Streamlit 시각화 팀 프로젝트.

---

## 📌 팀원 빠른 시작 (CSV 데이터가 있는 경우)

> 처음 합류하는 팀원은 여기서 시작하세요. 아래 순서대로만 따라하면 됩니다.

---

### STEP 0 — 준비

```bash
# 저장소 클론 (처음 한 번만)
git clone https://github.com/AhnJung-min/skn_1st_project_evcar.git
cd skn_1st_project_evcar

# 패키지 설치
pip install -r requirements.txt
```

`.env.example`을 복사해서 `.env`를 만들고 DB 비밀번호를 채웁니다.

```bash
copy .env.example .env   # Windows
```

```ini
# .env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=여기에_비밀번호_입력
DB_NAME=ev_infra
```

---

### STEP 1 — 내 데이터 파일 넣기

`data/` 폴더에 CSV 파일을 복사합니다.

```
data/
├── faq.json        ← 안정민 (건드리지 말 것)
└── 홍길동_ev.csv   ← 본인 파일 추가
```

> `_raw`가 파일명에 들어가면 gitignore가 자동으로 커밋 제외합니다.

---

### STEP 2 — 내 테이블 만들기 (`sql/schema.sql`)

`schema.sql` 하단 팀원 추가 영역에 본인 테이블을 추가하고 실행합니다.

```sql
-- [홍길동] 예시 테이블
CREATE TABLE IF NOT EXISTS ev_charger (
    id         INT            NOT NULL,
    station_nm VARCHAR(200)   NOT NULL  COMMENT '충전소명',
    addr       VARCHAR(300)   NULL      COMMENT '주소',
    lat        DECIMAL(10,7)  NULL      COMMENT '위도',
    lng        DECIMAL(10,7)  NULL      COMMENT '경도',
    created_at TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

```bash
# 로컬 DB에 반영 (처음 한 번 + 테이블 추가할 때마다)
mysql -u root -p < sql/schema.sql
```

---

### STEP 3 — 적재 스크립트 작성 (`etl/load_홍길동.py`)

아래 템플릿을 복사해서 파일명과 내용만 본인에 맞게 수정합니다.

```python
# etl/load_홍길동.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import settings
from common.db import get_engine

def main():
    # 1) 데이터 읽기
    df = pd.read_csv(settings.DATA_DIR / "홍길동_ev.csv", encoding="utf-8-sig")

    # 2) 컬럼명을 테이블 컬럼명으로 맞추기
    df = df.rename(columns={
        "충전소명": "station_nm",
        "주소":    "addr",
        "위도":    "lat",
        "경도":    "lng",
    })

    # 3) DB에 저장
    #    if_exists="append"  → 기존 데이터에 추가
    #    if_exists="replace" → 기존 데이터 삭제 후 재적재
    df.to_sql("ev_charger", con=get_engine(), if_exists="append", index=False)
    print(f"적재 완료: ev_infra.ev_charger ({len(df)}건)")

if __name__ == "__main__":
    main()
```

```bash
python etl/load_홍길동.py
```

---

### STEP 4 — 대시보드 페이지 만들기 (`app/pages/2_충전소현황.py`)

`app/pages/` 에 파일을 추가하면 사이드바에 자동으로 메뉴가 생깁니다.  
파일명 앞 숫자가 메뉴 순서입니다 (예: `2_충전소현황.py` → 두 번째 메뉴).

```python
# app/pages/2_충전소현황.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pages/는 parents[2]

import pandas as pd
import streamlit as st
from common.config import settings
from common.db import get_engine

st.set_page_config(page_title="충전소 현황", page_icon="⚡")
st.title("⚡ 전기차 충전소 현황")

@st.cache_data
def load_data():
    try:
        return pd.read_sql("SELECT * FROM ev_charger", get_engine())
    except Exception:
        # DB 없을 때 CSV로 대신 보여주기
        return pd.read_csv(settings.DATA_DIR / "홍길동_ev.csv", encoding="utf-8-sig")

df = load_data()
st.dataframe(df)
# 여기 아래에 본인 시각화 코드 작성
```

대시보드 실행:

```bash
streamlit run app/dashboard.py
```

---

### STEP 5 — 커밋 & 푸시

**본인이 만든 파일만** 골라서 올립니다. 다른 사람 파일을 건드리면 충돌이 납니다.

```bash
# 내 파일만 스테이징
git add data/홍길동_ev.csv
git add etl/load_홍길동.py
git add sql/schema.sql            # 내 테이블 DDL 추가했을 때만
git add app/pages/2_충전소현황.py

# 커밋
git commit -m "feat: [홍길동] 충전소 데이터 적재 및 대시보드 추가"

# push 전에 반드시 최신 코드 먼저 받기 (충돌 방지)
git pull origin main
git push origin main
```

---

## 디렉토리 구조

```
skn_1st_project_evcar/
│
├── common/                 ← 팀 공용 모듈 (모든 팀원이 import해서 씀)
│   ├── config.py           ← DB 접속 정보, 파일 경로 (settings 객체)
│   ├── db.py               ← get_engine() — DB 엔진 싱글턴
│   └── models.py           ← SQLAlchemy ORM 모델
│
├── data/                   ← 데이터 파일
│   ├── faq.json / faq.csv  ← [안정민] FAQ 데이터
│   └── *_raw.*             ← 원본 파일 (gitignore, 커밋 안 됨)
│
├── etl/                    ← 데이터 수집 · 적재 스크립트
│   ├── extract*.py         ← [안정민 전용] 크롤링
│   ├── transform.py        ← [안정민 전용] 정제
│   ├── load.py             ← [안정민] faq 적재
│   └── load_<이름>.py      ← [팀원] 본인 데이터 적재
│
├── sql/
│   └── schema.sql          ← DB 테이블 정의 (팀원 테이블도 여기 추가)
│
├── app/
│   ├── dashboard.py        ← [안정민] FAQ 대시보드 (메인 페이지)
│   └── pages/
│       └── <N>_<이름>.py   ← [팀원] 본인 대시보드 페이지
│
├── .env                    ← DB 비밀번호 (커밋 X)
├── .env.example            ← .env 템플릿 (커밋 O)
├── requirements.txt
└── README.md
```

---

## 공용 모듈 (`common/`) 사용법

DB 접속 코드를 직접 쓰지 말고 아래처럼 가져다 씁니다.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # etl/ 기준
# app/pages/ 파일은 parents[2]

from common.config import settings   # settings.DATA_DIR, settings.database_url
from common.db import get_engine     # SQLAlchemy 엔진 (싱글턴)
```

| 모듈 | 제공하는 것 | 사용 예 |
|---|---|---|
| `common.config` | `settings.DATA_DIR` — data/ 경로 | `settings.DATA_DIR / "파일.csv"` |
| `common.db` | `get_engine()` — DB 엔진 | `pd.read_sql("SELECT ...", get_engine())` |
| `common.models` | `Faq` ORM 클래스 | 필요한 경우 팀원 모델도 추가 가능 |

---

## 안정민 — FAQ 파이프라인

```bash
python etl/extract.py          # 한국교통안전공단 크롤링
python etl/extract_car365.py   # 자동차365 크롤링
python etl/extract_ev.py       # 무공해차 통합누리집 크롤링
python etl/transform.py        # 정제·병합 → faq.json / faq.csv
python etl/load.py             # MySQL 적재
```

| 출처 | 건수 |
|---|---|
| 한국교통안전공단 | 295건 |
| 자동차365 | 93건 |
| 무공해차 통합누리집 | 37건 |
| **합계** | **425건** |

---

## 담당 현황

| 담당 | 데이터셋 | 테이블 | 진행 |
|---|---|---|---|
| 안정민 | 자동차 FAQ (3개 사이트) | `faq` | ✅ |
| (팀원) | (본인 데이터셋) | (추가) | - |

---

## FAQ

**Q. DB 없이 대시보드를 볼 수 있나요?**  
네. DB 연결 실패 시 CSV 파일로 자동 폴백합니다. `except` 블록에 CSV 경로를 넣어두면 됩니다.

**Q. `.env`를 실수로 커밋하면 어떻게 되나요?**  
`.gitignore`에 등록되어 있어 `git add .`해도 자동 제외됩니다. 절대 강제로 추가하지 마세요.

**Q. `schema.sql`에서 충돌이 났어요.**  
여러 명이 건드리는 유일한 공유 파일입니다. push 전에 반드시 `git pull`을 먼저 해주세요.

**Q. `requirements.txt`에 패키지를 추가해도 되나요?**  
추가하고 같이 커밋해 주세요.
