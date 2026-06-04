-- =====================================================================
--  BDCC LDS7005 - Smart Meters in London
--  DATABASE SCHEMA / DATA DICTIONARY
--  Unity Catalog medallion lakehouse on Azure Databricks (Delta Lake)
-- ---------------------------------------------------------------------
--  Catalog : workspace
--  Schemas : smartmeter_bronze | smartmeter_silver | smartmeter_gold
--
--  NOTE: In the live pipeline these tables are NOT created with the DDL
--  below - they are written by Spark (df.write.saveAsTable, Delta format,
--  overwriteSchema=true) in notebooks 01-05. This file is a DOCUMENTED,
--  re-creatable equivalent of the schema each notebook produces, usable
--  as a data dictionary and (if ever needed) to pre-create the tables.
-- =====================================================================

CREATE CATALOG IF NOT EXISTS workspace;
CREATE SCHEMA  IF NOT EXISTS workspace.smartmeter_bronze;
CREATE SCHEMA  IF NOT EXISTS workspace.smartmeter_silver;
CREATE SCHEMA  IF NOT EXISTS workspace.smartmeter_gold;


-- =====================================================================
-- BRONZE  -  raw, faithful copy of the source files (no cleaning).
-- Every table carries two lineage columns: _source_file, _ingested_at.
-- Column names are sanitised at ingest (Delta rejects ( ) / space etc.):
--   energy(kWh/hh) -> energy_kWh_hh ,  "Bank holidays" -> Bank_holidays.
-- Types are inferred from CSV; energy/timestamps land as STRING because
-- the raw data contains literal "Null" text and 7-digit-fraction stamps.
-- =====================================================================

CREATE TABLE workspace.smartmeter_bronze.halfhourly (
    LCLid          STRING    COMMENT 'Household meter id (e.g. MAC000002)',
    tstp           STRING    COMMENT 'Reading timestamp, raw text (7-digit fraction)',
    energy_kWh_hh  STRING    COMMENT 'Energy in the half hour; may be literal "Null"',
    _source_file   STRING    COMMENT 'Lineage: source CSV path',
    _ingested_at   TIMESTAMP COMMENT 'Lineage: ingest time'
) USING DELTA
COMMENT 'Raw half-hourly readings - 21 block files read in parallel (~31.8M rows)';

CREATE TABLE workspace.smartmeter_bronze.households (
    LCLid          STRING    COMMENT 'Household meter id',
    stdorToU       STRING    COMMENT 'Tariff flag: Std or ToU',
    Acorn          STRING    COMMENT 'Detailed ACORN code (ACORN-A .. ACORN-U)',
    Acorn_grouped  STRING    COMMENT 'ACORN supergroup (Affluent/Comfortable/Adversity/...)',
    file           STRING    COMMENT 'Source block file the household belongs to',
    _source_file   STRING,
    _ingested_at   TIMESTAMP
) USING DELTA
COMMENT 'Household dimension (~5,566 rows)';

CREATE TABLE workspace.smartmeter_bronze.bank_holidays (
    Bank_holidays  STRING    COMMENT 'Holiday date (raw text); sanitised from "Bank holidays"',
    Type           STRING    COMMENT 'Holiday name',
    _source_file   STRING,
    _ingested_at   TIMESTAMP
) USING DELTA
COMMENT 'UK bank holidays reference (25 rows)';

CREATE TABLE workspace.smartmeter_bronze.weather_daily (
    time            STRING   COMMENT 'Day (raw text)',
    temperatureMax  STRING,
    temperatureMin  STRING,
    humidity        STRING,
    windSpeed       STRING,
    cloudCover      STRING,
    pressure        STRING,
    uvIndex         STRING,
    precipType      STRING,
    summary         STRING,
    -- ... remaining Dark Sky columns retained as-is ...
    _source_file    STRING,
    _ingested_at    TIMESTAMP
) USING DELTA
COMMENT 'Daily weather from Dark Sky (882 rows)';


-- =====================================================================
-- SILVER  -  cleaned, typed, deduplicated; daily table DERIVED from
-- the half-hourly readings. (Brief §3 Pre-processing.)
-- =====================================================================

CREATE TABLE workspace.smartmeter_silver.halfhourly (
    LCLid       STRING    COMMENT 'Household meter id',
    tstp        TIMESTAMP COMMENT 'Parsed reading timestamp (fraction dropped)',
    date        DATE      COMMENT 'Calendar date of the reading',
    hour        INT       COMMENT 'Hour of day 0-23',
    half_hour   INT       COMMENT 'Half-hour-of-day index 0-47 (00:00..23:30)',
    energy_kwh  DOUBLE    COMMENT 'Energy used in the half hour (kWh), nulls coerced'
) USING DELTA
COMMENT 'Clean half-hourly fact (~31.8M rows) - foundation for daily & load profile';

CREATE TABLE workspace.smartmeter_silver.daily (
    LCLid          STRING COMMENT 'Household meter id',
    day            DATE   COMMENT 'Calendar day',
    energy_sum     DOUBLE COMMENT 'Total kWh for the household-day',
    energy_mean    DOUBLE COMMENT 'Mean half-hourly kWh',
    energy_median  DOUBLE COMMENT 'Median half-hourly kWh (percentile_approx 0.5)',
    energy_max     DOUBLE COMMENT 'Max half-hourly kWh',
    energy_min     DOUBLE COMMENT 'Min half-hourly kWh',
    energy_std     DOUBLE COMMENT 'Std-dev of half-hourly kWh',
    energy_count   BIGINT COMMENT 'Number of half-hourly readings that day'
) USING DELTA
COMMENT 'Daily consumption DERIVED from half-hourly (~664,959 rows)';

