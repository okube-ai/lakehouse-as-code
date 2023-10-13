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
        self.set_warehouses()

    @property
    def cluster_env_vars(self):
        return {
            "AZURE_KEYVAULT_URL": "{{secrets/azure/keyvault-url}}",
            "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
            "AZURE_CLIENT_ID": "{{secrets/azure/client-id}}",
            "AZURE_CLIENT_SECRET": "{{secrets/azure/client-secret}}",
        }

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

        with open("initscripts.yaml") as fp:
            init_scripts = [models.InitScript.model_validate(s) for s in yaml.safe_load(fp)]

        for init_script in init_scripts:
            init_script.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
            ))

        # TODO: Add scripts to the list of allowed list

    # ----------------------------------------------------------------------- #
    # Clusters                                                                #
    # ----------------------------------------------------------------------- #

    def set_clusters(self):
        with open("clusters.yaml") as fp:
            clusters = [models.Cluster.model_validate(c) for c in yaml.safe_load(fp)]

        for cluster in clusters:
            cluster.spark_env_vars = self.cluster_env_vars
            cluster.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
                depends_on=self.secret_resources,
            ))

    # ----------------------------------------------------------------------- #
    # Warehouses                                                              #
    # ----------------------------------------------------------------------- #

    def set_warehouses(self):
        with open("warehouses.yaml") as fp:
            warehouses = [models.Warehouse.model_validate(c) for c in yaml.safe_load(fp)]

        for warehouse in warehouses:
            warehouse.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
            ))


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
