# -*- coding: utf-8 -*-
"""
config.py — 공용 환경설정(Settings)

프로젝트 루트의 .env 를 읽어 DB 접속 정보와 공용 경로를 한 곳에서 제공한다.
다른 모듈은 `from common.config import settings` 로 가져다 쓴다.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# common/ 의 부모가 프로젝트 루트
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class Settings:
    """환경설정 모음. 값은 .env(없으면 기본값)에서 읽는다."""

    # --- 경로 ---
    ROOT = ROOT
    DATA_DIR = ROOT / "data"

    # --- DB 접속 ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mysql")
    DB_NAME = os.getenv("DB_NAME", "ev_infra")

    @property
    def database_url(self) -> str:
        """SQLAlchemy 접속 URL. 비밀번호의 특수문자는 URL 인코딩한다."""
        return (
            f"mysql+pymysql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
