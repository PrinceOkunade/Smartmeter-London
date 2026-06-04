# Serving the Results — Dashboard Guide

The analysis results live in the **gold** Delta tables in Unity Catalog
(`workspace.smartmeter_gold.*`). This guide shows two ways to put a live
dashboard on top of them. Use either (or show both in the report).

Both options query the **same gold tables** — the dashboard is just a
presentation layer; no data is copied or duplicated.

---

## Option A — Databricks AI/BI Dashboard (native, recommended)

Fastest route, fully in-platform, works on Serverless.

**Steps**
1. Left sidebar: **SQL → Dashboards → Create dashboard**.
2. Top-right: attach a **Serverless SQL Warehouse** (start it if stopped).
3. Open `notebooks/06_dashboard.sql`. For each query:
   - **Data** tab → **Create from SQL** → paste the query → name the dataset
     (e.g. `demand_trend`).
4. **Canvas** tab → **Add a visualization** → choose the dataset → set the chart
   type from the `-- TILE:` comment in the SQL (line, bar, scatter, counter…).
5. Arrange tiles: KPIs across the top, trend + load curve as wide rows, ACORN /
   tariff / segment as a bottom row.
6. **Publish** (top-right) so it renders without edit chrome.
7. **Screenshot the published dashboard** → drop into report Section 4 as the
   "results served to decision-makers" figure.

**Tile plan (maps 1:1 to 06_dashboard.sql)**

| Tile | Dataset query | Chart |
|---|---|---|
| KPI cards | TILE 1 | Counter ×4 |
| Demand trend | TILE 2 | Line |
| ACORN consumption | TILE 3 | Bar (horizontal) |
| Tariff: Std vs ToU | TILE 4 | Bar |
| Demand vs temperature | TILE 5 | Scatter |
| Seasonal effects | TILE 6 | Table / grouped bar |
| Daily load curve | TILE 7 | Line |
| ML segments | TILE 8 | Pie or bar |
| Top households | TILE 9 | Table |

---

## Option B — Power BI Desktop (external BI tool)

Use this if your course specifically values Power BI. Power BI connects straight
to the Databricks SQL warehouse with the built-in connector — no export needed.

**Prerequisites**
- Power BI Desktop installed (Windows).
- A running **SQL Warehouse** in Databricks.
- A **Personal Access Token** (Databricks: top-right avatar → **Settings →
  Developer → Access tokens → Generate new token**; copy it once).

**Get the connection details**
- Databricks: **SQL Warehouses → (your warehouse) → Connection details** tab.
- Copy **Server hostname** (e.g. `adb-xxxx.azuredatabricks.net`) and
  **HTTP path** (e.g. `/sql/1.0/warehouses/abc123`).i

**Connect in Power BI Desktop**
1. **Home → Get data → More… → Azure → Azure Databricks** → Connect.
2. Paste **Server hostname** and **HTTP path**.
3. Data Connectivity mode: **Import** (small gold tables) or **DirectQuery**
   (live; keeps the warehouse as the engine). Import is simplest for the report.
4. Authentication: **Personal Access Token** → paste the token → Connect.
5. Navigator: expand `workspace → smartmeter_gold` → tick:
   `daily_totals`, `acorn_profile`, `load_profile`, `household_segments`,
   and optionally `daily_consumption` → **Load**.

**Model & visuals to build**
- Relationships: Power BI may auto-detect; otherwise link
  `daily_consumption[LCLid]` → `household_segments[LCLid]` and date columns as
  needed (the gold marts are already pre-aggregated, so you can also just
  visualise each mart directly).
- Suggested visuals (mirror the tile plan above):
  - **Line**: `daily_totals` day vs avg_kwh_per_home (demand trend).
  - **Clustered bar**: `acorn_profile` avg_daily_kwh by tariff.
  - **Scatter**: `daily_totals` temp_avg vs avg_kwh_per_home.
  - **Line**: `load_profile` clock_time vs avg_kwh (daily curve).
  - **Donut**: `household_segments` count by segment.
  - **Cards**: SUM(total_kwh), AVG(avg_kwh_per_home), MAX(active_homes).
- **File → Export → Export to PDF**, or screenshot, for the report.

**Note on cost/security**: keep the token out of the report and any committed
files; the warehouse should auto-stop when idle to control DBU cost (ties into
report §5 Cost Optimisation and §6 Security).

---

## Which to put in the report?

- Native AI/BI dashboard screenshot = shows results served **inside the same
  cloud platform** (clean cost/security story).
- Power BI screenshot = shows **integration with the enterprise BI tool**.
Either satisfies "the results are served on a dashboard"; showing both is a plus
for the Analysis & Insights and Architecture sections.
