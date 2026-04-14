# Lakehouse as Code — Claude Guide

## Project Overview

Template repository for deploying a full Databricks lakehouse using the [Laktory](https://github.com/okube-ai/laktory) DataOps framework. Demonstrates infrastructure-as-code across AWS/Azure/GCP, Unity Catalog management, and declarative data pipelines. The worked example ingests stock price data from Yahoo Finance through bronze → silver → gold layers.

## Tech Stack

| Layer | Technology |
|---|---|
| IaC / Deployment | Pulumi ≥ 3.0, Laktory ≥ 0.9 |
| Data platform | Databricks (DLT, Jobs, SQL, Volumes, Unity Catalog) |
| Data processing | PySpark, Narwhals (dataframe abstraction) |
| Domain models | Pydantic v2 |
| Package / build | UV, Hatchling |
| Testing | pytest + Databricks Connect |
| CI/CD | GitHub Actions |
| Cloud (active) | Azure (azure-infra is the reference implementation) |

## Key Directories

```
{cloud}_infra/          Cloud provider resources via Pulumi (Service class per provider)
unity-catalog/          Users, groups, catalogs, schemas, grants
workspace/              Clusters, warehouses, secrets, shared notebooks
workflows/              Main Laktory stack — pipelines, jobs, apps
  lake/                 Reusable Python package deployed as a wheel to Databricks
  notebooks/            Entry-point notebooks (jobs/, dlt/, apps/)
  resources/            YAML definitions for pipelines, jobs, queries, etc.
workflows-dab/          Databricks Asset Bundles alternative (newer approach)
  src/workflows/        Shared Python source code
  tests/                pytest suite using Databricks Connect
  fixtures/             JSON/CSV test data
.github/workflows/      CI/CD: deploy dev → run DLT → approval → deploy prd
```

## Essential Commands

```bash
# Run tests (from workflows-dab/)
uv run pytest

# Deploy a Laktory stack (from any stack directory, e.g. workflows/)
laktory deploy --env dev
laktory deploy --env prd

# Preview changes without deploying
laktory preview --env prd

# Deploy via Databricks Asset Bundles (from workflows-dab/)
databricks bundle deploy --target dev
databricks bundle run

# Build the lake wheel (from workflows/lake/)
uv build
```

## Environment Model

Each stack defines `dev` and `prd` environments. Variables like `${vars.catalog}` resolve to `dev` or `prd` at deploy time. The CI/CD pipeline enforces: deploy dev → run DLT validation → manual approval → deploy prd.

## Additional Documentation

- [Architectural Patterns](.claude/docs/architectural_patterns.md) — stack YAML conventions, medallion pipeline structure, Pydantic models, DAB resource patterns; check when modifying pipelines, adding resources, or extending the `lake` package.
