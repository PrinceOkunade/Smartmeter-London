# Database Schema Diagram — Smart Meters in London (Gold Star Schema)

This describes the **logical data model** of the lakehouse so you can reproduce
it as an ER / star-schema diagram in draw.io for the report (§3 Pre-processing
and §2 Architecture both benefit from it).

The gold layer is a classic **star schema**: one central **fact** table
(`daily_consumption`) surrounded by **dimension** tables it joins to. The other
gold tables are roll-ups (marts) built from that fact.

---

## ASCII overview (build this in draw.io)

```
                    +----------------------------+
                    |   DIM  households          |
                    |----------------------------|
                    | PK LCLid                   |
                    |    tariff                  |
                    |    acorn_group             |
                    |    acorn_code              |
                    +-------------+--------------+
                                  | 1
                                  |
                                  | *
   +-------------------+   *   +--+----------------------------+   *   +-------------------+
   | DIM weather_daily +-------+   FACT  daily_consumption     +-------+ DIM bank_holidays |
   |-------------------| 1     |-------------------------------| 1     |-------------------|
   | PK date           |       | FK LCLid   -> households      |       | PK date           |
   |    temp_avg       |       | FK day     -> weather.date    |       |    holiday_name   |
   |    temperatureMax |       | FK day     -> holidays.date   |       +-------------------+
   |    humidity ...   |       |    daily_kwh   (measure)      |
   +-------------------+       |    energy_mean/median/...     |
                               |    year, month, season        |
                               |    is_weekend, is_holiday      |
                               +---------------+---------------+
                                               |
                 rolled up into the gold marts (one-way, derived):
                                               |
        +--------------------+   +------------------+   +-----------------------+
        |  daily_totals      |   |  acorn_profile   |   |  household_segments   |
        |--------------------|   |------------------|   |-----------------------|
        | PK day             |   | acorn_group      |   | FK LCLid -> households |
        |    total_kwh       |   | tariff           |   |    segment (KMeans)    |
        |    avg_kwh_per_home |   | avg_daily_kwh    |   +-----------------------+
        |    active_homes    |   | median_daily_kwh |
        |    temp_avg        |   | households       |
        +--------------------+   +------------------+

        load_profile (half_hour 0-47, avg_kwh, clock_time)
        is built directly from silver.halfhourly, not from the fact.
```

---

## Relationships (cardinality)

| From (many) | To (one) | Join key | Meaning |
|---|---|---|---|
| `daily_consumption` | `households` | `LCLid` | each daily row belongs to one household |
| `daily_consumption` | `weather_daily` | `day = date` | each day has one weather record |
| `daily_consumption` | `bank_holidays` | `day = date` | each day optionally maps to one holiday |
| `household_segments` | `households` | `LCLid` | each household has one ML segment |

All relationships are **many-to-one** into the dimensions (a star, not a
snowflake — dimensions are flat, not further normalised).

---

## Lineage (how layers feed each other)

```
SOURCE CSVs (ADLS blob, abfss://)
      |  notebook 01 - ingest as-is + lineage cols
      v
BRONZE   halfhourly | households | bank_holidays | weather_daily
      |  notebook 02 - clean, type, dedup; derive daily + half_hour
      v
SILVER   halfhourly | daily | households | weather_daily | bank_holidays
      |  notebook 03 - join + aggregate
      v
GOLD     daily_consumption (FACT)
           |-> daily_totals      (group by day)
           |-> acorn_profile     (group by acorn_group, tariff)
           |-> load_profile      (from silver.halfhourly, by half_hour)
      |  notebook 05 - ML
      v
GOLD     household_segments (KMeans), forecast metrics
```

---

## draw.io build tips (to match the report's visual style)

- Use the **Entity Relation** shape group in the left panel (each box = a table
  with a title bar + a list of fields; mark PK/FK rows).
- Put `daily_consumption` dead centre, the three dimensions around it, and the
  three marts in a row underneath — that reads top-to-bottom as the star + its
  derived marts.
- Use **crow's-foot** connectors: the "many" (crow's foot) end touches the fact,
  the "one" end touches each dimension.
- Keep it monochrome (black text, white/grey fills) to match the report; export
  as PNG at 300 DPI and drop it into §3.
- Optional: add a thin left-to-right band labelled Bronze -> Silver -> Gold behind
  the boxes to tie the model to the medallion architecture.
