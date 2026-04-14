# unity-catalog

Deploys Databricks account-level and Unity Catalog resources using Laktory with a Pulumi backend. This stack must be deployed before `workflows/` since pipelines depend on the catalogs, schemas, and grants defined here.

## What's deployed

Defined in [`stack.yaml`](stack.yaml):

### Identity

| Resource | Description |
|---|---|
| 4 domain groups | `group-domain-finance`, `-market`, `-nyctaxi`, `-yahoo` — data domain ownership |
| 4 role groups | `group-role-analysts`, `-engineers`, `-metastore-admins`, `-workspace-admins` |
| 3 users | Olivier (admin), a data analyst, and a data engineer |
| 2 service principals | Dev and prd service principals assigned to domain and role groups |

Groups and users are assigned to both dev and prd workspaces. The workspace admins group gets ADMIN-level workspace permissions.

### Metastore

| Resource | Description |
|---|---|
| `metastore-lakehouse` | Azure-backed Unity Catalog metastore (eastus), assigned to dev and prd workspaces |
| 2 data accesses | Managed identities for dev and prd storage, used by external locations |

Delta sharing is enabled (INTERNAL_AND_EXTERNAL).

### Catalogs & schemas

| Catalog | Isolation | Description |
|---|---|---|
| `dev` | OPEN | Development catalog — schemas: `sources`, `sinks`, `yahoo`, `market`, `nyctaxi` |
| `prd` | ISOLATED | Production catalog — same schema layout, isolated from dev |
| `sandbox` | OPEN | Sandbox for ad-hoc exploration — broad access for all account users |
| `libraries` | OPEN | Stores cluster init scripts and shared libraries |

Each catalog has `sources` and `sinks` schemas pre-created with associated Volumes (`landing` and `tables`). The `landing` volume is where ingestion notebooks write raw event data; pipelines read from it.

The `yahoo_dab` and `market_dab` schemas mirror `yahoo` and `market` for the DAB deployment path.

### External locations

Five external locations backed by Azure storage accounts, granting Databricks access to landing and tables storage for both dev and prd environments, plus the metastore storage root.

## Deploy

**Prerequisites:** account-level credentials are required (not workspace-level). Set:

```bash
export DATABRICKS_ACCOUNT_ID=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...
```

**Deploy:**
```bash
laktory deploy --env dev
laktory deploy --env prd
```

Environment-specific variables (workspace IDs, storage URLs, service principal client IDs) are declared under `environments.dev` / `environments.prd` in `stack.yaml`.
