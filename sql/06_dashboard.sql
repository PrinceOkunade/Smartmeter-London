-- =====================================================================
--  BDCC LDS7005 - Smart Meters in London
--  06 - DASHBOARD QUERIES  (Databricks SQL / AI-BI Dashboard)
-- ---------------------------------------------------------------------
--  HOW TO USE
--  1. In the Databricks left sidebar choose: SQL > Dashboards > Create dashboard.
--  2. Attach a Serverless SQL Warehouse (top-right) - same data, SQL endpoint.
--  3. For EACH query below: Data tab > create a dataset > paste the SQL.
--  4. Canvas tab > add a visualization tile > pick the dataset > set the
--     chart type noted in the -- TILE: comment.
--  5. Publish, then screenshot the dashboard for report Section 4.
--
--  All queries read the GOLD layer in catalog `workspace`.
--  (If your catalog/schema differ, change the prefixes below.)
-- =====================================================================


-- TILE 1: KPI counters (Counter visual x4, or one table)
-- Headline numbers for the top of the dashboard.
SELECT
    ROUND(SUM(total_kwh)/1e6, 2)        AS total_GWh,
    ROUND(AVG(avg_kwh_per_home), 2)     AS avg_kwh_per_home_per_day,
    MAX(active_homes)                   AS peak_active_homes,
    COUNT(*)                            AS days_covered
FROM workspace.smartmeter_gold.daily_totals;


-- TILE 2: National demand trend over time  -- TILE: Line chart (x=day, y=avg_kwh_per_home)
SELECT day, avg_kwh_per_home, total_kwh, active_homes
FROM workspace.smartmeter_gold.daily_totals
ORDER BY day;


-- TILE 3: Consumption by detailed ACORN category  -- TILE: Bar chart (x=acorn_code, y=avg_daily_kwh)
-- (acorn_profile collapses to one bar on this subset, so drill into the detailed code)
SELECT acorn_code,
       ROUND(AVG(daily_kwh), 3)        AS avg_daily_kwh,
       COUNT(DISTINCT LCLid)           AS homes
FROM workspace.smartmeter_gold.daily_consumption
WHERE acorn_code IS NOT NULL
GROUP BY acorn_code
HAVING COUNT(DISTINCT LCLid) >= 5
ORDER BY avg_daily_kwh DESC;


-- TILE 4: Standard vs Time-of-Use tariff  -- TILE: Bar chart (x=tariff, y=avg_daily_kwh)
SELECT tariff,
       ROUND(AVG(avg_daily_kwh), 3)    AS avg_daily_kwh,
       SUM(households)                 AS households
FROM workspace.smartmeter_gold.acorn_profile
GROUP BY tariff
ORDER BY avg_daily_kwh DESC;


-- TILE 5: Demand vs temperature  -- TILE: Scatter (x=temp_avg, y=avg_kwh_per_home)
SELECT temp_avg, avg_kwh_per_home, season
FROM workspace.smartmeter_gold.daily_totals
WHERE temp_avg IS NOT NULL;


-- TILE 6: Seasonal / weekend / holiday effects  -- TILE: Table or grouped bar
SELECT season,
       ROUND(AVG(avg_kwh_per_home), 3)                                  AS avg_per_home,
       ROUND(AVG(CASE WHEN is_weekend = 1 THEN avg_kwh_per_home END), 3) AS weekend,
       ROUND(AVG(CASE WHEN is_weekend = 0 THEN avg_kwh_per_home END), 3) AS weekday,
       ROUND(AVG(CASE WHEN is_holiday = 1 THEN avg_kwh_per_home END), 3) AS holiday
FROM workspace.smartmeter_gold.daily_totals
GROUP BY season
ORDER BY avg_per_home DESC;


-- TILE 7: Average daily load curve (48 half-hours)  -- TILE: Line chart (x=clock_time, y=avg_kwh)
SELECT half_hour, clock_time, avg_kwh
FROM workspace.smartmeter_gold.load_profile
ORDER BY half_hour;


-- TILE 8: ML behavioural segments  -- TILE: Pie/Bar (x=segment, y=households)
SELECT segment,
       COUNT(*) AS households
FROM workspace.smartmeter_gold.household_segments
GROUP BY segment
ORDER BY segment;


-- TILE 9 (optional): Top 15 highest-consuming households  -- TILE: Table
SELECT LCLid,
       ROUND(AVG(daily_kwh), 2)        AS avg_daily_kwh,
       FIRST(tariff)                   AS tariff,
       FIRST(acorn_code)               AS acorn_code
FROM workspace.smartmeter_gold.daily_consumption
GROUP BY LCLid
ORDER BY avg_daily_kwh DESC
LIMIT 15;
