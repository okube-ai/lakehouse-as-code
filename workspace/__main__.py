import os

import yaml

import pulumi
import pulumi_databricks as databricks
from laktory import models


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #


class Service:
    def __init__(self):
        self.org = "o3"
        self.service = "lakehouse"
        self.pulumi_config = pulumi.Config()
        self.env = pulumi.get_stack()
        self.infra_stack = pulumi.StackReference(f"okube/azure-infra/{self.env}")

        # Providers
        self.workspace_provider = databricks.Provider(
            "provider-workspace-neptune",
            host=self.infra_stack.get_output("dbks-ws-host"),
            azure_client_id=self.infra_stack.get_output("neptune-client-id"),
            azure_client_secret=self.infra_stack.get_output("neptune-client-secret"),
            azure_tenant_id="ab09b389-116f-42c5-9826-3505f22a906b",
        )

        # Resources
        self.pipelines = {}
        self.pipeline_ids = {}

    def run(self):
        self.set_notebooks()
        self.set_workspace_files()
        self.set_pipelines()
        self.set_jobs()

    # ----------------------------------------------------------------------- #
    # Properties                                                              #
    # ----------------------------------------------------------------------- #

    @property
    def cluster_env_vars(self):
        return {
            "AZURE_KEYVAULT_URL": "{{secrets/azure/keyvault-url}}",
            "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
            "AZURE_CLIENT_ID": "{{secrets/azure/client-id}}",
            "AZURE_CLIENT_SECRET": "{{secrets/azure/client-secret}}",
            "LAKTORY_WORKSPACE_ENV": self.env,
        }

    # ----------------------------------------------------------------------- #
    # Notebooks                                                               #
    # ----------------------------------------------------------------------- #

    def set_notebooks(self):
        with open("notebooks.yaml") as fp:
            notebooks = [models.Notebook.model_validate(s) for s in yaml.safe_load(fp)]

        for notebook in notebooks:
            notebook.deploy(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )

    # ----------------------------------------------------------------------- #
    # Workspace Files                                                         #
    # ----------------------------------------------------------------------- #

    def set_workspace_files(self):

        with open("workspacefiles.yaml") as fp:
            workspace_files = [
                models.WorkspaceFile.model_validate(s) for s in yaml.safe_load(fp)
            ]

        for workspace_file in workspace_files:
            workspace_file.deploy(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )

    # ----------------------------------------------------------------------- #
    # Pipelines                                                               #
    # ----------------------------------------------------------------------- #

    def set_pipelines(self):
        root_dir = "./pipelines/"

        pipelines = []
        for filename in os.listdir(root_dir):
            filepath = os.path.join(root_dir, filename)
            with open(filepath, "r") as fp:
                pipelines += [models.Pipeline.model_validate_yaml(fp)]

        for pipeline in pipelines:
            pipeline.vars = {
                "env": self.env,
                "is_dev": self.env == "dev",
            }
            pipeline.clusters[0].spark_env_vars = self.cluster_env_vars

            # TODO: Refactor and improve
            for table in pipeline.tables:
                if table.event_source:
                    table.event_source.events_root = f"/Volumes/{self.env}/sources/landing/events/"

            pipeline.deploy(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )
            self.pipelines[pipeline.name] = pipeline
            self.pipeline_ids[pipeline.name] = pipeline.id

    # ----------------------------------------------------------------------- #
    # Jobs                                                                    #
    # ----------------------------------------------------------------------- #

    def set_jobs(self):
        root_dir = "./jobs/"

        jobs = []
        for filename in os.listdir(root_dir):
            filepath = os.path.join(root_dir, filename)
            with open(filepath, "r") as fp:
                jobs += [models.Job.model_validate_yaml(fp)]

        vars = {f"{k}-id": v for k, v in self.pipeline_ids.items()}
        vars["pause_status"] = "PAUSED" if self.env == "dev" else None

        for job in jobs:
            job.vars = vars
            job.deploy(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
