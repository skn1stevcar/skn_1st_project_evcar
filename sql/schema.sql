-- ============================================================
--  ev_infra 데이터베이스 스키마
--  팀 공용 DB. 각 팀원은 자신의 데이터셋 테이블을 아래에 추가한다.
-- ============================================================

CREATE DATABASE IF NOT EXISTS ev_infra
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ev_infra;

-- ------------------------------------------------------------
--  [안정민] 한국교통안전공단 일반분야 FAQ
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faq (
    id          INT             NOT NULL COMMENT '원본 FAQ 번호(출처별 고유)',
    source      VARCHAR(100)    NOT NULL DEFAULT '한국교통안전공단' COMMENT '크롤링 출처 사이트',
    category    VARCHAR(50)     NULL     COMMENT '분류(자동차검사·도로안전 등)',
    question    VARCHAR(500)    NOT NULL COMMENT '질문(제목)',
    answer      TEXT            NULL     COMMENT '답변(본문)',
    modified    DATE            NULL     COMMENT '마지막 수정일',
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP COMMENT '적재 시각',
    PRIMARY KEY (source, id),
    KEY idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='자동차 관련 사이트 FAQ(출처별 통합)';

-- ------------------------------------------------------------
--  [팀원 추가 영역] 본인 데이터셋 테이블을 여기에 정의하세요.
--  예) CREATE TABLE IF NOT EXISTS ev_charger ( ... );
-- ------------------------------------------------------------
