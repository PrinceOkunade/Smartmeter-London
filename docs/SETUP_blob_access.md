# Setup — Let Serverless Databricks read your Azure Blob container

On **Serverless**, the only supported way to read `abfss://` data is via a Unity Catalog
**External Location**. You do this **once**; afterwards every notebook reads your blob directly.

> **Prerequisite check (do these first):**
> 1. Storage account is **ADLS Gen2** → Portal → storage account → *Configuration* →
>    **Hierarchical namespace = Enabled**. If Disabled, use the **Fallback** at the bottom.
> 2. You can create resources + assign roles (Owner / User Access Administrator on the sub).
>
> You will need these names handy (used in the notebook widgets):
> `storage account name`, `container name`.

---

## Step 1 — Create a Databricks Access Connector (managed identity)
Azure Portal → search **"Access Connector for Azure Databricks"** → **Create**:
- Same **resource group** & **region** as your Databricks workspace.
- Name e.g. `ac-databricks-smartmeter`. Create.
- Open it → copy its **Resource ID** (Settings → Properties): looks like
  `/subscriptions/.../resourceGroups/.../providers/Microsoft.Databricks/accessConnectors/ac-...`.

## Step 2 — Give the connector access to your storage
Portal → your **storage account** → **Access Control (IAM)** → **Add role assignment**:
- Role: **Storage Blob Data Contributor**
- Assign access to: **Managed identity** → select your Access Connector → **Review + assign**.

## Step 3 — Create a Storage Credential in Databricks
Databricks → **Catalog** (left nav) → **External Data** → **Credentials** → **Create credential**:
- Type: **Azure Managed Identity**
- Name: `cred-smartmeter`
- Access Connector ID: paste the Resource ID from Step 1. → Create.

## Step 4 — Create the External Location
Databricks → **Catalog** → **External Data** → **External Locations** → **Create location**:
- Name: `ext-smartmeter`
- URL: `abfss://<container>@<storageaccount>.dfs.core.windows.net/`
  (replace `<container>` and `<storageaccount>` with your names)
- Storage credential: `cred-smartmeter` → Create.
- Click **Test connection** — it should pass.

## Step 5 — Verify from a notebook
In any notebook (Serverless attached), run:
```python
dbutils.fs.ls("abfss://<container>@<storageaccount>.dfs.core.windows.net/")
```
You should see your files/folders (incl. the `halfhourly` folder). **Paste this output to me**
so we lock the exact paths in `00_config_and_setup` widgets.

---

## Fallback (if HNS is Disabled or role assignment is blocked) — use a Volume
Fast, always works on serverless, ~10 minutes:
1. Run notebook `00` (it creates a Volume `/Volumes/<catalog>/smartmeter/raw`).
2. Catalog → your catalog → `smartmeter` → `raw` → **Upload**: drop your 21 half-hourly blocks
   into `raw/halfhourly/` and the small CSVs into `raw/`.
3. In `00`, set the `source_mode` widget to **volume**. Done — same pipeline, different source.

In the report you still describe Azure Blob/ADLS as your cloud storage tier; the Volume is just
the working copy Databricks reads.
