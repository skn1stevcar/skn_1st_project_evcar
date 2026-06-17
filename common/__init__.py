# -*- coding: utf-8 -*-
"""
common — 팀 공용 모듈

ev_infra 프로젝트의 모든 ETL/대시보드가 공유하는 설정·DB·모델.

    from common.config import settings     # 환경설정(.env)
    from common.db import get_engine, get_session   # DB 접속
    from common.models import Faq           # ORM 모델

스크립트(etl/*, app/*)에서 import 하려면 프로젝트 루트가 sys.path 에 있어야 한다.
각 스크립트 상단에 다음 한 줄을 둔다:

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ 은 parents[1]
"""
