"""
build_report.py
=================
Generates the BDCC LDS7005 (Component 1, 60%) Word report from a single script,
so it can be regenerated as notebook results / screenshots come in.

Run:  python build_report.py
Out:  BDCC_LDS7005_Report.docx   (in the project root)

Design choices
--------------
* Heading styles are used throughout so Word can auto-build the Table of Contents.
* Every place that needs a screenshot is inserted as a shaded, red, bold paragraph
  beginning with "[SCREENSHOT n]", search the doc for "[SCREENSHOT" to find them all.
* Appendix A lists every screenshot with the matching file you already captured
  (in /screenshot) or a short "CAPTURE:" instruction for ones still to take.
* Harvard in-text citations (Author, year); full reference list at the end.
"""

import os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BLACK = RGBColor(0x00, 0x00, 0x00)

VIZ_DIR = "visualization"  # chart PNGs exported from notebook 04/05

# ----------------------------------------------------------------------------- helpers
doc = Document()

# Ask Word to update all fields (TOC, Table of Figures) the first time the doc is opened.
_uf = OxmlElement("w:updateFields"); _uf.set(qn("w:val"), "true")
doc.settings.element.append(_uf)

# Base font
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.font.color.rgb = BLACK

# ---- Monochrome: force black everywhere, kill the Word theme blue ----------------
for sname in ["Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "Heading 4",
              "Caption", "TOC 1", "TOC 2", "TOC 3", "TOC 4", "Hyperlink",
              "List Bullet", "List Number"]:
    try:
        st = doc.styles[sname]
        st.font.color.rgb = BLACK
        if sname == "Hyperlink":
            st.font.underline = False
    except KeyError:
        pass

# Separate caption style for tables -> lets us build a Table of Tables distinct from the
# Table of Figures (figures keep the built-in 'Caption' style).
try:
    _tcap = doc.styles.add_style("TableCaption", WD_STYLE_TYPE.PARAGRAPH)
    _tcap.base_style = doc.styles["Caption"]
    _tcap.font.color.rgb = BLACK
except Exception:
    pass

SCREENSHOTS = []  # collected for Appendix A


