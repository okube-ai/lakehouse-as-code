# Lakehouse as Code with Laktory 

## Okube Company 

Okube is committed to develop open source data and ML engineering tools. This is an open space. Contributions are more than welcome.

## Laktory
Laktory is a DataOps framework for building Databricks lakehouse. More information here:
https://github.com/okube-ai/laktory

## Template
This repository acts as a comprehensive template on how to deploy a lakehouse as code using Laktory through
4 pulumi projects:
- `{cloud_provider}_infra`: Deploy the required resources on your cloud provider
- `unity-catalog`: Setup users, groups, catalogs, schemas and manage grants
- `workspace`: Setup secrets, clusters and warehouses and common files/notebooks
- `workflows`: The data workflows to build your lakehouse
