# Lakehouse as Code with Laktory

A reference template for building a production Databricks lakehouse using the [Laktory](https://github.com/okube-ai/laktory) DataOps framework.

## What is Laktory?

Laktory is a declarative framework for the full Databricks lakehouse stack. Define your resources in YAML and deploy them with a single command — data pipelines (DLT, Jobs), Unity Catalog resources (metastores, catalogs, schemas, grants), workspace resources (clusters, warehouses, secret scopes), and cloud infrastructure. It supports streaming and batch, enforces data quality expectations, and works with both PySpark and Narwhals. More at [github.com/okube-ai/laktory](https://github.com/okube-ai/laktory).

## What this repo demonstrates

**Cloud infrastructure** (`{cloud}_infra/`)
- Storage accounts, key vaults, and managed identities for dev and prd environments

**Unity Catalog** (`unity-catalog/`)
- A metastore with Azure-backed storage and managed identity data accesses
- Role-based and domain-based identity groups, users, and service principals
- Dev, prd, sandbox, and libraries catalogs with schemas, volumes, and external locations

**Workspace** (`workspace/`)
- A shared all-purpose cluster, a serverless SQL warehouse, and a cluster policy
- Secret scopes for Azure credentials and Databricks tokens
- Workspace directory structure and a cloned Laktory Git repo

**Data pipelines** (`workflows/` or `workflows-dab/`)
- `pl-stock-prices` — full medallion pipeline (bronze → silver → gold): streaming ingestion from Yahoo Finance, quality expectations with quarantine sinks, SCD Type 1 merge, Narwhals-based gold aggregation, quality monitor
- `pl-taxi-trips` — intro-level pipeline reading from a Databricks sample dataset, showing custom transformer functions from the `lake` package
- A custom `lake` Python package (domain models, Narwhals namespace extensions) deployed as a wheel alongside the pipelines

## Project structure

| Directory | Purpose |
|---|---|
| `{cloud}_infra/` | Cloud provider resources via Pulumi |
| `unity-catalog/` | Metastore, catalogs, schemas, external locations, users, groups, grants |
| `workspace/` | Clusters, SQL warehouse, cluster policy, secret scopes, Git repos |
| `workflows/` | Data pipelines — Laktory-native deployment path |
| `workflows-dab/` | Data pipelines — DAB integration path |


## Workflows: two deployment paths

The `unity-catalog/` and `workspace/` stacks use Laktory's native deployment backend. For `workflows/`, two paths are available, both using the same Laktory pipeline YAML syntax:

| | `workflows/`                                      | `workflows-dab/` |
|---|---------------------------------------------------|---|
| **Backend** | Pulumi (`laktory deploy`)                         | Databricks CLI (`databricks bundle`) |
| **Best for** | Teams adopting Laktory as their primary IaC layer | Teams already using DAB who want to add Laktory pipelines |
| **How it works** | Laktory manages the full deployment lifecycle     | `laktory.dab:build_resources` generates native DAB resources from Laktory pipeline YAMLs at bundle resolution time |

## Okube

Okube is committed to building open source data and ML engineering tools. Contributions are welcome.
