# workflows — Laktory-native path

This directory demonstrates deploying Laktory pipelines using Laktory's built-in deployment backend (Pulumi). No Databricks CLI bundle setup is required — `laktory deploy` manages the full lifecycle.

For teams already using DAB, see [`../workflows-dab/`](../workflows-dab/README.md) instead.

## What's deployed

Defined in [`stack.yaml`](stack.yaml):

| Resource | Description |
|---|---|
| `pl-taxi-trips` | Intro-level pipeline — reads from the Databricks `samples.nyctaxi.trips` table, adds computed columns, filters short trips |
| `pl-stock-prices` | Full medallion pipeline — streaming ingestion from Yahoo Finance, quality expectations, quarantine sinks, SCD Type 1 merge, Narwhals-based gold aggregation, quality monitor |
| `job-stock-prices` | Job that runs the stock prices pipeline on a daily schedule |
| `app-stocks-dash` | Databricks App serving a Dash-based stocks dashboard |
| Queries, workspace tree | Supporting SQL queries and workspace file structure |

## The `lake` package

[`lake/`](lake/) is a custom Python package built as a wheel and deployed alongside the pipelines. It contains:

- `DataEvent` / `DataProducer` — Pydantic domain models for wrapping and writing event data to Databricks Volumes
- `dataframe_ext.py` — Narwhals namespace extensions (e.g., `lake.get_sample_zones`) callable from pipeline transformer nodes

The wheel is uploaded to the workspace automatically during deploy and referenced by pipelines via the `${vars.lake_package}` variable.

## Deploy

**Prerequisites:** set the following environment variables (see `stack.yaml` for the full list):

```bash
export DATABRICKS_HOST=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...
```

**Deploy to dev:**
```bash
laktory deploy --env dev
```

**Deploy to production:**
```bash
laktory deploy --env prd
```

Environment-specific variables (`catalog`, `sql_tasks_warehouse_id`, etc.) are declared under `environments.dev` / `environments.prd` in `stack.yaml`.
