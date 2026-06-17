# -*- coding: utf-8 -*-
"""
models.py — 공용 ORM 모델

ev_infra DB 테이블을 SQLAlchemy ORM 으로 정의한다.
테이블 생성(DDL)의 진실원천은 여전히 sql/schema.sql 이며, 이 모델은 그것을
파이썬에서 다루기 위한 매핑이다(읽기/적재에 사용). 컬럼은 schema.sql 과 일치시킬 것.

팀원은 본인 테이블을 이 파일 하단에 ORM 모델로 추가하면 된다(선택).
"""

from sqlalchemy import Column, Date, Integer, String, Text, TIMESTAMP, Index, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Faq(Base):
    """[안정민] 자동차 관련 사이트 FAQ(출처별 통합). PK = (source, id)."""

    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, nullable=False, comment="원본 FAQ 번호(출처별 고유)")
    source = Column(String(100), primary_key=True, nullable=False,
                    server_default="한국교통안전공단", comment="크롤링 출처 사이트")
    category = Column(String(50), nullable=True, comment="분류(자동차검사·도로안전 등)")
    question = Column(String(500), nullable=False, comment="질문(제목)")
    answer = Column(Text, nullable=True, comment="답변(본문)")
    modified = Column(Date, nullable=True, comment="마지막 수정일")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment="적재 시각")

    __table_args__ = (
        Index("idx_category", "category"),
        {"comment": "자동차 관련 사이트 FAQ(출처별 통합)"},
    )

    def __repr__(self):
        return f"<Faq source={self.source!r} id={self.id} q={self.question[:20]!r}>"


# ------------------------------------------------------------
#  [팀원 추가 영역] 본인 테이블 ORM 모델을 여기에 정의하세요(선택).
#  예) class EvCharger(Base): __tablename__ = "ev_charger"; ...
# ------------------------------------------------------------