CREATE TABLE workspace.smartmeter_silver.households (
    LCLid          STRING COMMENT 'Household meter id (PK)',
    stdorToU       STRING COMMENT 'Raw tariff flag',
    acorn_code     STRING COMMENT 'Detailed ACORN code (renamed from Acorn)',
    Acorn_grouped  STRING COMMENT 'Raw ACORN supergroup',
    tariff         STRING COMMENT 'Derived: "Time-of-Use" or "Standard"',
    acorn_group    STRING COMMENT 'Derived: supergroup, blanks -> "Unclassified"'
) USING DELTA
COMMENT 'Household dimension, conformed (~5,566 rows)';

CREATE TABLE workspace.smartmeter_silver.weather_daily (
    date            DATE   COMMENT 'Calendar day (PK)',
    temp_avg        DOUBLE COMMENT 'Derived: (temperatureMax + temperatureMin)/2',
    temperatureMax  DOUBLE,
    temperatureMin  DOUBLE,
    humidity        DOUBLE,
    windSpeed       DOUBLE,
    cloudCover      DOUBLE,
    pressure        DOUBLE,
    uvIndex         DOUBLE,
    precipType      STRING,
    summary         STRING
) USING DELTA
COMMENT 'Daily weather dimension, typed (879 rows after dedup)';

CREATE TABLE workspace.smartmeter_silver.bank_holidays (
    date          DATE   COMMENT 'Holiday date (PK)',
    holiday_name  STRING COMMENT 'Holiday name (renamed from Type)'
) USING DELTA
COMMENT 'Bank-holiday calendar dimension (25 rows)';


-- =====================================================================
-- GOLD  -  business-ready, analytics & ML-ready aggregates.
-- daily_consumption is the central FACT; the others are roll-ups / views
-- onto it. (Brief §3 -> §4.)
-- =====================================================================

CREATE TABLE workspace.smartmeter_gold.daily_consumption (
    LCLid          STRING COMMENT 'Household meter id  (FK -> silver.households.LCLid)',
    day            DATE   COMMENT 'Calendar day        (FK -> dimensions by date)',
    daily_kwh      DOUBLE COMMENT 'Total kWh for the household-day (renamed energy_sum)',
    energy_mean    DOUBLE,
    energy_median  DOUBLE,
    energy_max     DOUBLE,
    energy_min     DOUBLE,
    energy_std     DOUBLE,
    energy_count   BIGINT,
    tariff         STRING COMMENT 'From households dim',
    acorn_group    STRING COMMENT 'From households dim',
    acorn_code     STRING COMMENT 'From households dim',
    temp_avg       DOUBLE COMMENT 'From weather dim (joined on day)',
    -- ...full weather columns (temperatureMax/Min, humidity, windSpeed,
    --    cloudCover, pressure, uvIndex, precipType, summary) carried through...
    holiday_name   STRING COMMENT 'From holidays dim (null if not a holiday)',
    year           INT,
    month          INT,
    day_of_week    INT    COMMENT '1=Sun .. 7=Sat',
    is_weekend     INT    COMMENT '1 if Sat/Sun',
    is_holiday     INT    COMMENT '1 if a UK bank holiday',
    season         STRING COMMENT 'Winter/Spring/Summer/Autumn'
) USING DELTA
COMMENT 'MASTER FACT: household x day, enriched with tariff/ACORN/weather/calendar (~664,959 rows). Powers analysis (04) and ML (05).';

CREATE TABLE workspace.smartmeter_gold.daily_totals (
    day               DATE   COMMENT 'Calendar day (PK)',
    season            STRING,
    is_weekend        INT,
    is_holiday        INT,
    total_kwh         DOUBLE COMMENT 'Sum of daily_kwh across active homes',
    avg_kwh_per_home  DOUBLE COMMENT 'Mean daily_kwh per active home',
    active_homes      BIGINT COMMENT 'Distinct households reporting that day',
    temp_avg          DOUBLE COMMENT 'Average temperature for the day'
) USING DELTA
COMMENT 'One row per day - demand trend & weather correlation (829 rows)';

CREATE TABLE workspace.smartmeter_gold.acorn_profile (
    acorn_group       STRING COMMENT 'ACORN supergroup',
    tariff            STRING COMMENT 'Standard / Time-of-Use',
    avg_daily_kwh     DOUBLE COMMENT 'Mean daily kWh for the group x tariff',
    median_daily_kwh  DOUBLE COMMENT 'Median daily kWh (percentile_approx 0.5)',
    households        BIGINT COMMENT 'Distinct households in the cell'
) USING DELTA
COMMENT 'Consumption by affluence group x tariff - "who consumes most"';

CREATE TABLE workspace.smartmeter_gold.load_profile (
    half_hour   INT    COMMENT 'Half-hour-of-day index 0-47 (PK)',
    avg_kwh     DOUBLE COMMENT 'Average energy per half-hour across all households',
    clock_time  STRING COMMENT 'Human-readable HH:MM for the slot'
) USING DELTA
COMMENT 'The 48-point average daily demand curve';

CREATE TABLE workspace.smartmeter_gold.household_segments (
    LCLid    STRING COMMENT 'Household meter id (FK -> silver.households.LCLid)',
    segment  INT    COMMENT 'K-Means load-shape segment (0,1,2 - k=3)'
) USING DELTA
COMMENT 'ML output (notebook 05): each household assigned a behavioural segment';
