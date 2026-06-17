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
--  [신가을] 전기차 화재 발생 현황 통합 테이블 (역정규화 빌드)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `ev_fire_records` (
    `id`                     INT AUTO_INCREMENT  NOT NULL COMMENT '화재사고 고유 ID',
    `fire_year`              INT                 NOT NULL COMMENT '화재발생연',
    `fire_month`             INT                 NOT NULL COMMENT '월',
    `sido`                   VARCHAR(50)         NOT NULL COMMENT '시도',
    `ignition_main_category` VARCHAR(50)         NOT NULL COMMENT '발화요인 대분류',
    `ignition_sub_category`  VARCHAR(100)        NOT NULL COMMENT '발화요인 소분류',
    `vehicle_location`       VARCHAR(50)         NULL     COMMENT '차량장소',
    `ground_level`           VARCHAR(20)         NULL     COMMENT '지상지하',
    `vehicle_status`         VARCHAR(50)         NULL     COMMENT '차량상태',
    `ignition_point`         VARCHAR(50)         NULL     COMMENT '차량발화지점',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='전기차 화재 발생 현황 통합';

-- ------------------------------------------------------------
--  [김길환] 전체 자동차 대수 대비 전기차 비중 데이터 비교
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS car_ev_status (
    id          INT          AUTO_INCREMENT NOT NULL COMMENT '행 고유 ID',
    base_month  VARCHAR(7)   NOT NULL COMMENT '기준 연월(YYYY-MM)',
    region      VARCHAR(50)  NOT NULL COMMENT '지역(시도)',
    total_cars  INT          NOT NULL COMMENT '총 자동차 등록 대수',
    ev_cars     INT          NOT NULL COMMENT '전기차 등록 대수',
    ev_ratio    FLOAT        NOT NULL COMMENT '전기차 비중(%)',
    PRIMARY KEY (id),
    KEY idx_month (base_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='전체 자동차 대비 전기차 비중(지역·월별)';

-- ------------------------------------------------------------
--  [팀원 추가 영역] 본인 데이터셋 테이블을 여기에 정의하세요.
--  예) CREATE TABLE IF NOT EXISTS ev_charger ( ... );
-- ------------------------------------------------------------