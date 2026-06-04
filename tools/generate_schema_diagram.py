"""
Render the gold-layer star schema as a PNG (no draw.io needed).
Output: visualization/schema_diagram.png  (monochrome, report-ready, 300 DPI)
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

HEADER = "#D9D9D9"   # grey header bar (matches report tables)
EDGE   = "black"
FILL   = "white"

ROW_H   = 0.34       # height per field row
HEAD_H  = 0.46       # header bar height
PAD     = 0.12

def draw_table(ax, x, y, w, title, fields, pk=(), fk=()):
    """Draw a table box with header + field rows. (x, y) = top-left corner."""
    n = len(fields)
    body_h = n * ROW_H
    total_h = HEAD_H + body_h
    # body
    ax.add_patch(FancyBboxPatch((x, y - total_h), w, total_h,
                 boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.3, edgecolor=EDGE, facecolor=FILL, zorder=2))
    # header bar
    ax.add_patch(plt.Rectangle((x, y - HEAD_H), w, HEAD_H,
                 linewidth=1.3, edgecolor=EDGE, facecolor=HEADER, zorder=3))
    ax.text(x + w/2, y - HEAD_H/2, title, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color="black", zorder=4)
    # field rows
    for i, f in enumerate(fields):
        fy = y - HEAD_H - (i + 0.5) * ROW_H
        tag = ""
        weight = "normal"
        if f in pk:
            tag, weight = "PK  ", "bold"
        elif f in fk:
            tag, weight = "FK  ", "normal"
        ax.text(x + PAD, fy, f"{tag}{f}", ha="left", va="center",
                fontsize=8.6, color="black", fontweight=weight, zorder=4)
        if i < n - 1:
            ax.plot([x, x + w], [y - HEAD_H - (i+1)*ROW_H]*2,
                    color="#cccccc", lw=0.6, zorder=3)
    return (x, y, w, total_h)   # return geometry for connectors

def center_bottom(box):
    x, y, w, h = box; return (x + w/2, y - h)
def center_top(box):
    x, y, w, h = box; return (x + w/2, y)
def center_left(box):
    x, y, w, h = box; return (x, y - h/2)
def center_right(box):
    x, y, w, h = box; return (x + w, y - h/2)

def connect(ax, p1, p2):
    ax.annotate("", xy=p2, xytext=p1,
                arrowprops=dict(arrowstyle="-", color="black", lw=1.4),
                zorder=1)

fig, ax = plt.subplots(figsize=(15, 10))
ax.set_xlim(0, 15); ax.set_ylim(0, 10); ax.axis("off")

ax.text(7.5, 9.7, "Gold Star Schema  -  Smart Meters in London",
        ha="center", fontsize=15, fontweight="bold")
ax.text(7.5, 9.35, "FACT: daily_consumption  -  joined to flat dimensions; gold marts derived below",
        ha="center", fontsize=9.5, color="#444444")

# ---- dimensions (top row) ----
b_house = draw_table(ax, 5.85, 9.0, 3.3, "DIM  households",
        ["LCLid", "tariff", "acorn_group", "acorn_code"], pk=("LCLid",))

b_weather = draw_table(ax, 0.4, 7.4, 3.5, "DIM  weather_daily",
        ["date", "temp_avg", "temperatureMax", "temperatureMin", "humidity", "windSpeed"],
        pk=("date",))

b_holiday = draw_table(ax, 11.1, 7.4, 3.5, "DIM  bank_holidays",
        ["date", "holiday_name"], pk=("date",))

# ---- fact (centre) ----
b_fact = draw_table(ax, 5.55, 7.1, 3.9, "FACT  daily_consumption",
        ["LCLid", "day", "daily_kwh", "energy_mean", "tariff", "acorn_code",
         "temp_avg", "season", "is_weekend", "is_holiday"],
        pk=(), fk=("LCLid", "day"))

# ---- marts (bottom row) ----
b_totals = draw_table(ax, 0.4, 2.9, 3.4, "MART  daily_totals",
        ["day", "total_kwh", "avg_kwh_per_home", "active_homes", "temp_avg"], pk=("day",))

b_acorn = draw_table(ax, 4.25, 2.9, 3.4, "MART  acorn_profile",
        ["acorn_group", "tariff", "avg_daily_kwh", "median_daily_kwh", "households"])

b_load = draw_table(ax, 8.1, 2.9, 3.3, "MART  load_profile",
        ["half_hour", "clock_time", "avg_kwh"], pk=("half_hour",))

b_seg = draw_table(ax, 11.7, 2.9, 3.0, "ML  household_segments",
        ["LCLid", "segment"], fk=("LCLid",))

# ---- connectors: fact -> dimensions ----
connect(ax, center_top(b_fact), center_bottom(b_house))
connect(ax, center_left(b_fact), center_right(b_weather))
connect(ax, center_right(b_fact), center_left(b_holiday))

# ---- connectors: fact -> marts (derived) ----
connect(ax, center_bottom(b_fact), center_top(b_totals))
connect(ax, center_bottom(b_fact), center_top(b_acorn))
connect(ax, center_bottom(b_fact), center_top(b_seg))
# load_profile is built from silver.halfhourly (dashed = different source)
ax.annotate("", xy=center_top(b_load), xytext=center_bottom(b_fact),
            arrowprops=dict(arrowstyle="-", color="#777777", lw=1.2,
                            linestyle=(0, (4, 3))), zorder=1)

# legend
ax.text(0.4, 0.4, "PK = primary key   FK = foreign key   "
        "solid line = join / roll-up   dashed = built from silver.halfhourly",
        fontsize=8.5, color="#444444")

plt.tight_layout()
out = os.path.join("visualization", "schema_diagram.png")
os.makedirs("visualization", exist_ok=True)
plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print("saved ->", os.path.abspath(out))
