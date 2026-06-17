# -*- coding: utf-8 -*-
"""
db.py — 공용 DB 접속

settings.database_url 로 SQLAlchemy 엔진을 만들고, 프로세스 내에서 재사용한다.
다른 모듈은 `from common.db import get_engine` (또는 get_session) 로 가져다 쓴다.
"""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from common.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """공용 SQLAlchemy 엔진(싱글턴). pool_pre_ping 으로 끊긴 커넥션 자동 복구."""
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine())


def get_session() -> Session:
    """새 ORM 세션 반환. 사용 후 close() 하거나 with 문으로 감싼다."""
    return _session_factory()()
