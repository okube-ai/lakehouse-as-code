import yaml

import pulumi
import pulumi_databricks as databricks
from laktory import models
from laktory import pulumi_resources


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
        self.set_directories()
        self.set_workspace_files()
        self.set_clusters()
        self.set_warehouses()

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
    # Secrets                                                                 #
    # ----------------------------------------------------------------------- #

    def set_secrets(self):
        with open("secretscopes.yaml") as fp:
            secret_scopes = [
                models.SecretScope.model_validate(s) for s in yaml.safe_load(fp)
            ]

        self.secret_resources = []
        for secret_scope in secret_scopes:
            secret_scope.variables = {
                "secret-keyvault-url": self.infra_stack.get_output("keyvault-url"),
                "secret-tenant-id": self.infra_stack.get_output("tenant-id"),
                "secret-client-id": self.infra_stack.get_output("neptune-client-id"),
                "secret-client-secret": self.infra_stack.get_output("neptune-client-secret"),
            }
            secret_scope.options.aliases = [
                f"urn:pulumi:dev::workspace-conf::laktory:databricks:SecretScope$databricks:index/secretScope:SecretScope::{secret_scope.resource_name}"
            ]

            self.secret_resources += secret_scope.to_pulumi(
                opts=pulumi.ResourceOptions(provider=self.workspace_provider)
            ).values()

    # ----------------------------------------------------------------------- #
    # Directories                                                             #
    # ----------------------------------------------------------------------- #

    def set_directories(self):
        with open("directories.yaml") as fp:
            directories = [
                models.Directory.model_validate(s) for s in yaml.safe_load(fp)
            ]

        for directory in directories:
            directory.options.aliases = [
                f"urn:pulumi:dev::workspace-conf::laktory:databricks:Directory$databricks:index/directory:Directory::{directory.resource_name}"
            ]
            directory.to_pulumi(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )
            pulumi.export(
                directory.resource_name,
                pulumi_resources[directory.resource_name].object_id.apply(lambda v: f"folders/{v}")
            )

    # ----------------------------------------------------------------------- #
    # Workspace Files                                                         #
    # ----------------------------------------------------------------------- #

    def set_workspace_files(self):
        """
        Init scripts are installed in Unity Catalog Volumes in the unity
        catalog stack. However, no isolation clusters can't connect to UC and
        require a different location.
        """

        with open("workspacefiles.yaml") as fp:
            workspace_files = [
                models.WorkspaceFile.model_validate(s) for s in yaml.safe_load(fp)
            ]

        for workspace_file in workspace_files:
            workspace_file.to_pulumi(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )

        # TODO: Add scripts to the list of allowed list

    # ----------------------------------------------------------------------- #
    # Clusters                                                                #
    # ----------------------------------------------------------------------- #

    def set_clusters(self):
        with open("clusters.yaml") as fp:
            clusters = [models.Cluster.model_validate(c) for c in yaml.safe_load(fp)]

        for cluster in clusters:
            cluster.spark_env_vars = self.cluster_env_vars
            cluster.options.aliases = [
                f"urn:pulumi:dev::workspace-conf::laktory:databricks:Cluster$databricks:index/cluster:Cluster::{cluster.resource_name}",
            ]
            cluster.to_pulumi(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                    depends_on=self.secret_resources,
                )
            )

    # ----------------------------------------------------------------------- #
    # Warehouses                                                              #
    # ----------------------------------------------------------------------- #

    def set_warehouses(self):
        with open("warehouses.yaml") as fp:
            warehouses = [
                models.Warehouse.model_validate(c) for c in yaml.safe_load(fp)
            ]

        for warehouse in warehouses:
            warehouse.options.aliases = [
                f"urn:pulumi:dev::workspace-conf::laktory:databricks:Warehouse$databricks:index/sqlEndpoint:SqlEndpoint::{warehouse.resource_name}",
            ]
            warehouse.to_pulumi(
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                )
            )
            pulumi.export(
                f"{warehouse.resource_name}-data-source-id",
                pulumi_resources[warehouse.resource_name].data_source_id
            )


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
