import uuid

import pulumi
from pulumi import Output
import pulumi_azure as azure
import pulumi_azure_native as azure_native
import pulumi_azuread as azuread
import pulumi_databricks as databricks


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #

class Service:

    def __init__(self):
        self.org = "o3"
        self.service = "lakehouse"
        self.pulumi_config = pulumi.Config()
        self.azure_config = azure_native.authorization.get_client_config()
        self.env = pulumi.get_stack()
        self.tenant_id = self.azure_config.tenant_id
        self.subscription_id = self.azure_config.subscription_id

        # Providers
        self.databricks_workspace_provider = None

        # Resources
        self.app = None
        self.app_secret = None
        self.sp = None
        self.me = None
        self.rg = None
        self.keyvault = None
        self.storage_account = None
        self.container_landing = None
        self.container_metastore = None
        self.workspace = None

    def run(self):

        # Service principals
        self.set_service_principal()

        # Resources Group
        self.set_resource_group()

        # Key Vault
        self.set_keyvault()

        # Storage Account
        self.set_storage()

        # Databricks workspace
        self.set_databricks_workspace()

        # Databricks connector
        self.set_databricks_connector()

    def set_service_principal(self):

        self.app = azuread.Application(
            "aad-app-neptune",
            display_name=f"Neptune{self.env.title()}"
        )
        pulumi.export("neptune-object-id", self.app.object_id)
        pulumi.export("neptune-client-id", self.app.application_id)

        self.sp = azuread.ServicePrincipal(
            "aad-sp-neptune",
            application_id=self.app.application_id,
        )

        self.app_secret = azuread.ApplicationPassword(
            "aad-app-secret-neptune",
            application_object_id=self.app.object_id,
            end_date_relative=f"{24*30*6}h",
        )
        pulumi.export("neptune-client-secret", self.app_secret.value)

    def set_resource_group(self):
        k = f"{self.org}-rg-{self.service}"
        self.rg = azure_native.resources.ResourceGroup(
            k,
            location="eastus",
            resource_group_name=f"{k}-{self.env}"
        )
        pulumi.export("resource-group-name", self.rg.name)

    def set_keyvault(self):

        k = f"{self.org}-kv-{self.service}"
        self.keyvault = azure_native.keyvault.Vault(
            k,
            vault_name=f"{k}-{self.env}",
            resource_group_name=self.rg.name,
            location=self.rg.location,
            properties=azure_native.keyvault.VaultPropertiesArgs(
                sku=azure_native.keyvault.SkuArgs(
                    family="A",
                    name=azure_native.keyvault.SkuName.STANDARD,
                ),
                tenant_id=self.tenant_id,
                enable_rbac_authorization=True,
            ),
        )

        # Secrets
        for key, value in [
            # ("azure-devops-token", self.pulumi_config.get_secret("azure_devops_token"))
        ]:
            self._set_secret(key, value)

        # RBAC - Olivier - Key Vault Administrator
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#key-vault-administrator
        self._set_rbac(
            name="rbac-87073600-2bce-41d9-ae65-15eda3e6f858-keyvault",
            role_id="00482a5a-887f-4fb3-b363-3b7fe8e74483",
            principal_id="87073600-2bce-41d9-ae65-15eda3e6f858",
            principal_type="User",
            scope=self.keyvault.id,
        )

        # RBAC - Databricks - Key Vault Reader
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#key-vault-reader
        self._set_rbac(
            name="rbac-neptune-keyvault",
            role_id="00482a5a-887f-4fb3-b363-3b7fe8e74483",
            principal_id=self.sp.object_id,
            scope=self.keyvault.id,
        )

    def set_storage(self):

        k = f"{self.org}stg{self.service}"
        self.storage_account = azure.storage.Account(
            k,
            name=f"{k}{self.env}",
            resource_group_name=self.rg.name,
            location=self.rg.location,
            account_tier="Standard",
            account_replication_type="LRS",
            is_hns_enabled=True,  # required for Datalake Gen 2
        )

        self.container_landing = azure.storage.Container(
            "landing",
            name="landing",
            storage_account_name=self.storage_account.name,
            container_access_type="private"
        )
        pulumi.export("container-landing-id", self.container_landing.id)
        pulumi.export("container-landing-name", self.container_landing.name)
        pulumi.export("container-landing-account-name", self.container_landing.storage_account_name)

        self.container_metastore = azure.storage.Container(
            "metastore",
            name="metastore",
            storage_account_name=self.storage_account.name,
            container_access_type="private"
        )
        pulumi.export("container-metastore-id", self.container_metastore.id)
        pulumi.export("container-metastore-name", self.container_metastore.name)
        pulumi.export("container-metastore-account-name", self.container_metastore.storage_account_name)

        # RBAC - Databricks App - Storage Blob Data Contributor
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
        self._set_rbac(
            name="rbac-neptune-storage",
            role_id="ba92f5b4-2d11-453d-a403-e96b0029c9fe",
            principal_id=self.sp.object_id,
            scope=self.storage_account.id,
        )

        # Save secrets
        secret = self._set_secret("lakehouse-sa-conn-str",
                                  self.storage_account.primary_connection_string.apply(lambda x: x))

    def set_databricks_workspace(self):
        k = f"{self.org}-dbksws-{self.service}"
        self.workspace = azure_native.databricks.Workspace(
            k,
            workspace_name=f"{k}-{self.env}",
            location=self.rg.location,
            managed_resource_group_id=f"/subscriptions/{self.subscription_id}/resourceGroups/{self.org}-rg-dbksws-{self.service}-{self.env}",
            resource_group_name=self.rg.name,
        )
        pulumi.export("dbks-ws-name", self.workspace.name)
        pulumi.export("dbks-ws-host", self.workspace.workspace_url)
        pulumi.export("dbks-ws-id", self.workspace.workspace_id)
        secret = self._set_secret("databricks-host", self.workspace.workspace_url)

    def set_databricks_connector(self):

        # Connector
        k = f"{self.org}-dbksac-{self.service}"
        connector = azure.databricks.AccessConnector(
            k,
            name=f"{k}-{self.env}",
            resource_group_name=self.rg.name,
            location=self.rg.location,
            identity=azure.databricks.AccessConnectorIdentityArgs(
                type="SystemAssigned",
            ),
        )
        pulumi.export("databricks-access-connector-id", connector.id)

        # RBAC - Workspace Connector - Storage Account Contributor
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
        self._set_rbac(
            name="rbac-databricks-connector-storage",
            role_id="ba92f5b4-2d11-453d-a403-e96b0029c9fe",
            principal_id=connector.identity.principal_id,
            scope=self.storage_account.id,
        )

    def _set_rbac(self, name, role_id, principal_id, scope, principal_type="ServicePrincipal"):
        name = name + f"-{role_id}-{self.env}"

        return azure_native.authorization.RoleAssignment(
            name,
            principal_id=principal_id,
            principal_type=principal_type,
            role_assignment_name=str(uuid.uuid5(uuid.UUID(role_id), name=name)),  # random but static user-provided UUID
            # role_assignment_name=str(uuid.uuid4()),  # random but static user-provided UUID
            role_definition_id=f"/subscriptions/{self.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
            scope=scope,
            opts=pulumi.ResourceOptions(
                delete_before_replace=True
            ),
        )

    def _set_secret(self, key, value):
        return azure_native.keyvault.Secret(
            key,
            secret_name=key,
            properties=azure_native.keyvault.SecretPropertiesArgs(
                value=value,
            ),
            resource_group_name=self.rg.name,
            vault_name=self.keyvault.name,
        )


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
