# Architectural Patterns

## 1. Stack YAML Configuration Pattern

Every deployable module (`workflows/`, `unity-catalog/`, `workspace/`) owns a `stack.yaml` that follows the same schema:

```
name / organization / backend: pulumi
pulumi.config:        provider credentials via ${vars.*} interpolation
resources:            typed resource maps, each value !use'd from a separate YAML file
variables:            stack-level defaults
environments.dev/prd: overrides (catalog name, warehouse IDs, feature flags)
```

References: `workflows/stack.yaml:1-38`, `unity-catalog/stack.yaml`, `workspace/stack.yaml`

**Convention:** resource YAML files live in `resources/` and are included with the `!use` directive. Keep one resource per file; name the file `{resource-name}.yaml` or `{resource-name}.{type}.yml` (DAB convention).

Variable interpolation uses `${vars.VAR_NAME}`. Environment-specific values are declared under `environments.dev` / `environments.prd` and override the top-level `variables` block at deploy time.

---

## 2. Medallion Pipeline Structure (Laktory)

Pipelines are declared as node DAGs in YAML. Each node follows the pattern:

```
nodes:
  - name: {layer}_{entity}          # brz_ / slv_ / gld_ prefix
    source:
      node_name: …                  # upstream node, OR
      path: /Volumes/…              # raw storage path
      as_stream: true/false
    transformer:
      nodes:
        - expr: "SELECT … FROM {df}"   # inline SQL (use {df} as table alias)
        - func_name: drop_duplicates   # Spark/Narwhals function call
          func_kwargs: …
    sinks:
      - table_name: …
        catalog_name: ${vars.catalog}
        mode: APPEND | MERGE | OVERWRITE
```

References: `workflows/resources/pl-stock-prices.yaml:33-223`

**Bronze nodes** read from Volumes with `as_stream: true` and write with `mode: APPEND`.  
**Silver nodes** chain from bronze via `node_name`, may include `expectations` (QUARANTINE / DROP actions), and can write to a quarantine sink (`is_quarantine: true`).  
**Gold nodes** use `as_stream: false`, apply `NARWHALS` dataframe API for framework-agnostic aggregations, and attach `databricks_quality_monitor` configs directly on the sink.

SCD Type-1 merges are expressed inline on the sink:

```yaml
mode: MERGE
merge_cdc_options:
  order_by: extracted_at
  primary_keys: [symbol]
  scd_type: 1
```

Reference: `workflows/resources/pl-stock-prices.yaml:126-131`

---

## 3. Pydantic Domain Models (`lake` package)

Custom domain models in `workflows/lake/lake/` extend `pydantic.BaseModel`:

- **`DataProducer`** (`dataproducer.py:7-24`): lightweight metadata (name, party type literal).
- **`DataEvent`** (`dataevent.py:26-311`): full event model with computed fields added in `model_post_init` (name, producer name, timestamp), property-based storage paths (`dirpath`, `event_root`, `events_root`), serialization control via `model_dump` overrides, and a `to_databricks()` method for writing to Volumes.

**Pattern:** computed/derived attributes are added in `model_post_init`, not in `__init__`. Fields that should be excluded from serialization are listed in the module-level `EXCLUDES` list (`dataevent.py:18-23`).

---

## 4. Narwhals Namespace Extensions

The `lake` package registers custom namespaces with Narwhals for dataframe-agnostic column logic:

- `LakeDataFrameNamespace` — DataFrame-level operations (e.g., `with_last_modified()`).
- `LakeExprNamespace` — Expression-level operations (e.g., `symbol_to_name()`).

Reference: `workflows/lake/lake/dataframe_ext.py:8-28`

These are registered so pipeline YAML can call `laktory.` or custom namespace functions by name in `func_name` transformer nodes.

---

## 5. Cloud Infrastructure Service Class Pattern

Each `{cloud}_infra/__main__.py` defines a `Service` class:

```python
class Service:
    def __init__(self):
        self.config = pulumi.Config()
        # Initialize providers
        self.databricks_workspace_provider = …
    
    def set_resource_group(self): …
    def set_storage(self): …
    def set_keyvault(self): …
```

References: `azure-infra/__main__.py:14-42`, `gcp-infra/__main__.py:14-36`

Cross-stack references use `pulumi.StackReference()` to read outputs from sibling stacks (e.g., workspace URL from `azure-infra` consumed by `unity-catalog`).

---

## 6. Databricks Asset Bundles (DAB) Resource Convention

The `workflows-dab/` tree uses DAB YAML with the pattern:

```yaml
resources:
  pipelines:
    {resource-key}:
      name: pl-{entity}
      …
  jobs:
    {resource-key}:
      name: job-{entity}
      tasks:
        - pipeline_task:
            pipeline_id: ${resources.pipelines.{key}.id}
```

References: `workflows-dab/resources/taxi-trips.job.yml`, `workflows-dab/resources/pl-taxi-trips.yml`

Cross-resource references use `${resources.{type}.{key}.id}` interpolation (DAB native). File naming convention: `{entity}.{type}.yml` (e.g., `taxi-trips.job.yml`, `pl-taxi-trips.yml`).

---

## 7. CI/CD Gated Promotion Pattern

The GitHub Actions pipeline enforces a one-way promotion gate:

```
deploy dev  →  run DLT on dev  →  preview prd  →  manual approval  →  deploy prd
```

Reference: `.github/workflows/laktory-deploy.yml`

Each stage is a reusable workflow (`_job_laktory_*.yml`). Prd deployment uses separate secrets (`AZURE_CLIENT_ID_PRD`) from dev. The approval job (`_job_release_approval.yml`) is the gate between preview and deploy.

---

## 8. Test Fixture Pattern (workflows-dab)

Tests use Databricks Connect via two pytest fixtures defined in `tests/conftest.py`:

- `spark` — returns a `DatabricksSession`-backed `SparkSession`.
- `load_fixture(filename)` — loads JSON or CSV from `fixtures/` and returns a Spark DataFrame.

Reference: `workflows-dab/tests/conftest.py:21-56`

If no compute is configured, `pytest_configure` auto-enables serverless compute via `DATABRICKS_SERVERLESS_COMPUTE_ID=auto`.
