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

    def run(self):
        self.set_notebooks()
        self.set_pipelines()

    # ----------------------------------------------------------------------- #
    # Notebooks                                                               #
    # ----------------------------------------------------------------------- #

    def set_notebooks(self):
        with open("notebooks.yaml") as fp:
            notebooks = [models.Notebook.model_validate(s) for s in yaml.safe_load(fp)]

        for notebook in notebooks:

            notebook.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
            ))

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
            if self.env != "prod":
                pipeline.development = True
            pipeline.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
            ))


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
