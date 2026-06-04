"""
Render the medallion lakehouse architecture as a PNG (no draw.io needed).
Mirrors the components + 7-step data flow described in report section 2.1.
Output: visualization/architecture_diagram.png  (monochrome, report-ready, 300 DPI)
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

EDGE = "black"
GREY = "#D9D9D9"
LGREY = "#F2F2F2"

def box(ax, x, y, w, h, title, sub="", fill="white", title_size=10, sub_size=8, bold=True):
    """Draw a rounded box; (x, y) = bottom-left. Returns (cx, cy, x, y, w, h)."""
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.06",
                 linewidth=1.3, edgecolor=EDGE, facecolor=fill, zorder=3))
    cx, cy = x + w/2, y + h/2
    if sub:
        ax.text(cx, cy + 0.16, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold" if bold else "normal", zorder=4)
        ax.text(cx, cy - 0.22, sub, ha="center", va="center",
                fontsize=sub_size, color="#333333", zorder=4)
    else:
        ax.text(cx, cy, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold" if bold else "normal", zorder=4)
    return (cx, cy, x, y, w, h)

def arrow(ax, p1, p2, style="-|>", color="black", lw=1.6, ls="-"):
    ax.annotate("", xy=p2, xytext=p1,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls,
                                shrinkA=2, shrinkB=2), zorder=2)

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

ax.text(8, 8.6, "Scalable Big Data Processing Architecture", ha="center",
        fontsize=17, fontweight="bold")
ax.text(8, 8.2, "Medallion lakehouse on Azure Databricks (Serverless Apache Spark) + ADLS Gen2",
        ha="center", fontsize=10.5, color="#444444")

# ---------------- Governance band (spans storage + compute) ----------------
gov = box(ax, 2.9, 7.05, 8.7, 0.85,
          "Governance & Security  —  Unity Catalog",
          "Storage Credential + External Location  ·  Access Connector (managed identity, key-less abfss://)",
          fill=GREY, title_size=10, sub_size=8)

# ---------------- Sources (left column) ----------------
ax.text(1.45, 6.55, "Data sources (CSV)", ha="center", fontsize=10, fontweight="bold")
src_specs = [
    ("Half-hourly readings", "21 block files"),
    ("Households", "tariff + ACORN"),
    ("Weather (daily)", "Dark Sky"),
    ("Bank holidays", "calendar"),
]
src_boxes = []
y0 = 5.7
for i, (t, s) in enumerate(src_specs):
    b = box(ax, 0.4, y0 - i*1.0, 2.1, 0.8, t, s, fill=LGREY, title_size=8.5, sub_size=7.5)
    src_boxes.append(b)

# ---------------- ADLS Gen2 ----------------
adls = box(ax, 3.1, 3.55, 1.9, 1.9,
           "Azure Data\nLake Storage\nGen2", "bronze container\n(raw files)",
           fill="white", title_size=9.5, sub_size=7.8)

# ---------------- Databricks Serverless container ----------------
ax.add_patch(FancyBboxPatch((5.4, 2.55), 6.25, 4.0,
             boxstyle="round,pad=0.02,rounding_size=0.06",
             linewidth=1.6, edgecolor=EDGE, facecolor="white", zorder=1))
ax.text(8.5, 6.2, "Azure Databricks  —  Serverless (Apache Spark)",
        ha="center", fontsize=10.5, fontweight="bold", zorder=4)

bronze = box(ax, 5.7, 3.7, 1.75, 1.7, "BRONZE", "raw Delta\n+ lineage", fill=LGREY,
             title_size=9.5, sub_size=7.8)
silver = box(ax, 7.65, 3.7, 1.75, 1.7, "SILVER", "cleaned, typed\n+ derived daily", fill=GREY,
             title_size=9.5, sub_size=7.8)
gold   = box(ax, 9.6, 3.7, 1.75, 1.7, "GOLD", "star schema\n(fact + dims)", fill="#BFBFBF",
             title_size=9.5, sub_size=7.8)

# notebook labels under each layer
for b, lbl in [(bronze, "nb 01"), (silver, "nb 02"), (gold, "nb 03")]:
    ax.text(b[0], 3.45, lbl, ha="center", va="top", fontsize=7.5, style="italic", color="#555555")

# ---------------- Consumption (right column) ----------------
ax.text(13.9, 6.2, "Consumption", ha="center", fontsize=10, fontweight="bold")
cons_specs = [
    ("Spark SQL + charts", "analytics (nb 04)"),
    ("scikit-learn ML", "K-Means + GBT (nb 05)"),
    ("Power BI dashboard", "served to decision-makers"),
]
cons_boxes = []
for i, (t, s) in enumerate(cons_specs):
    b = box(ax, 12.1, 5.0 - i*1.05, 3.5, 0.9, t, s, fill=LGREY, title_size=9, sub_size=7.5)
    cons_boxes.append(b)

# ---------------- Monitoring band (below compute) ----------------
mon = box(ax, 5.4, 1.35, 6.25, 0.8,
          "Monitoring & Management",
          "Spark UI  ·  Query History  ·  Delta DESCRIBE HISTORY  ·  Azure Monitor / Cost Management",
          fill=GREY, title_size=9.5, sub_size=7.8)

# ================= arrows =================
# sources -> ADLS
for b in src_boxes:
    arrow(ax, (b[2] + b[4], b[1]), (adls[2], adls[1]))
# ADLS -> Bronze
arrow(ax, (adls[2] + adls[4], adls[1]), (bronze[2], bronze[1]), lw=2.0)
# Bronze -> Silver -> Gold
arrow(ax, (bronze[2] + bronze[4], bronze[1]), (silver[2], silver[1]), lw=2.0)
arrow(ax, (silver[2] + silver[4], silver[1]), (gold[2], gold[1]), lw=2.0)
# Gold -> each consumption box
for b in cons_boxes:
    arrow(ax, (gold[2] + gold[4], gold[1]), (b[2], b[1]))

# governance -> storage & compute (dashed, key-less access)
arrow(ax, (adls[0], gov[3]), (adls[0], adls[1] + adls[5]/2), style="-", lw=1.1, ls=(0, (4, 3)), color="#666666")
arrow(ax, (8.5, gov[3]), (8.5, 6.45), style="-", lw=1.1, ls=(0, (4, 3)), color="#666666")
# compute -> monitoring (dashed)
arrow(ax, (8.5, 2.55), (8.5, mon[1] + mon[5]), style="-", lw=1.1, ls=(0, (4, 3)), color="#666666")

# legend
ax.text(0.4, 0.5,
        "Solid arrows = data flow (medallion pipeline).   "
        "Dashed lines = governance / observability (cross-cutting).",
        fontsize=8.5, color="#444444")

plt.tight_layout()
out = os.path.join("visualization", "architecture_diagram.png")
os.makedirs("visualization", exist_ok=True)
plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print("saved ->", os.path.abspath(out))
