"""A Python Pulumi program"""

import pulumi


"""

    def set_databricks_mount(self):
        # TODO: REPLACE WITH VOLUME
        mount = databricks.Mount(
            "landing-mount",
            name="landing/",
            uri=Output.all(container=self.container_landing.name, account=self.storage_account.name).apply(
                lambda args: f"abfss://{args['container']}@{args['account']}.dfs.core.windows.net/"),
            extra_configs={
                "fs.azure.account.auth.type": "OAuth",
                "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
                "fs.azure.account.oauth2.client.id": self.pulumi_config.get("neptune_client_id"),
                "fs.azure.account.oauth2.client.secret": self.pulumi_config.get_secret("neptune_client_secret"),
                "fs.azure.account.oauth2.client.endpoint": f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token",
            },
            opts=pulumi.ResourceOptions(
                provider=self.databricks_workspace_provider,
                replace_on_changes=["*"],
                delete_before_replace=True,
            ),
        )
    

"""

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
        self.secret_resources = []

    def run(self):
        self.set_secrets()
        self.set_init_scripts()
        self.set_clusters()

    # ----------------------------------------------------------------------- #
    # Secrets                                                                 #
    # ----------------------------------------------------------------------- #

    def set_secrets(self):

        with open("secretscopes.yaml") as fp:
            secret_scopes = [models.SecretScope.model_validate(s) for s in yaml.safe_load(fp)]

        self.secret_resources = []
        for secret_scope in secret_scopes:

            for s in secret_scope.secrets:
                if s.key == "keyvault-url":
                    s.value = self.infra_stack.get_output("keyvault-url")
                elif s.key == "tenant-id":
                    s.value = self.infra_stack.get_output("tenant-id")
                elif s.key == "client-id":
                    s.value = self.infra_stack.get_output("neptune-client-id")
                elif s.key == "client-secret":
                    s.value = self.infra_stack.get_output("neptune-client-secret")

                if s.value is None:
                    raise ValueError(f"Secret {s.scope}.{s.key} value empty")

            self.secret_resources += [
                secret_scope.deploy(opts=pulumi.ResourceOptions(provider=self.workspace_provider))
            ]

    # ----------------------------------------------------------------------- #
    # Init Scripts                                                            #
    # ----------------------------------------------------------------------- #

    def set_init_scripts(self):
        """
        Init scripts are installed in Unity Catalog Volumes in the unity
        catalog stack. However, no isolation clusters can't connect to UC and
        require a different location.
        """

        with open("init_scripts.yaml") as fp:
            init_scripts = [models.InitScript.model_validate(s) for s in yaml.safe_load(fp)]

        for init_script in init_scripts:
            init_script.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
            ))

    # ----------------------------------------------------------------------- #
    # Clusters                                                                #
    # ----------------------------------------------------------------------- #

    def set_clusters(self):
        with open("clusters.yaml") as fp:
            clusters = [models.Cluster.model_validate(c) for c in yaml.safe_load(fp)]

        for cluster in clusters:
            cluster.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
                depends_on=self.secret_resources,
            ))


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