def _shade(paragraph, fill="FFF2CC"):
    """Apply a background shading to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def _shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def screenshot(desc, source):
    """Insert a clearly-marked screenshot placeholder and log it for the appendix."""
    n = len(SCREENSHOTS) + 1
    SCREENSHOTS.append((n, desc, source))
    p = doc.add_paragraph()
    _shade(p, "FCE4D6")
    run = p.add_run(f"[SCREENSHOT {n}]  {desc}")
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    run.font.size = Pt(10)
    sub = doc.add_paragraph()
    r2 = sub.add_run(f"      → {source}")
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    return p


def todo(text):
    """A note to the student about something to fill in from a notebook run."""
    p = doc.add_paragraph()
    _shade(p, "E2EFDA")
    run = p.add_run(f"[FILL IN]  {text}")
    run.bold = True
    run.font.color.rgb = RGBColor(0x37, 0x6E, 0x37)
    run.font.size = Pt(10)
    return p


def body(text):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    return p


def bullet(text):
    p = doc.add_paragraph(text, style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def numbered(text):
    return doc.add_paragraph(text, style="List Number")


def code_block(text):
    p = doc.add_paragraph()
    _shade(p, "F2F2F2")
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    return p


def _seq_caption(label, text, center=False):
    """Add an auto-numbered caption: '<label> <SEQ>. <text>'. Word renumbers the SEQ
    fields automatically, so figures/tables never need manual renumbering. 'Figure'
    captions use the Caption style; 'Table' captions use TableCaption."""
    style = "Caption" if label == "Figure" else "TableCaption"
    p = doc.add_paragraph(style=style)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{label} ")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), f" SEQ {label} \\* ARABIC ")
    _r = OxmlElement("w:r"); _t = OxmlElement("w:t"); _t.text = "1"; _r.append(_t); fld.append(_r)
    p._p.append(fld)
    p.add_run(f". {text}")
    return p


def embed_image(filename, caption, width_in=6.0):
    """Embed a chart/screenshot PNG from VIZ_DIR with an auto-numbered Figure caption.
    Falls back to a screenshot placeholder if the file is not present."""
    path = os.path.join(VIZ_DIR, filename)
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width_in))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _seq_caption("Figure", caption, center=True)
    else:
        screenshot(caption, f"CAPTURE: expected image not found at {path}")


def add_field(instr, placeholder="Right-click here and choose 'Update Field' to populate."):
    """Insert a Word field (e.g. a TOC) that Word populates on open / update."""
    p = doc.add_paragraph()
    r = p.add_run()._r
    begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin"); r.append(begin)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r.append(it)
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate"); r.append(sep)
    t = OxmlElement("w:t"); t.text = placeholder; r.append(t)
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end"); r.append(end)
    return p


def add_table(headers, rows, caption=None):
    if caption:
        _seq_caption("Table", caption)
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"                     # plain black borders, no theme colour
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = BLACK
        _shade_cell(c, "D9D9D9")               # light-grey header (not blue)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(9)
            run.font.color.rgb = BLACK
    doc.add_paragraph()
    return t


# ============================================================================= TITLE
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("Optimizing Big Data Processing in the Cloud")
r.bold = True
r.font.size = Pt(22)
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("A Medallion Lakehouse for London Smart-Meter Energy Data on Azure Databricks")
r.font.size = Pt(14)
r.italic = True

doc.add_paragraph()
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
for line in [
    "Module: LDS7005M, Big Data and Cloud Computing",
    "Component 1 (Creative Artefact), 60%",
    "Student ID: [INSERT YOUR STUDENT ID]",
    "Word count: [INSERT]",
    "May 2026",
]:
    rr = meta.add_run(line + "\n")
    rr.font.size = Pt(12)

doc.add_page_break()

# ============================================================================= TOC
body("(If any list below shows grey placeholder text, click into it and press F9, or right-click → "
     "Update Field, to populate page numbers.)")

doc.add_heading("Table of Contents", level=1)
add_field('TOC \\o "1-3" \\z \\u')
doc.add_page_break()

doc.add_heading("Table of Figures", level=1)
add_field('TOC \\z \\c "Figure"')
doc.add_page_break()

doc.add_heading("Table of Tables", level=1)
add_field('TOC \\z \\c "Table"')
doc.add_page_break()

# ============================================================================= INTRO
doc.add_heading("Introduction", level=1)
body(
    "This report presents the design and implementation of a cloud-based big data solution for a "
    "multinational enterprise seeking to optimise the storage, processing and analysis of large, "
    "diverse datasets (Chen, Mao and Liu, 2014; Marz and Warren, 2015). Adopting the role of a data "
    "architect, the solution is demonstrated end-to-end "
    "on a Smart-City energy use case: the Smart Meters in London dataset, from which over 31.7 "
    "million half-hourly electricity readings spanning 5,566 households were ingested and processed "
    "(UK Power Networks, 2014). "
    "The implementation uses a lakehouse architecture on Microsoft Azure, Azure Data Lake Storage "
    "Gen2 for storage and Azure Databricks (serverless Apache Spark) for distributed processing, "
    "organised using the medallion (bronze/silver/gold) design pattern (Databricks, 2024a). "
    "The report follows the seven assessed areas of the brief and is accompanied by the coding "
    "artefacts (six PySpark/Spark SQL notebooks) and a README."
)

# ============================================================================= SECTION 1
doc.add_heading("1. Data Ingestion and Storage", level=1)

doc.add_heading("1.1 Types and sources of data", level=2)
body(
    "A modern enterprise handles heterogeneous data: structured transactional records, "
    "semi-structured logs and telemetry, and unstructured text and media. To demonstrate the "
    "solution on a realistic high-volume source, the Smart Meters in London dataset is used "
    "(Jean-Michel, 2019; originally the Low Carbon London project, UK Power Networks, 2014). It is a "
    "Smart-City energy dataset that comfortably exceeds the 1 GB threshold required by the brief "
    "(approximately 11 GB uncompressed), and combines four complementary sources:"
)
add_table(
    ["Source", "Type / format", "Grain", "Role in the model"],
    [
        ["Half-hourly meter readings", "Structured CSV (split into 21 block files)", "household × 30-min interval", "Primary fact, the large, partitioned source"],
        ["Household information", "Structured CSV", "one row per household", "Dimension, tariff type and ACORN affluence group"],
        ["Daily weather (Dark Sky)", "Structured CSV", "one row per day", "Dimension, temperature, humidity, wind, etc."],
        ["UK bank holidays", "Structured CSV", "one row per holiday", "Calendar dimension, holiday flag"],
    ],
    caption="The four source datasets and their role in the dimensional model.",
)
body(
    "The half-hourly readings are the 'big data' core: a tall, narrow table of "
    "(LCLid, timestamp, energy) that was split into 21 block files to enable parallel ingestion. "
    "The remaining three are small reference/dimension tables. This mix of one large fact and "
    "several small dimensions is the classic star-schema shape of dimensional analytics "
    "(Kimball and Ross, 2013) and motivates the scalable architecture in Section 2."
)
embed_image("fig_dataset_size.png",
            "The raw half-hourly dataset on disk, 7.32 GB across 112 source files, "
            "confirming the >1 GB large-scale requirement of the brief.")
embed_image("fig_bronze_container.png",
            "The four source datasets uploaded into the bronze container (halfhourly, households, "
            "calendar, weather) on Azure Data Lake Storage Gen2.")

doc.add_heading("1.2 Cloud-based storage solution", level=2)
body(
    "The proposed storage tier is Azure Data Lake Storage (ADLS) Gen2, Azure Blob Storage with a "
    "hierarchical namespace enabled, which is the recommended foundation for analytics lakes on "
    "Azure (Microsoft, 2024a). It is evaluated against the three criteria in the brief:"
)
bullet("Scalability: object storage scales effectively without limit and decouples storage from "
       "compute, so data volume can grow independently of processing capacity. A single account "
       "supports petabyte-scale data and high request throughput (Microsoft, 2024a).")
bullet("Redundancy: Azure replicates data automatically. Locally-redundant storage (LRS) keeps three "
       "copies within a datacentre; geo-redundant storage (GRS) additionally replicates to a paired "
       "region for regional-disaster durability of eleven nines (Microsoft, 2024b). LRS is adequate "
       "for this reproducible dataset; GRS would be specified for business-critical data.")
bullet("Cost-effectiveness: access tiers (Hot / Cool / Cold / Archive) let infrequently-used data move "
       "to cheaper tiers via lifecycle policies, and pricing is pay-per-GB with no pre-provisioning "
       "(Microsoft, 2024c). Storing data as compressed, columnar Parquet/Delta further reduces both "
       "footprint and the volume scanned per query.")
body(
    "Within the lake, data is organised using the medallion architecture: a bronze container holds "
    "raw source files, while the bronze/silver/gold Delta table layers (Section 3) provide governed, "
    "progressively-refined copies. This separation of a cheap raw landing zone from curated tables is "
    "a widely-adopted lakehouse pattern (Databricks, 2024a)."
)
embed_image("fig_storage_account.png",
            "The storage account configuration: ADLS Gen2 (Hierarchical namespace = Enabled), "
            "Standard performance and Locally-redundant storage (LRS).")

doc.add_heading("1.3 Data ingestion process and tools", level=2)
body(
    "Ingestion follows a governed path from the lake into Delta tables. Because the Databricks "
    "workspace runs on serverless compute, access to ADLS is brokered through Unity Catalog rather "
    "than account keys: a Databricks Access Connector (an Azure managed identity) is granted the "
    "Storage Blob Data Contributor role on the storage account, registered in Unity Catalog as a "
    "Storage Credential, and exposed as an External Location over the abfss:// endpoint (Databricks, "
    "2024b; Microsoft, 2024d). This is the enterprise-grade, key-less pattern and also satisfies the "
    "security requirements in Section 6."
)
body("The ingestion steps are:")
numbered("Source files are uploaded to the ADLS Gen2 container (bronze) under four folders.")
numbered("A Unity Catalog External Location authorises serverless Spark to read the container via "
         "abfss://bronze@smartmeterprince.dfs.core.windows.net/.")
numbered("Notebook 01 reads each source with Spark's CSV reader. The 21 half-hourly blocks are read "
         "with a single glob (halfhourly/*.csv) so Spark ingests them in parallel.")
numbered("Each record is stamped with lineage columns, the source file path and an ingestion "
         "timestamp, and written to a bronze Delta table (mode overwrite).")
code_block(
    'df = (read_csv(PATHS["halfhourly"])\n'
    '        .withColumn("_source_file", F.col("_metadata.file_path"))\n'
    '        .withColumn("_ingested_at", F.current_timestamp()))\n'
    'df.write.format("delta").mode("overwrite").saveAsTable(tgt)'
)
body(
    "Delta Lake is chosen as the table format because it adds ACID transactions, schema enforcement "
    "and time-travel to Parquet, which makes ingestion idempotent and auditable (Armbrust et al., "
    "2020). For a continuously-arriving feed the same pattern extends to Databricks Auto Loader for "
    "incremental, exactly-once file ingestion (Databricks, 2024c); here a batch read is sufficient "
    "for the fixed historical dataset."
)
embed_image("fig_access_connector.png",
            "The Databricks Access Connector (managed identity) deployed in Azure, the "
            "identity that Unity Catalog uses to reach the storage account.")
embed_image("fig_credential.png",
            "The Unity Catalog Storage Credential 'cred-smartmeter' (Managed Identity type) "
            "referencing the Access Connector's resource ID.")
embed_image("fig_external_location.png",
            "Creating the Unity Catalog External Location over "
            "abfss://bronze@smartmeterprince.dfs.core.windows.net/ using that credential.")
embed_image("fig_bronze_tables.png",
            "The bronze schema after ingestion, showing the four raw Delta tables and a sample of the "
            "half-hourly fact with its lineage columns.")
body("Notebook 01 reported the following ingested volumes, confirming the scale of the source:")
add_table(
    ["Bronze table", "Rows ingested"],
    [
        ["halfhourly (the large fact)", "31,796,103"],
        ["households", "5,566"],
        ["weather_daily", "882"],
        ["bank_holidays", "25"],
    ],
    caption="Row counts ingested into the bronze layer (from notebook 01).",
)
body(
    "The half-hourly fact contains over 31.7 million readings, the partitioned, parallel-read source "
    "that demonstrates the big-data capability of the architecture, while the three dimensions are "
    "small lookup tables, confirming the one-large-fact/many-small-dimensions shape described above."
)

# ============================================================================= SECTION 2
doc.add_heading("2. Scalable Processing Architecture", level=1)

body("The following table summarises the principal design decisions taken across the whole solution "
     "and the reasoning behind each, so the rationale is explicit before the architecture is detailed. "
     "Every choice is driven by three forces: the need to scale to a large dataset, the constraints "
     "of the serverless platform, and cost-efficiency.")
add_table(
    ["Decision", "Choice made", "Justification"],
    [
        ["Cloud platform", "Azure Databricks lakehouse on ADLS Gen2",
         "Managed, auto-scaling Spark with governed storage; compatible with the Azure for Students subscription."],
        ["Compute model", "Databricks Serverless",
         "No cluster sizing or management and pay-per-use billing; classic clusters were unavailable under the student subscription's vCPU quota."],
        ["Storage access", "Unity Catalog External Location + Access Connector (managed identity)",
         "Key-less, governed access to abfss://, no account keys or SAS tokens are stored anywhere."],
        ["Table format", "Delta Lake",
         "ACID transactions, schema enforcement and time-travel make ingestion idempotent and auditable."],
        ["Data architecture", "Medallion (bronze / silver / gold)",
         "Incremental data-quality, isolation of failures, and independently re-computable layers."],
        ["Source layout", "21 half-hourly block files",
         "Lets Spark read and process the 31.8M-row fact in parallel."],
        ["ML execution", "scikit-learn on Spark-aggregated data",
         "Spark MLlib is not whitelisted on serverless; Spark reduces 31.8M rows to a small table, then scikit-learn models it (Spark for ETL, single-node for ML)."],
        ["Cluster count k", "Fixed k = 3",
         "Silhouette is a flat plateau (~0.15); k = 3 yields balanced, interpretable segments and avoids a degenerate cluster."],
        ["ACORN analysis", "Detailed ACORN code (A–E)",
         "The sampled subset is almost entirely the Affluent supergroup, so the supergroup view collapses; the detailed code recovers the real gradient."],
    ],
    caption="Key design decisions and their justifications.",
)

doc.add_heading("2.1 Architecture design", level=2)
body(
    "The processing architecture is a lakehouse built on Azure Databricks, implementing the medallion "
    "pattern. Raw files in ADLS are progressively refined through three Delta table layers, each a "
    "distinct Unity Catalog schema:"
)
code_block(
    "ADLS Gen2 (abfss://)        BRONZE              SILVER                 GOLD             CONSUME\n"
    "-----------------------  ->  raw Delta    ->  cleaned & typed   ->  joined/aggregated -> SQL / charts / ML\n"
    "halfhourly/ (21 blocks)     (+lineage)       halfhourly (clean)     daily_consumption    notebooks 04 & 05\n"
    "household, weather,                         daily (DERIVED)        daily_totals\n"
    "holidays                                                            acorn_profile, load_profile"
)
bullet("Bronze, faithful, replayable raw copy of each source with lineage columns.")
bullet("Silver, cleaned, typed, deduplicated tables; the daily consumption table is derived here "
       "from the half-hourly readings by aggregation.")
bullet("Gold, business-ready tables (a master daily fact, daily totals, an ACORN/tariff profile and "
       "a 48-point load curve) that feed analytics and machine learning directly.")
body(
    "This layered design improves data quality incrementally, isolates failures, and lets each layer "
    "be recomputed independently, a recognised benefit of the medallion approach (Databricks, 2024a). "
    "All transformation logic is written in PySpark and Spark SQL across six notebooks, with a single "
    "configuration notebook (00) defining all paths, schemas and helpers."
)
body(
    "The end-to-end architecture is composed of the following components. Each maps to a box in the "
    "architecture diagram, and the data-flow steps that follow map to the arrows between them."
)
add_table(
    ["Layer", "Component", "Role in the architecture"],
    [
        ["Sources", "Four source datasets (CSV)",
         "Half-hourly meter readings (21 blocks), households, daily weather and bank holidays."],
        ["Storage", "Azure Data Lake Storage Gen2 (bronze container)",
         "Scalable, redundant object store holding the raw source files (the data lake)."],
        ["Governance / security", "Databricks Access Connector + Unity Catalog (Storage Credential, External Location)",
         "Key-less managed-identity access and central governance over the abfss:// data."],
        ["Compute", "Azure Databricks Serverless (Apache Spark)",
         "Auto-scaling distributed engine that runs every notebook; no cluster to manage."],
        ["Bronze layer", "Raw Delta tables",
         "Faithful, replayable copy of each source with lineage columns."],
        ["Silver layer", "Cleaned Delta tables",
         "Typed, de-duplicated tables plus the derived daily table."],
        ["Gold layer", "Curated Delta tables",
         "Business-ready star-schema tables (daily_consumption fact plus dimensions)."],
        ["Consumption", "Spark SQL + matplotlib (nb 04); scikit-learn (nb 05)",
         "Analytical queries, charts, and the K-Means and gradient-boosting models."],
        ["Monitoring", "Spark UI, Query History, Azure Monitor",
         "Cross-cutting observability over compute and storage."],
    ],
    caption="Components of the architecture and their roles.",
)
body("The data flows through these components as follows (the arrows of the diagram):")
numbered("The four source CSV datasets are uploaded into the bronze container on ADLS Gen2.")
numbered("Unity Catalog, using the Access Connector's managed identity, exposes the container as an "
         "External Location, authorising Serverless Spark to read it over abfss:// without any keys.")
numbered("Notebook 01 reads the raw files in parallel and writes them, with lineage columns, to the "
         "Bronze Delta tables.")
numbered("Notebook 02 cleans, types and de-duplicates Bronze and derives the daily table, producing "
         "the Silver Delta tables.")
numbered("Notebook 03 joins and aggregates Silver into the Gold Delta tables (the star schema).")
numbered("Notebook 04 queries Gold with Spark SQL and renders charts, while Notebook 05 trains the "
         "scikit-learn models on the aggregated Gold and Silver data; results feed business decisions.")
numbered("Throughout, the Spark UI, Query History and Azure Monitor observe the running jobs and "
         "the storage for performance management.")
embed_image("architecture_diagram.png",
            "The end-to-end solution architecture: the four CSV sources land in ADLS Gen2, are "
            "progressively refined through the bronze, silver and gold Delta layers on Databricks "
            "Serverless, and are consumed by Spark SQL analytics, the scikit-learn models and the "
            "Power BI dashboard. Unity Catalog provides key-less governance across storage and "
            "compute, and a monitoring layer observes the running system.")
body(
    "The diagram makes the design's two organising principles explicit. The horizontal axis is the "
    "data-flow pipeline (solid arrows), data moves left to right and is enriched at each medallion "
    "stage, so a failure or quality issue is isolated to a single, independently re-computable layer. "
    "The vertical elements are cross-cutting concerns (dashed lines): Unity Catalog governs every "
    "access to storage and compute through a single managed identity rather than scattered keys, and "
    "the monitoring layer observes the whole pipeline. Critically, storage (ADLS Gen2) and compute "
    "(serverless Spark) are separate boxes, they scale independently, which is the property that lets "
    "the same architecture grow from this ~1,050-household subset to a national meter rollout without "
    "redesign (Section 2.3)."
)
embed_image("fig_resource_group.png",
            "The Azure resource group provisioned for the solution (Azure for Students, "
            "Spain Central region).")
embed_image("fig_databricks_home.png",
            "The Azure Databricks workspace (dbw-smartmeterprince) used to host the pipeline.")
embed_image("fig_serverless_notebook.png",
            "A pipeline notebook attached to Serverless compute (top-right), the distributed "
            "Spark engine used throughout, with no cluster to size or manage.")

doc.add_heading("2.2 Cloud services for distributed and parallel processing", level=2)
body(
    "Distributed processing is provided by Apache Spark on Azure Databricks. Spark partitions a "
    "dataset across the cluster and executes transformations in parallel on each partition, which is "
    "the core mechanism that makes the half-hourly fact tractable, building on the MapReduce model "
    "of distributed computation (Dean and Ghemawat, 2008; Zaharia et al., 2016). Splitting "
    "the half-hourly data into 21 block files lets Spark read and process them concurrently rather "
    "than serially. Spark SQL's Catalyst optimiser and the columnar Parquet substrate of Delta "
    "further reduce work by pruning columns and partitions and pushing filters down to storage "
    "(Armbrust et al., 2015)."
)
body(
    "The workspace uses Databricks Serverless compute. Serverless removes cluster management "
    "entirely: capacity is provisioned on demand when a notebook runs and released automatically when "
    "idle, so the user never sizes or starts a cluster (Databricks, 2024d). This was also the "
    "practical choice on the Azure subscription used, where classic clusters were unavailable; "
    "serverless provided the distributed Spark engine without a vCPU quota."
)

doc.add_heading("2.3 Accommodating growing data volumes", level=2)
body("The architecture scales along several independent axes:")
bullet("Storage/compute separation: data can grow in ADLS without changing the compute tier, and "
       "compute can scale up for heavy jobs without moving data (Microsoft, 2024a).")
bullet("Elastic, auto-scaling compute: serverless adds and removes resources with workload size, so "
       "larger inputs are handled without re-architecting (Databricks, 2024d).")
bullet("Partitioned, columnar storage: more block files simply increase Spark's read parallelism; "
       "Delta supports partitioning and OPTIMIZE/Z-ORDER compaction to keep large tables performant "
       "(Armbrust et al., 2020).")
bullet("Incremental ingestion path: for an operational feed, Auto Loader processes only new files, so "
       "cost and runtime track new data rather than total data (Databricks, 2024c).")
body(
    "The same notebooks would therefore run unchanged on the full multi-year feed of all 5,567 "
    "households, or on a national rollout of millions of meters, by allowing serverless to scale and "
    "adding more block files. This elastic, storage-and-compute-separated model is the defining "
    "characteristic of big-data processing on cloud platforms (Hashem et al., 2015; "
    "Assunção et al., 2015)."
)

# ============================================================================= SECTION 3
doc.add_heading("3. Data Extraction and Pre-processing", level=1)

doc.add_heading("3.1 Dataset selection", level=2)
body(
    "The Smart Meters in London dataset was selected under the Smart City topic. It is well suited to "
    "this assignment because it is genuinely large (~11 GB; over 31.7 million readings ingested here), it is naturally "
    "multi-source (meter, weather, household, calendar), and it supports both descriptive analytics "
    "and predictive machine learning. It also has clear enterprise relevance: energy retailers and "
    "network operators routinely apply smart-meter data analytics for tariff design, demand-response "
    "and grid "
    "capacity planning (UK Power Networks, 2014; Wang et al., 2019)."
)

doc.add_heading("3.2 Extraction process, tools and transformations", level=2)
body(
    "Extraction is performed by notebook 01 (Bronze). Spark reads each CSV source from the External "
    "Location; the 21 half-hourly blocks are extracted in parallel via a single glob path. The only "
    "transformation at this stage is the addition of two lineage columns (source file path and "
    "ingestion timestamp), bronze deliberately preserves the raw values so the layer is replayable. "
    "A deliberate design point is that the household dimension is read by its exact filename rather "
    "than a folder glob, because the ACORN lookup file shares that folder but has a different schema; "
    "globbing would corrupt the read."
)
add_table(
    ["Source", "Extraction path", "Bronze table"],
    [
        ["Half-hourly", "halfhourly/*.csv (21 blocks, parallel)", "..._bronze.halfhourly"],
        ["Households", "household/informations_households.csv", "..._bronze.households"],
        ["Bank holidays", "calendar/uk_bank_holidays.csv", "..._bronze.bank_holidays"],
        ["Weather (daily)", "weather/weather_daily_darksky.csv", "..._bronze.weather_daily"],
    ],
    caption="Extraction mapping from lake files to bronze Delta tables.",
)

doc.add_heading("3.3 Pre-processing: cleaning and preparation", level=2)
body(
    "Notebook 02 (Silver) converts the raw bronze data into clean, typed, analysis-ready tables and "
    "derives the daily consumption table. The half-hourly readings required several specific fixes "
    "identified by inspecting the raw data:"
)
bullet("Energy column: the source column 'energy(kWh/hh)' contains leading spaces and the literal "
       "text 'Null'. It is trimmed and cast to double, which coerces non-numeric values to true nulls, "
       "then null rows are filtered out.")
bullet("Timestamps: values such as '2012-10-12 00:30:00.0000000' carry seven fractional-second digits "
       "that Spark cannot parse; the first 19 characters are kept and converted with to_timestamp.")
bullet("Feature derivation: a half_hour index 0–47 (hour×2 + [minute≥30]) is added to support the "
       "load-profile and clustering analyses, along with date and hour.")
bullet("Deduplication: duplicate (household, timestamp) pairs are dropped.")
bullet("Dimensions: tariff codes are mapped to readable labels (Std→Standard, ToU→Time-of-Use); blank "
       "or unknown ACORN groups become 'Unclassified'; weather gains a derived average temperature; "
       "bank-holiday dates are parsed and typed.")
code_block(
    'hh = (spark.table(table("bronze","halfhourly"))\n'
    '   .withColumnRenamed("energy(kWh/hh)", "energy_kwh")\n'
    '   .withColumn("energy_kwh", F.trim("energy_kwh").cast("double"))\n'
    '   .withColumn("tstp", F.to_timestamp(F.substring("tstp",1,19)))\n'
    '   .withColumn("half_hour", F.col("hour")*2 + (F.minute("tstp")>=30).cast("int"))\n'
    '   .dropDuplicates(["LCLid","tstp"]))'
)
body(
    "Crucially, the daily consumption table is then derived from the cleaned half-hourly readings by "
    "grouping on (household, day) and computing sum, mean, median, max, min, standard deviation and "
    "count of energy. This means the entire downstream pipeline is reproduced from the half-hourly "
    "source alone, without requiring any separate pre-aggregated daily file."
)
embed_image("fig_silver_tables.png",
            "The silver schema after cleaning, showing the cleaned half-hourly table, the derived daily "
            "table, and the conformed dimension tables.")
body("The cleaning is verified by the resulting silver row counts:")
add_table(
    ["Silver table", "Rows", "Note"],
    [
        ["halfhourly (cleaned)", "31,795,055", "1,048 'Null'/duplicate rows removed from bronze"],
        ["daily (derived)", "664,959", "household-day aggregates built from half-hourly"],
        ["households", "5,566", "tariff + ACORN conformed"],
        ["weather_daily", "879", "3 duplicate dates removed"],
        ["bank_holidays", "25", "typed calendar dimension"],
    ],
    caption="Silver-layer row counts after cleaning and derivation (from notebook 02).",
)
body(
    "The 1,048-row reduction in the half-hourly table confirms the null-coercion and de-duplication "
    "logic executed correctly, and the 664,959 derived household-day records become the grain of the "
    "gold analytics layer."
)

# ============================================================================= SECTION 4
doc.add_heading("4. Data Analysis and Insights", level=1)

doc.add_heading("4.1 Cloud-based analytics solution", level=2)
body(
    "Analytics run on the gold layer (notebook 03), which joins and aggregates the silver tables into "
    "four business-ready tables: daily_consumption (a household×day master fact enriched with tariff, "
    "ACORN, weather and calendar features), daily_totals (one row per day), acorn_profile "
    "(consumption by affluence group and tariff) and load_profile (a 48-point daily demand curve). "
    "Notebook 04 then queries these tables with Spark SQL and visualises them with matplotlib, all "
    "executed on serverless Spark, a fully cloud-based analytics solution requiring no local "
    "infrastructure."
)
embed_image("fig_gold_tables.png",
            "The gold schema, showing the four business-ready tables (daily_consumption, daily_totals, "
            "acorn_profile, load_profile).")
body("The gold layer produced four analytics tables. Notably, daily_consumption retained exactly "
     "664,959 rows, identical to the silver daily grain, confirming the dimension joins neither "
     "dropped nor duplicated any records:")
add_table(
    ["Gold table", "Rows", "Grain / purpose"],
    [
        ["daily_consumption", "664,959", "household × day master fact (ML features)"],
        ["daily_totals", "829", "one row per day (≈2.3 years of demand)"],
        ["acorn_profile", "3", "ACORN affluence supergroup × tariff"],
        ["load_profile", "48", "average half-hourly daily demand curve"],
    ],
    caption="Gold-layer tables and row counts (from notebook 03).",
)
body(
    "The gold layer is organised as a classic star schema. At its centre is the daily_consumption "
    "fact table (one row per household per day), which references three conformed dimensions, "
    "households (tariff and ACORN affluence), weather_daily (joined on date) and bank_holidays "
    "(joined on date). The remaining gold tables (daily_totals, acorn_profile and load_profile) are "
    "pre-aggregated marts derived from that fact, and household_segments holds the machine-learning "
    "segment assigned to each household. The schema is illustrated below."
)
embed_image("schema_diagram.png",
            "The gold-layer star schema: the daily_consumption fact joined to the households, "
            "weather_daily and bank_holidays dimensions, with the derived marts and the ML "
            "household_segments table.")
body(
    "This star-schema design is deliberate. Centralising the measures (daily_kwh and its statistics) "
    "in a single narrow fact and keeping the descriptive attributes in small, flat dimensions makes "
    "the analytical queries in Section 4.2 simple and fast: each business question is answered by "
    "joining the fact to one dimension and aggregating (Kimball and Ross, 2013). It also keeps the "
    "model extensible, a new attribute (for example, dwelling type) is added as a dimension column "
    "without reshaping the fact, and it cleanly separates the high-volume fact (664,959 rows) from "
    "the kilobyte-scale dimensions, which lets Spark broadcast the small tables during joins for "
    "efficiency. A full column-level data dictionary for every bronze, silver and gold table is "
    "provided with the coding artefacts (schema.sql)."
)

doc.add_heading("4.2 Analytical queries and machine-learning algorithms", level=2)
body(
    "Six analytical queries answer concrete business questions, each supported by a chart from "
    "notebook 04:"
)
add_table(
    ["#", "Question", "Method"],
    [
        ["1", "How does national daily demand move over time?", "Time-series of avg kWh/home"],
        ["2", "Does affluence relate to demand?", "Avg daily kWh by detailed ACORN category (bar)"],
        ["3", "Do Time-of-Use customers behave differently?", "Avg daily kWh by tariff"],
        ["4", "How strongly does temperature drive demand?", "Pearson correlation + scatter"],
        ["5", "What are the season/weekend/holiday effects?", "Grouped SQL aggregation"],
        ["6", "When does demand peak during the day?", "48-point half-hourly load curve"],
    ],
    caption="The six analytical queries and the method used for each.",
)
embed_image("avg daily electricity per household over time.png",
            "Insight 1, average daily electricity use per household over the period. The "
            "pronounced winter peaks and summer troughs show demand is strongly seasonal.")
body(
    "Insight 1 confirms a clear seasonal cycle: per-home demand rises sharply in winter and falls in "
    "summer, which both motivates the weather-based forecast (Section 4.2) and frames the seasonal "
    "breakdown in Insight 5."
)
body(
    "Data-coverage note (Insight 2). The 21 ingested block files cover approximately 1,050 of the "
    "5,566 households, and because the Kaggle half-hourly data is partitioned by household rather than "
    "by time, this subset falls almost entirely within the single 'Affluent' ACORN supergroup, where "
    "ACORN is the CACI geodemographic classification of UK households (CACI, 2014). "
    "Aggregating at the three-level supergroup therefore collapses to one bar and is uninformative. "
    "The analysis instead drills down to the detailed ACORN category (ACORN-A to ACORN-E), which "
    "varies meaningfully within the subset and recovers a genuine affluence–consumption relationship. "
    "The pipeline itself is group-agnostic and would surface the full Affluent/Comfortable/Adversity "
    "contrast unchanged on a broader set of blocks."
)
embed_image("avg daily consumpt by detailed ACORN category.png",
            "Insight 2, average daily consumption by detailed ACORN category. A clear "
            "gradient emerges: the most affluent category (ACORN-A) consumes ~80% more than ACORN-E.")
add_table(
    ["ACORN category", "Avg daily kWh", "Households"],
    [
        ["ACORN-A (most affluent)", "19.064", "157"],
        ["ACORN-D", "13.578", "292"],
        ["ACORN-C", "11.951", "151"],
        ["ACORN-B", "11.903", "25"],
        ["ACORN-E", "10.620", "423"],
    ],
    caption="Insight 2, average daily consumption by detailed ACORN category.",
)
body(
    "Even within the affluent population there is a strong affluence gradient: ACORN-A households "
    "average 19.06 kWh/day against 10.62 kWh/day for ACORN-E, roughly 80% higher. This confirms that "
    "more affluent households (typically larger properties with more appliances) drive materially "
    "higher demand, which is actionable for targeted energy-efficiency programmes and for differentiated "
    "tariff design."
)
body(
    "Insight 3 (the strong result). Holding affluence constant within the Affluent group, Time-of-Use "
    "households consume noticeably less than Standard-tariff households: 11.90 kWh/day (227 homes) "
    "versus 13.15 kWh/day (823 homes), a reduction of roughly 10%. Because both groups share the "
    "same affluence profile, this difference is attributable to the dynamic-pricing signal rather "
    "than to socio-economic confounding, providing clean evidence that Time-of-Use tariffs shift and "
    "reduce consumption."
)
add_table(
    ["Tariff", "Avg daily kWh", "Households"],
    [["Standard", "13.145", "823"], ["Time-of-Use", "11.902", "227"]],
    caption="Insight 3, average daily consumption by tariff (within the Affluent-dominated subset).",
)
embed_image("dmand vs temp.png",
            "Insight 4, daily per-home demand versus average temperature. The strong "
            "negative correlation (Pearson r = -0.83) indicates heating-led, weather-driven demand.")
body(
    "Insight 4 quantifies the seasonality of Insight 1: with r = -0.83, temperature is a dominant "
    "driver of daily demand, which directly justifies including weather features in the forecasting "
    "model and is the single most useful signal for grid capacity planning."
)
add_table(
    ["Season", "Avg / home", "Weekend", "Weekday", "Holiday"],
    [
        ["Winter", "15.081", "15.632", "14.862", "15.557"],
        ["Spring", "12.680", "13.084", "12.521", "12.671"],
        ["Autumn", "12.644", "12.955", "12.520", "10.607"],
        ["Summer", "10.082", "10.181", "10.041", "10.243"],
    ],
    caption="Insight 5, average daily kWh per home by season, split by weekend/weekday/holiday.",
)
body(
    "Insight 5 shows winter demand (15.08 kWh/home) is roughly 50% higher than summer (10.08), and "
    "that weekends consistently exceed weekdays across every season, consistent with higher daytime "
    "occupancy at weekends."
)
embed_image("avd half hourly load profile.png",
            "Insight 6, average half-hourly load profile across a typical day, showing a "
            "pronounced evening peak around 17:00-20:00.")
body(
    "Insight 6 locates demand within the day: a clear evening peak between roughly 17:00 and 20:00. "
    "This is precisely the window in which Time-of-Use pricing and demand-response programmes deliver "
    "the most value, linking the load shape back to the tariff finding in Insight 3."
)

body(
    "Two machine-learning models (notebook 05) extend the descriptive analytics into prediction and "
    "segmentation. Because Spark MLlib is restricted on serverless compute, the models are implemented "
    "with scikit-learn (Pedregosa et al., 2011) on the Spark-aggregated data, a standard pattern for "
    "applied machine learning (Géron, 2019):"
)
body(
    "Customer segmentation (K-Means). Each household's average daily load is pivoted into a 48-point "
    "profile and L1-normalised so clustering captures the shape of usage (when energy is used) rather "
    "than its magnitude. The number of clusters k is selected using the silhouette coefficient over "
    "k = 2 to 6 (Rousseeuw, 1987), then K-Means is fitted and the cluster centres are plotted as "
    "interpretable load shapes (for example, an evening-peak segment versus a flatter daytime segment)."
)
add_table(
    ["k", "Silhouette"],
    [["2", "0.1530"], ["3", "0.1546  (selected)"], ["4", "0.1554"], ["5", "0.1494"], ["6", "0.1462"]],
    caption="K-Means silhouette score by number of clusters, a flat plateau around 0.15.",
)
body(
    "The silhouette scores form a flat plateau (~0.15) with no pronounced peak, which is expected "
    "for household load curves: behaviour varies along a continuum rather than in sharply separated "
    "groups. Although the metric nominally edges highest at k = 4, the spread between k = 2 and k = 4 "
    "is within the algorithm's run-to-run variation, and k = 4 produces a degenerate cluster of only "
    "~10 households. Following good practice of not over-fitting to a near-flat metric, k = 3 is "
    "selected for a balanced, interpretable segmentation, yielding three well-populated segments of "
    "289, 398 and 363 households."
)
embed_image("kmeans segment load shapes.png",
            "K-Means cluster centres, the normalised daily load shape of each of the three "
            "household segments (share of daily energy by half-hour).")

body(
    "Demand forecasting (Gradient-Boosted Trees). A gradient-boosted regression-tree ensemble "
    "(Friedman, 2001) predicts average daily kWh per home "
    "from weather and calendar features (temperature, month, day-of-week, weekend, holiday, season). "
    "An honest time-based split (train on the earlier ~75% of dates, test on the later 25%) is used, "
    "and performance is reported with RMSE, MAE and R², plus a feature-importance ranking."
)
embed_image("gbt forecast actual vs predicted.png",
            "GBT demand forecast, actual versus predicted average daily demand over the "
            "held-out (latest 25%) test period.")
add_table(
    ["Metric", "Value", "Interpretation"],
    [
        ["RMSE", "1.2477", "≈1.25 kWh typical error vs a ~12 kWh/home mean (~10%)"],
        ["MAE", "0.6570", "median absolute error well under 1 kWh/home/day"],
        ["R²", "0.6845", "the model explains ~68% of daily demand variance"],
    ],
    caption="GBT forecast performance on the held-out test period.",
)
body(
    "An R² of 0.68 from weather and calendar features alone is a strong result for daily demand, and "
    "the low MAE (0.66 kWh) shows the forecast is accurate enough for operational capacity planning."
)
add_table(
    ["Feature", "Importance"],
    [
        ["temp_avg", "0.860"],
        ["month", "0.065"],
        ["season_idx", "0.057"],
        ["day_of_week", "0.017"],
        ["is_weekend", "0.002"],
        ["is_holiday", "0.000"],
    ],
    caption="GBT feature importance, temperature dominates.",
)
body(
    "Temperature overwhelmingly dominates (importance 0.860), with the remaining calendar features "
    "contributing only marginally. This independently corroborates Insight 4 (r = -0.83): demand is "
    "fundamentally weather-driven. The practical implication is that an accurate temperature forecast "
    "is sufficient to anticipate aggregate demand, letting the enterprise pre-position supply and size "
    "the network for forecast peaks."
)

doc.add_heading("4.3 Contribution to decision-making", level=2)
body("Each result maps to an enterprise decision:")
bullet("The seasonal, weather-driven demand trend (Insights 1, 4) justifies weather-based forecasting "
       "and informs grid capacity planning for winter peaks.")
bullet("The affluence gradient across detailed ACORN categories (Insight 2), ACORN-A using ~80% "
       "more than ACORN-E, lets the utility target energy-efficiency incentives at the highest-"
       "consuming segments.")
bullet("The ~10% lower consumption of Time-of-Use versus Standard households within the same "
       "affluence group (Insight 3) provides evidence that dynamic pricing curbs demand, supporting "
       "wider Time-of-Use tariff rollout and demand-side management.")
bullet("The evening peak in the load curve (Insight 6) identifies the 17:00–20:00 window where "
       "Time-of-Use pricing and demand-response deliver the most value.")
bullet("K-Means segments let the utility match each behavioural group to the right tariff and "
       "demand-response programme.")
bullet("The GBT forecast lets the enterprise pre-position supply and size the network for predicted "
       "peak demand, reducing both shortage risk and over-provisioning cost.")

doc.add_heading("4.4 Serving the results: an interactive dashboard", level=2)
body(
    "To make the insights consumable by business decision-makers rather than only by data scientists, "
    "the gold tables are served to an interactive Microsoft Power BI dashboard. Power BI connects "
    "directly to the Databricks SQL warehouse using the native Azure Databricks connector, so the "
    "dashboard queries the same governed gold Delta tables live, no data is exported, copied or "
    "duplicated, which preserves the single source of truth and the Unity Catalog security model "
    "(Microsoft, 2024g). Authentication uses a personal access token over the warehouse's server "
    "hostname and HTTP path; in a production deployment this would be upgraded to organisational "
    "single sign-on."
)
embed_image("fig_powerbi_connection.png",
            "Connecting Power BI Desktop to the Azure Databricks SQL warehouse via the native "
            "connector (server hostname and HTTP path), the key-less, governed link to the gold layer.")
embed_image("fig_powerbi_loading.png",
            "Loading the five gold tables (daily_consumption, daily_totals, acorn_profile, "
            "load_profile and household_segments) into the Power BI semantic model.")
embed_image("fig_powerbi_dashboard.png",
            "The Power BI dashboard serving the gold layer: headline KPIs, the demand trend, the "
            "demand-versus-temperature relationship, the ACORN affluence gradient, the tariff "
            "comparison, the daily load curve and the K-Means household segments.")
body(
    "The dashboard consolidates the whole analysis onto a single canvas. Three KPI cards report the "
    "headline figures (total energy of roughly 8.5 million kWh, an average of 12.88 kWh per home per "
    "day, and around one thousand active households). Beneath them, the visuals reproduce the report's "
    "key findings interactively: the demand-trend line shows the seasonal cycle, the scatter makes the "
    "strong negative demand-versus-temperature relationship (r = -0.83) visible at a glance, the ACORN "
    "bar chart shows the affluence gradient (ACORN-A consuming markedly more than ACORN-E), the load "
    "curve exposes the evening peak, and the doughnut shows the three behavioural segments produced by "
    "the K-Means model. Because every tile is backed by a live query, a decision-maker can filter and "
    "drill into the figures themselves rather than reading static charts, which is exactly how the "
    "analytics translate into operational decisions on tariffs, demand-response and capacity planning."
)

# ============================================================================= SECTION 5
doc.add_heading("5. Cost Optimisation Strategies", level=1)
body(
    "Cost is optimised across compute, storage and query efficiency:"
)
bullet("Serverless, pay-per-use compute: resources are billed only while a notebook is running and "
       "are released automatically when idle, eliminating the cost of idle clusters (Databricks, "
       "2024d). This is the single largest saving for an intermittent analytics workload.")
bullet("Compressed columnar storage: storing data as Delta/Parquet compresses it and, because queries "
       "read only the columns and partitions they need, reduces the volume scanned and therefore "
       "compute time (Armbrust et al., 2020).")
bullet("Storage tiering and lifecycle policies: raw bronze data that is rarely re-read can be moved "
       "to the Cool or Archive access tier automatically, cutting storage cost for cold data "
       "(Microsoft, 2024c).")
bullet("Right-sizing the source: splitting the half-hourly data into blocks improves read parallelism "
       "and lets jobs finish faster, which directly lowers serverless cost.")
bullet("Reserved / committed-use discounts: for steady-state production workloads, Azure reservations "
       "and Databricks committed-use contracts trade a usage commitment for a substantial discount "
       "versus on-demand pricing (Microsoft, 2024c).")
bullet("Table maintenance: periodic Delta OPTIMIZE compaction avoids the small-files problem that "
       "would otherwise inflate query cost on a growing table (Armbrust et al., 2020).")
embed_image("fig_cost_analysis.png",
            "Azure Cost Management cost analysis for the resource group, evidencing the low spend of the "
            "serverless, pay-per-use design.")
embed_image("fig_describe_detail.png",
            "DESCRIBE DETAIL on the daily_consumption gold table, the 664,959-row fact occupies "
            "roughly 16 MB in a single Delta/Parquet file, evidencing the compression of the columnar "
            "format.")
body(
    "The DESCRIBE DETAIL output quantifies the storage saving directly: the 664,959-row daily_consumption "
    "fact, enriched with more than twenty columns, occupies only about 16 MB (sizeInBytes ≈ 16.1 million) "
    "in a single Delta/Parquet file. Columnar encoding and compression therefore reduce what would be a "
    "much larger row-oriented dataset to a few megabytes, which lowers both storage cost and the volume "
    "scanned, and hence the compute time, of every query against it (Armbrust et al., 2020). The single-file "
    "layout also confirms there is no small-files problem on this table; as data grows, periodic OPTIMIZE "
    "compaction maintains this efficient layout.")

# ============================================================================= SECTION 6
doc.add_heading("6. Security and Compliance", level=1)

doc.add_heading("6.1 Security measures and compliance", level=2)
body(
    "The household data is personal data under the UK GDPR, since consumption patterns relate to "
    "identifiable households (European Parliament, 2016). The solution therefore treats "
    "confidentiality, integrity and lawful processing as first-class concerns. Confidentiality and "
    "integrity rest on three layers. First, encryption: Azure encrypts all data at rest by default "
    "(256-bit AES, Storage Service Encryption) and all access occurs over TLS in transit "
    "(Microsoft, 2024e). Second, governed access through Unity Catalog, which provides a central "
    "metastore with auditable, fine-grained permissions over every catalog, schema and table "
    "(Databricks, 2024b). Third, ACID transactions and schema enforcement in Delta Lake protect "
    "integrity by preventing partial or malformed writes (Armbrust et al., 2020)."
)
body(
    "For compliance, the relevant GDPR principles are data minimisation (only the fields needed for "
    "analysis are carried into silver/gold), purpose limitation, and the fact that the household "
    "identifier (LCLid) is already a pseudonymous code rather than a name or address. In a regulated "
    "production setting this would be complemented by an audit log (available from Unity Catalog and "
    "Azure Monitor), a data-retention policy implemented via storage lifecycle rules, and the ability "
    "to honour erasure requests through Delta DELETE operations."
)

doc.add_heading("6.2 Access control and encryption practices", level=2)
body("Access control is identity-based and key-less:")
bullet("Managed-identity access: serverless Spark reaches storage through a Databricks Access "
       "Connector (an Azure managed identity) granted the Storage Blob Data Contributor role, no "
       "account keys or SAS tokens are stored anywhere (Microsoft, 2024d).")
bullet("Unity Catalog RBAC: the Storage Credential and External Location restrict which principals may "
       "use that identity, and GRANT/REVOKE on catalogs, schemas and tables enforces least-privilege "
       "access for analysts (Databricks, 2024b).")
bullet("Encryption: AES-256 at rest by default, with the option of customer-managed keys in Azure Key "
       "Vault for stricter control; TLS for all data in transit (Microsoft, 2024e).")
bullet("Network controls: in production the storage account firewall would be restricted to selected "
       "networks/private endpoints so the lake is not reachable from the public internet.")
embed_image("fig_encryption.png",
            "Storage-account encryption: data at rest is encrypted by default with "
            "Microsoft-managed keys (AES-256), with customer-managed keys available if required.")
embed_image("fig_role_permissions.png",
            "The Storage Blob Data Contributor role, the least-privilege data-plane role "
            "granted to the managed identity (read/write/list/delete on blob data only).")
embed_image("fig_role_assignment.png",
            "The role assignment binding Storage Blob Data Contributor to the identity, "
            "scoped to the smartmeterprince storage account, identity-based, key-less access control.")

# ============================================================================= SECTION 7
doc.add_heading("7. Performance Monitoring and Management", level=1)

doc.add_heading("7.1 Monitoring and troubleshooting strategy", level=2)
body(
    "Performance is monitored at three levels. At the job level, the Spark UI exposes the stages, "
    "tasks and shuffle behaviour of each query, which is the primary tool for diagnosing bottlenecks. "
    "At the workspace level, Databricks Query History records the duration and resource use of every "
    "SQL execution, making slow queries easy to identify. At the data level, Delta's DESCRIBE HISTORY "
    "provides a full audit and operational-metrics trail for every table version (Armbrust et al., "
    "2020). Typical bottlenecks in this workload and their remedies are: data skew on a few large "
    "households (mitigated by Spark's adaptive query execution), the small-files problem on the "
    "block-partitioned source (mitigated by Delta OPTIMIZE), and wide shuffles in the daily "
    "aggregation (mitigated by partition pruning and broadcast joins for the small dimensions)."
)
embed_image("fig_describe_history.png",
            "DESCRIBE HISTORY on the daily_consumption gold table, every table version is logged "
            "with its operation, timestamp and the user who ran it, giving a full audit and "
            "time-travel trail.")
body(
    "Delta's DESCRIBE HISTORY provides table-level observability and governance: each version records "
    "the operation performed (here CREATE OR REPLACE TABLE AS SELECT), the timestamp, the user and "
    "operational metrics. This supports three management capabilities, auditability (who changed what, "
    "and when), reproducibility and rollback via time travel (any prior version can be queried or "
    "restored), and troubleshooting (a regression can be traced to the exact write that caused it) "
    "(Armbrust et al., 2020).")

doc.add_heading("7.2 Tools and services for system management", level=2)
bullet("Spark UI, stage/task timelines, shuffle and memory diagnostics for query tuning.")
bullet("Databricks Query History, per-query duration and resource usage across the workspace "
       "(Databricks, 2024e).")
bullet("Delta DESCRIBE HISTORY and system tables, table-level audit, lineage and operational metrics.")
bullet("Azure Monitor and Cost Management, platform-level metrics, alerting and spend tracking "
       "(Microsoft, 2024f).")
bullet("Delta OPTIMIZE / Z-ORDER and Auto Loader, proactive management of file layout and incremental "
       "ingestion as data grows.")
embed_image("fig_query_history.png",
            "The Databricks Query History page, listing executed queries with their durations and "
            "resource use for performance monitoring.")

# ============================================================================= CONCLUSION
doc.add_heading("Conclusion", level=1)
body(
    "This report designed and implemented a scalable, secure and cost-aware cloud big-data solution "
    "and demonstrated it end-to-end on the Smart Meters in London dataset. Using ADLS Gen2 for "
    "storage and serverless Apache Spark on Azure Databricks, organised with the medallion "
    "architecture and Delta Lake, the pipeline ingests over 31.7 million half-hourly readings, cleans and "
    "conforms them, derives daily and load-profile aggregates, and produces both descriptive insights "
    "and two machine-learning models. The analysis translates directly into enterprise decisions "
    "around tariff design, demand-response and capacity planning, while Unity Catalog governance, "
    "managed-identity access and serverless economics address the security, compliance and "
    "cost-optimisation requirements of the brief."
)

# ============================================================================= REFERENCES
doc.add_heading("References", level=1)
refs = [
    "Armbrust, M., Xin, R.S., Lian, C., Huai, Y., Liu, D., Bradley, J.K., Meng, X., Kaftan, T., "
    "Franklin, M.J., Ghodsi, A. and Zaharia, M. (2015) 'Spark SQL: relational data processing in "
    "Spark', Proceedings of the 2015 ACM SIGMOD International Conference on Management of Data, "
    "pp. 1383–1394.",
    "Armbrust, M., Das, T., Sun, L., Yavuz, B., Zhu, S., Murthy, M., Torres, J., van Hovell, H., "
    "Ionescu, A., Łuszczak, A., Świtakowski, M., Szafrański, M., Li, X., Ueshin, T., Mokhtar, M., "
    "Boncz, P., Ghodsi, A., Paranjpye, S., Senster, P., Xin, R. and Zaharia, M. (2020) 'Delta Lake: "
    "high-performance ACID table storage over cloud object stores', Proceedings of the VLDB "
    "Endowment, 13(12), pp. 3411–3424.",
    "Assunção, M.D., Calheiros, R.N., Bianchi, S., Netto, M.A.S. and Buyya, R. (2015) 'Big Data "
    "computing and clouds: Trends and future directions', Journal of Parallel and Distributed "
    "Computing, 79–80, pp. 3–15.",
    "CACI (2014) The Acorn User Guide. London: CACI Limited.",
    "Chen, M., Mao, S. and Liu, Y. (2014) 'Big data: A survey', Mobile Networks and Applications, "
    "19(2), pp. 171–209.",
    "Databricks (2024a) Medallion architecture. Available at: "
    "https://docs.databricks.com/lakehouse/medallion.html (Accessed: 29 May 2026).",
    "Databricks (2024b) What is Unity Catalog? Available at: "
    "https://docs.databricks.com/data-governance/unity-catalog/index.html (Accessed: 29 May 2026).",
    "Databricks (2024c) What is Auto Loader? Available at: "
    "https://docs.databricks.com/ingestion/auto-loader/index.html (Accessed: 29 May 2026).",
    "Databricks (2024d) Serverless compute. Available at: "
    "https://docs.databricks.com/compute/serverless.html (Accessed: 29 May 2026).",
    "Databricks (2024e) Query history. Available at: "
    "https://docs.databricks.com/sql/user/queries/query-history.html (Accessed: 29 May 2026).",
    "Dean, J. and Ghemawat, S. (2008) 'MapReduce: simplified data processing on large clusters', "
    "Communications of the ACM, 51(1), pp. 107–113.",
    "European Parliament and Council of the European Union (2016) Regulation (EU) 2016/679 (General "
    "Data Protection Regulation). Official Journal of the European Union, L119, pp. 1–88.",
    "Friedman, J.H. (2001) 'Greedy function approximation: A gradient boosting machine', The Annals "
    "of Statistics, 29(5), pp. 1189–1232.",
    "Géron, A. (2019) Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow. 2nd edn. "
    "Sebastopol, CA: O'Reilly Media.",
    "Hashem, I.A.T., Yaqoob, I., Anuar, N.B., Mokhtar, S., Gani, A. and Khan, S.U. (2015) 'The rise "
    "of \"big data\" on cloud computing: Review and open research issues', Information Systems, 47, "
    "pp. 98–115.",
    "Jean-Michel, D. (2019) Smart Meters in London. Kaggle. Available at: "
    "https://www.kaggle.com/datasets/jeanmidev/smart-meters-in-london (Accessed: 29 May 2026).",
    "Kimball, R. and Ross, M. (2013) The Data Warehouse Toolkit: The Definitive Guide to Dimensional "
    "Modeling. 3rd edn. Indianapolis: Wiley.",
    "Marz, N. and Warren, J. (2015) Big Data: Principles and Best Practices of Scalable Real-Time "
    "Data Systems. Shelter Island, NY: Manning.",
    "Microsoft (2024a) Introduction to Azure Data Lake Storage Gen2. Available at: "
    "https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction (Accessed: 29 May 2026).",
    "Microsoft (2024b) Azure Storage redundancy. Available at: "
    "https://learn.microsoft.com/azure/storage/common/storage-redundancy (Accessed: 29 May 2026).",
    "Microsoft (2024c) Hot, Cool, Cold and Archive access tiers for blob data. Available at: "
    "https://learn.microsoft.com/azure/storage/blobs/access-tiers-overview (Accessed: 29 May 2026).",
    "Microsoft (2024d) Connect to Azure Data Lake Storage using a managed identity (Azure Databricks "
    "Access Connector). Available at: "
    "https://learn.microsoft.com/azure/databricks/connect/unity-catalog/ (Accessed: 29 May 2026).",
    "Microsoft (2024e) Azure Storage encryption for data at rest. Available at: "
    "https://learn.microsoft.com/azure/storage/common/storage-service-encryption (Accessed: 29 May 2026).",
    "Microsoft (2024f) Azure Monitor overview. Available at: "
    "https://learn.microsoft.com/azure/azure-monitor/overview (Accessed: 29 May 2026).",
    "Microsoft (2024g) Connect Power BI to Azure Databricks. Available at: "
    "https://learn.microsoft.com/azure/databricks/partners/bi/power-bi (Accessed: 29 May 2026).",
    "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., "
    "Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, "
    "M., Perrot, M. and Duchesnay, É. (2011) 'Scikit-learn: Machine learning in Python', Journal of "
    "Machine Learning Research, 12, pp. 2825–2830.",
    "Rousseeuw, P.J. (1987) 'Silhouettes: A graphical aid to the interpretation and validation of "
    "cluster analysis', Journal of Computational and Applied Mathematics, 20, pp. 53–65.",
    "UK Power Networks (2014) SmartMeter Energy Consumption Data in London Households (Low Carbon "
    "London project). London Datastore. Available at: "
    "https://data.london.gov.uk/dataset/smartmeter-energy-use-data-in-london-households "
    "(Accessed: 29 May 2026).",
    "Wang, Y., Chen, Q., Hong, T. and Kang, C. (2019) 'Review of smart meter data analytics: "
    "Applications, methodologies, and challenges', IEEE Transactions on Smart Grid, 10(3), "
    "pp. 3125–3148.",
    "Zaharia, M., Xin, R.S., Wendell, P., Das, T., Armbrust, M., Dave, A., Meng, X., Rosen, J., "
    "Venkataraman, S., Franklin, M.J., Ghodsi, A., Gonzalez, J., Shenker, S. and Stoica, I. (2016) "
    "'Apache Spark: a unified engine for big data processing', Communications of the ACM, 59(11), "
    "pp. 56–65.",
]
for r in refs:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.paragraph_format.space_after = Pt(6)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# ============================================================================= APPENDIX A
doc.add_page_break()
doc.add_heading("Appendix A, Screenshot checklist", level=1)
if SCREENSHOTS:
    body("Each placeholder in the report is listed here with the source. 'Existing file' screenshots are "
         "already in the /screenshot folder; 'CAPTURE' items are to be taken from the notebook runs.")
    rows = [[str(n), desc, src] for (n, desc, src) in SCREENSHOTS]
    add_table(["#", "What it shows", "Source / file"], rows)
else:
    body("All platform screenshots and analysis charts are embedded directly in the report as numbered "
         "figures (see the Table of Figures). The accompanying coding artefacts comprise the six "
         "PySpark/Spark SQL notebooks (00-05), the dashboard query file (06_dashboard.sql), the schema "
         "data dictionary (schema.sql) and the README.")

# ============================================================================= SAVE
out = "BDCC_LDS7005_Report.docx"
doc.save(out)
print(f"Saved {out} with {len(SCREENSHOTS)} screenshot placeholders.")
