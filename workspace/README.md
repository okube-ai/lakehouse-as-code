# workspace

Deploys Databricks workspace-level resources using Laktory with a Pulumi backend. This covers shared infrastructure — compute, SQL warehouses, secrets, and Git repos — that pipelines and users depend on.

## What's deployed

Defined in [`stack.yaml`](stack.yaml):

### Compute

| Resource | Description |
|---|---|
| `cluster-default` | All-purpose cluster (Spark 17.2, Standard_DS3_v2, 1–4 workers, user isolation) — engineers and analysts can restart |
| `cluster-policy-okube` | Policy capping DBU usage (0–10/hr) with 30-minute auto-termination; enforced for the engineers group |
| `warehouse-default` | 2X-Small serverless SQL warehouse, auto-stops after 10 minutes; accessible to all account users |

### Secrets

| Resource | Description |
|---|---|
| `secret-scope-azure` | Azure credentials (key vault URL, tenant ID, client ID/secret) — used by clusters and pipelines to authenticate against Azure services |
| `secret-scope-databricks` | Databricks PATs for service accounts; read access limited to metastore-admins and workspace-admins |

### Workspace structure

| Resource | Description |
|---|---|
| `directory-laktory-queries` | `/.laktory/queries/` — root for Laktory-managed SQL queries |
| `directory-laktory-alerts` | `/.laktory/alerts/` — root for Laktory-managed alerts |
| `repo-laktory` | Clones the Laktory GitHub repo into the workspace for reference and development |

## Deploy

```bash
export DATABRICKS_HOST=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...
```

```bash
laktory deploy --env dev
laktory deploy --env prd
```

Deploy this stack after `unity-catalog/` and before `workflows/`. The warehouse ID output from this stack is referenced by the workflows stack as `sql_tasks_warehouse_id`.
