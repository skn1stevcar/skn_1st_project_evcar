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
--  [김길환?] 고속도로 전기차 통행량 · 충전 수요 분석
--    raw_* : 엑셀 원본 적재용(문자 그대로) → 정제 INSERT 는 etl/transform_charging_traffic.sql
--    ev_*_analysis : 정제·집계된 분석 테이블
--    ev_charger_geo : 충전소 좌표(카카오 주소검색 API 결과)
--    ev_charging_map_analysis : 지도 시각화용 VIEW
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_ev_charger_daily (
    charge_start_date  VARCHAR(50),
    station_name       VARCHAR(150),
    address            VARCHAR(255),
    charger_id         VARCHAR(100),
    charger_type       VARCHAR(100),
    charge_count       VARCHAR(50),
    total_charge_kwh   VARCHAR(50),
    total_charge_time  VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='충전소 일별 원본(문자 그대로 적재)';

CREATE TABLE IF NOT EXISTS raw_highway_traffic (
    entry_toll_code      VARCHAR(50),
    entry_toll_name      VARCHAR(100),
    entry_address        VARCHAR(255),
    exit_toll_code       VARCHAR(50),
    exit_toll_name       VARCHAR(100),
    exit_address         VARCHAR(255),
    direction            VARCHAR(20),
    exit_date            VARCHAR(50),
    ev_count             VARCHAR(50),
    total_vehicle_count  VARCHAR(50),
    distance_km          VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='고속도로 통행량 원본(문자 그대로 적재)';

CREATE TABLE IF NOT EXISTS ev_charging_analysis (
    charging_id        INT AUTO_INCREMENT PRIMARY KEY,
    charge_date        DATE NOT NULL,
    station_name       VARCHAR(150),
    address            VARCHAR(255),
    charger_type       VARCHAR(100),
    charge_count       INT,
    total_charge_kwh   DECIMAL(14, 2),
    total_charge_time  DECIMAL(14, 2),
    avg_charge_kwh     DECIMAL(14, 2),
    avg_charge_time    DECIMAL(14, 2),
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_charging_date (charge_date),
    KEY idx_charging_station (station_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='충전 분석(일자·충전소별 집계)';

CREATE TABLE IF NOT EXISTS ev_traffic_analysis (
    traffic_id           INT AUTO_INCREMENT PRIMARY KEY,
    traffic_date         DATE NOT NULL,
    entry_toll_name      VARCHAR(100),
    exit_toll_name       VARCHAR(100),
    direction            VARCHAR(20),
    section_name         VARCHAR(255),
    ev_count             INT,
    total_vehicle_count  INT,
    ev_ratio             DECIMAL(8, 4),
    distance_km          DECIMAL(10, 2),
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_traffic_date (traffic_date),
    KEY idx_traffic_exit (exit_toll_name),
    KEY idx_traffic_section (section_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='통행량 분석(일자·구간별 집계)';

CREATE TABLE IF NOT EXISTS ev_charger_geo (
    geo_id        INT AUTO_INCREMENT PRIMARY KEY,
    station_name  VARCHAR(150),
    address       VARCHAR(255),
    latitude      DECIMAL(12, 8),
    longitude     DECIMAL(12, 8),
    api_status    VARCHAR(30),
    api_message   VARCHAR(255),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_station_name (station_name),
    KEY idx_geo_station (station_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='충전소 좌표(카카오 주소검색 API)';

-- 지도 시각화용 VIEW (충전 분석 + 좌표 조인). 별도 적재 불필요.
CREATE OR REPLACE VIEW ev_charging_map_analysis AS
SELECT
    c.station_name,
    MAX(c.address) AS address,
    g.latitude,
    g.longitude,
    SUM(c.charge_count) AS total_charge_count,
    SUM(c.total_charge_kwh) AS total_charge_kwh,
    SUM(c.total_charge_time) AS total_charge_time,
    ROUND(SUM(c.total_charge_kwh) / NULLIF(SUM(c.charge_count), 0), 2) AS avg_charge_kwh,
    ROUND(SUM(c.total_charge_time) / NULLIF(SUM(c.charge_count), 0), 2) AS avg_charge_time
FROM ev_charging_analysis c
JOIN ev_charger_geo g ON c.station_name = g.station_name
WHERE g.api_status = 'success'
  AND g.latitude IS NOT NULL
  AND g.longitude IS NOT NULL
GROUP BY c.station_name, g.latitude, g.longitude;

-- ------------------------------------------------------------
--  [팀원 추가 영역] 본인 데이터셋 테이블을 여기에 정의하세요.
--  예) CREATE TABLE IF NOT EXISTS ev_charger ( ... );
-- ------------------------------------------------------------