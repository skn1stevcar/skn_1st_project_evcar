-- ============================================================
--  고속도로 통행량·충전 raw → 분석 테이블 정제 적재
--  선행: loader_traffic_charging.py 로 raw_ev_charger_daily /
--        raw_highway_traffic 적재 후 본 스크립트를 실행한다.
--  재실행 안전: 적재 전 TRUNCATE.
-- ============================================================
USE ev_infra;

-- 1) 충전 raw → 충전 분석
TRUNCATE TABLE ev_charging_analysis;
INSERT INTO ev_charging_analysis (
    charge_date, station_name, address, charger_type,
    charge_count, total_charge_kwh, total_charge_time,
    avg_charge_kwh, avg_charge_time
)
SELECT
    charge_date, station_name, address, charger_type,
    charge_count, total_charge_kwh, total_charge_time,
    ROUND(total_charge_kwh / NULLIF(charge_count, 0), 2) AS avg_charge_kwh,
    ROUND(total_charge_time / NULLIF(charge_count, 0), 2) AS avg_charge_time
FROM (
    SELECT
        DATE(charge_start_date) AS charge_date,
        station_name, address, charger_type,
        COALESCE(CAST(NULLIF(NULLIF(REPLACE(charge_count, ',', ''), ''), 'nan') AS UNSIGNED), 0) AS charge_count,
        COALESCE(CAST(NULLIF(NULLIF(REPLACE(total_charge_kwh, ',', ''), ''), 'nan') AS DECIMAL(14, 2)), 0) AS total_charge_kwh,
        COALESCE(CAST(NULLIF(NULLIF(REPLACE(total_charge_time, ',', ''), ''), 'nan') AS DECIMAL(14, 2)), 0) AS total_charge_time
    FROM raw_ev_charger_daily
) t
WHERE charge_date IS NOT NULL;

-- 2) 통행량 raw → 통행량 분석
TRUNCATE TABLE ev_traffic_analysis;
INSERT INTO ev_traffic_analysis (
    traffic_date, entry_toll_name, exit_toll_name, direction,
    section_name, ev_count, total_vehicle_count, ev_ratio, distance_km
)
SELECT
    traffic_date, entry_toll_name, exit_toll_name, direction,
    CONCAT(entry_toll_name, ' → ', exit_toll_name, ' (', direction, ')') AS section_name,
    ev_count, total_vehicle_count,
    ROUND(ev_count / NULLIF(total_vehicle_count, 0) * 100, 4) AS ev_ratio,
    distance_km
FROM (
    SELECT
        CASE
            WHEN date_clean REGEXP '^[0-9]{8}$' AND date_clean <> '00000000'
            THEN STR_TO_DATE(date_clean, '%Y%m%d')
            ELSE NULL
        END AS traffic_date,
        entry_toll_name, exit_toll_name, direction,
        COALESCE(CAST(CAST(ev_count_clean AS DECIMAL(20, 2)) AS UNSIGNED), 0) AS ev_count,
        COALESCE(CAST(CAST(total_vehicle_count_clean AS DECIMAL(20, 2)) AS UNSIGNED), 0) AS total_vehicle_count,
        COALESCE(CAST(distance_km_clean AS DECIMAL(10, 2)), 0) AS distance_km
    FROM (
        SELECT
            REPLACE(REPLACE(TRIM(exit_date), '.0', ''), ',', '') AS date_clean,
            entry_toll_name, exit_toll_name, direction,
            NULLIF(NULLIF(REPLACE(TRIM(ev_count), ',', ''), ''), 'nan') AS ev_count_clean,
            NULLIF(NULLIF(REPLACE(TRIM(total_vehicle_count), ',', ''), ''), 'nan') AS total_vehicle_count_clean,
            NULLIF(NULLIF(REPLACE(TRIM(distance_km), ',', ''), ''), 'nan') AS distance_km_clean
        FROM raw_highway_traffic
    ) s
) t
WHERE traffic_date IS NOT NULL;
