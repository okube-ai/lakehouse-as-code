import json
import pulumi
from pulumi import Output
import pulumi_azure as azure
import pulumi_azure_native as azure_native
import pulumi_databricks as databricks


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #


class Service:

    def __init__(self):
        self.pulumi_config = pulumi.Config()
        self.azure_config = azure_native.authorization.get_client_config()
        self.env = self.pulumi_config.get("env")
        self.tenant_id = self.azure_config.tenant_id
        self.subscription_id = self.azure_config.subscription_id

        # Providers
        self.databricks_workspace_provider = None
        self.databricks_account_provider = None

        # Resources
        self.service = "lakehouse"
        self.storage_account = None
        self.container_landing = None
        self.container_metastore = None
        self.rg = None
        self.keyvault = None
        self.sp = None

        # Stacks
        self.dev_stack = None
        if self.env == "prod":
            self.dev_stack = pulumi.StackReference(
                f"taigamotors/dna-lakehouse-infra/dev"
            )

    def run(self):

        # Resources Group
        self.set_resource_group()

        # Key Vault
        self.set_keyvault()

        # Landing Storage
        self.set_storage()

        # Set account provider
        self.set_databricks_account_provider()

        # Set users
        self.set_databricks_users()

        # Databricks workspace
        self.set_databricks_workspace()

        # Databricks metastore
        self.set_databricks_metastore()

        # Databricks token
        self.set_databricks_token()

        # Databricks mounts
        self.set_databricks_secrets()

        # Databricks mounts
        self.set_databricks_mount()

    def set_resource_group(self):
        self.rg = azure_native.resources.ResourceGroup(
            f"tg-rg-{self.service}",
            location="canadacentral",
            resource_group_name=f"tg-rg-{self.service}-{self.env}",
        )

    def set_keyvault(self):

        self.keyvault = azure_native.keyvault.Vault(
            f"tg-kv-{self.service}",
            vault_name=f"tg-kv-{self.service}-{self.env}",
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
            ("ion-api-client-id", self.pulumi_config.get_secret("ion_api_client_id")),
            (
                "ion-api-client-secret",
                self.pulumi_config.get_secret("ion_api_client_secret"),
            ),
            ("ion-api-username", self.pulumi_config.get_secret("ion_api_username")),
            ("ion-api-password", self.pulumi_config.get_secret("ion_api_password")),
            (
                "salesforce-username",
                self.pulumi_config.get_secret("salesforce_username"),
            ),
            (
                "salesforce-password",
                self.pulumi_config.get_secret("salesforce_password"),
            ),
            ("salesforce-token", self.pulumi_config.get_secret("salesforce_token")),
            ("azure-devops-token", self.pulumi_config.get_secret("azure_devops_token")),
        ]:
            self._set_secret(key, value)

        # RBAC - Olivier - Key Vault Administrator
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#key-vault-administrator
        if self.env == "dev":
            name = "00482a5a-887f-4fb3-b363-3b7fe8e74483"
        elif self.env == "prod":
            name = "62347e66-6ade-4cac-a3bf-c506fa291f56"
        else:
            raise ValueError()
        role = azure_native.authorization.RoleAssignment(
            "rbac-olivier-soucy-keyvault",
            principal_id="218b4c39-dd56-4931-a567-3f1865e16ded",
            principal_type="User",
            role_assignment_name=name,  # random but static user-provided UUID
            role_definition_id=f"/subscriptions/{self.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/00482a5a-887f-4fb3-b363-3b7fe8e74483",
            scope=self.keyvault.id,
        )

        # RBAC - Databricks - Key Vault Reader
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#key-vault-reader
        role_id = ""
        if self.env == "dev":
            name = "4633458b-17de-408a-b874-0445c86b69e6"
        elif self.env == "prod":
            name = "54f5a090-aa83-4700-a17b-7e51bbd14227"
        else:
            raise ValueError()
        role = azure_native.authorization.RoleAssignment(
            "rbac-databricks-keyvault",
            principal_id=self.pulumi_config.get("databricks_app_object_id"),
            principal_type="ServicePrincipal",
            role_assignment_name=name,  # random but static user-provided UUID
            role_definition_id=f"/subscriptions/{self.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/4633458b-17de-408a-b874-0445c86b69e6",
            scope=self.keyvault.id,
        )

    def set_storage(self):

        self.storage_account = azure.storage.Account(
            f"tgstg{self.service}",
            name=f"tgstg{self.service}{self.env}",
            resource_group_name=self.rg.name,
            location=self.rg.location,
            account_tier="Standard",
            account_replication_type="LRS",
            is_hns_enabled=True,  # required for Datalake Gen 2 and SFTP
            sftp_enabled=True,
        )

        self.container_landing = azure.storage.Container(
            "landing",
            name="landing",
            storage_account_name=self.storage_account.name,
            container_access_type="private",
        )

        self.container_metastore = azure.storage.Container(
            "metastore",
            name="metastore",
            storage_account_name=self.storage_account.name,
            container_access_type="private",
        )

        # RBAC - Databricks App - Storage Blob Data Contributor
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
        if self.env == "dev":
            name = "26652554-955c-4ccb-9975-9ba28c4f9dc6"
        elif self.env == "prod":
            name = "04a6e8b2-10ca-433c-8e1e-94f3701b2fce"
        else:
            raise ValueError()

        role = azure_native.authorization.RoleAssignment(
            "rbac-databricks-storage-contributor",
            principal_id=self.pulumi_config.get("databricks_app_object_id"),
            principal_type="ServicePrincipal",
            role_assignment_name=name,  # random but static user-provided UUID
            role_definition_id=f"/subscriptions/{self.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe",
            scope=self.storage_account.id,
        )

        # SFTP (local) user
        user = azure.storage.LocalUser(
            "iondesk",
            name="iondesk",
            storage_account_id=self.storage_account.id,
            ssh_password_enabled=True,
            home_directory="landing/",
            permission_scopes=[
                azure.storage.LocalUserPermissionScopeArgs(
                    permissions=azure.storage.LocalUserPermissionScopePermissionsArgs(
                        create=True,
                        delete=True,
                        list=True,
                        read=True,
                        write=True,
                    ),
                    service="blob",
                    resource_name=self.container_landing.name,
                )
            ],
        )

        # Save secrets
        secret = self._set_secret(
            "lakehouse-sa-conn-str",
            self.storage_account.primary_connection_string.apply(lambda x: x),
        )
        secret = self._set_secret(
            "iondesk-sftp-password", user.password.apply(lambda x: x)
        )

    def set_databricks_account_provider(self):
        self.databricks_account_provider = databricks.Provider(
            "azure-account-provider",
            host="https://accounts.azuredatabricks.net",
            account_id="c7de928e-0d28-40ab-bf79-bed6798bbf13",
            auth_type="azure-cli",
        )

    def set_databricks_users(self):

        # This is set at the account level and is not environment-specific.
        if self.env != "dev":
            return

        # Service principal
        self.sp = databricks.ServicePrincipal(
            "neptune",
            display_name="neptune",
            application_id="7cacd544-c947-41ab-946a-ed26a60d7500",
            allow_cluster_create=True,
            databricks_sql_access=True,
            workspace_access=True,
            opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
        )

        # Service principal role
        databricks.ServicePrincipalRole(
            f"{self.sp.display_name}-role-account-admin",
            role="account_admin",
            service_principal_id=self.sp.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
        )

        # Groups
        admins = databricks.Group(
            "metastore-admins",
            display_name="metastore-admins",
            allow_cluster_create=True,
            allow_instance_pool_create=True,
            opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
        )

        for user_name, user_id in {
            self.sp.display_name: self.sp.id,
            # "olivier.soucy": "olivier.soucy@taigamotors.ca", # TODO
            # "gabriel.bernadchez": "gabriel.bernadchez@taigamotors.ca", # TODO
        }.items():
            databricks.GroupMember(
                f"{user_name}-{admins.display_name}",
                group_id=admins.id,
                member_id=user_id,
                opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
            )

    def set_databricks_workspace(self):
        self.workspace = azure_native.databricks.Workspace(
            f"tg-dbksws-{self.service}",
            workspace_name=f"tg-dbws-{self.service}-{self.env}",
            location=self.rg.location,
            managed_resource_group_id=f"/subscriptions/{self.subscription_id}/resourceGroups/tg-rg-dbksws-{self.service}-{self.env}",
            resource_group_name=self.rg.name,
        )
        pulumi.export("dbks-ws-host", self.workspace.workspace_url)
        secret = self._set_secret("databricks-host", self.workspace.workspace_url)

        self.databricks_workspace_provider = databricks.Provider(
            "azure-workspace-provider",
            host=self.workspace.workspace_url,
            azure_client_id=self.pulumi_config.get("databricks_app_client_id"),
            azure_client_secret=self.pulumi_config.get_secret(
                "databricks_app_client_secret"
            ),
        )

    def set_databricks_metastore(self):

        # Connector
        connector = azure.databricks.AccessConnector(
            f"tg-dbks-access-connector",
            name=f"tg-dbks-access-connector-{self.env}",
            resource_group_name=self.rg.name,
            location=self.rg.location,
            identity=azure.databricks.AccessConnectorIdentityArgs(
                type="SystemAssigned",
            ),
        )

        # RBAC - Workspace Connector - Storage Account Contributor
        # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
        if self.env == "dev":
            name = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
        elif self.env == "prod":
            name = "c7c2aa35-84e9-45ea-8dfd-cf7dc1595838"
        else:
            raise ValueError()

        role = azure_native.authorization.RoleAssignment(
            "rbac-dbks-access-connector-container",
            principal_id=connector.identity.principal_id,
            principal_type="ServicePrincipal",
            role_assignment_name=name,  # random but static user-provided UUID
            role_definition_id=f"/subscriptions/{self.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe",
            scope=self.storage_account.id,
        )

        if self.env == "dev":

            metastore = databricks.Metastore(
                f"metastore-lakehouse",
                name=f"metastore-lakehouse-{self.env}",
                cloud="azure",
                storage_root="abfss://metastore@tgstglakehousedev.dfs.core.windows.net/",
                region=self.rg.location,
                force_destroy=True,
                opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
            )
            # TODO: Export does not work. Had to be set manually
            # pulumi.export(f"metastore-id", metastore.metastore_id)
            pulumi.export(f"metastore-id", "9caeeaec-8ec4-4abd-ab63-42d4d19038a7")

        else:

            metastore = databricks.Metastore.get(
                f"metastore-lakehouse",
                id=self.dev_stack.get_output("metastore-id"),
                opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
            )

        if self.env == "dev":
            # TODO: Review if this is required in PROD
            name = "metastore-lakehouse-dataaccess"
            metastore_access = databricks.MetastoreDataAccess(
                name,
                name=name,
                metastore_id=metastore.id,
                azure_managed_identity=databricks.MetastoreDataAccessAzureManagedIdentityArgs(
                    access_connector_id=connector.id,
                ),
                is_default=self.env == "dev",
                opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
            )

        metastore_assignment = databricks.MetastoreAssignment(
            f"{metastore.name}-{self.workspace.name}",
            metastore_id=metastore.id,
            workspace_id=self.workspace.workspace_id,
            opts=pulumi.ResourceOptions(provider=self.databricks_account_provider),
        )
        #
        # # TODO: Add group(s) to workspace. This is currently not supported by Pulumi and must be done manually in the
        # # account console.

    def set_databricks_token(self):

        # Service Principal Token (will be used to manage workspace jobs and workflows)
        token = databricks.Token(
            "dbks-wokrkspace-token",
            comment="pulumi-ci-cd",
            lifetime_seconds=3600 * 24 * 364,
            opts=pulumi.ResourceOptions(
                provider=self.databricks_workspace_provider,
            ),
        )
        pulumi.export(f"dbks-ws-token", token.token_value)
        secret = self._set_secret("databricks-token", token.token_value)

    def set_databricks_secrets(self):

        app = databricks.SecretScope(
            "dbks-secret-scope-azure",
            name="azure",
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-keyvault-url",
            key="keyvault-url",
            string_value=self.keyvault.properties.vault_uri,
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-tenant-id",
            key="tenant-id",
            string_value=self.tenant_id,
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-client-id",
            key="client-id",
            string_value=self.pulumi_config.get("databricks_app_client_id"),
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-client-secret",
            key="client-secret",
            string_value=self.pulumi_config.get_secret("databricks_app_client_secret"),
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-azure-devops-token",
            key="devops-token",
            string_value=self.pulumi_config.get_secret("azure_devops_token"),
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        if self.env == "dev":

            app = databricks.SecretScope(
                "dbks-secret-scope-salesforce-prod",
                name="salesforce-prod",
                opts=pulumi.ResourceOptions(
                    provider=self.databricks_workspace_provider
                ),
            )

            databricks.Secret(
                "dbks-secret-salesforce-username-prod",
                key="username",
                string_value=self.pulumi_config.get_secret("salesforce_username_prod"),
                scope=app.id,
                opts=pulumi.ResourceOptions(
                    provider=self.databricks_workspace_provider
                ),
            )

            databricks.Secret(
                "dbks-secret-salesforce-password-prod",
                key="password",
                string_value=self.pulumi_config.get_secret("salesforce_password_prod"),
                scope=app.id,
                opts=pulumi.ResourceOptions(
                    provider=self.databricks_workspace_provider
                ),
            )

            databricks.Secret(
                "dbks-secret-salesforce-token-prod",
                key="token",
                string_value=self.pulumi_config.get_secret("salesforce_token_prod"),
                scope=app.id,
                opts=pulumi.ResourceOptions(
                    provider=self.databricks_workspace_provider
                ),
            )

    def set_databricks_mount(self):
        pass
        # mount = databricks.Mount(
        #     "landing-mount",
        #     name="landing/",
        #     uri=Output.all(container=self.container_landing.name, account=self.storage_account.name).apply(
        #         lambda args: f"abfss://{args['container']}@{args['account']}.dfs.core.windows.net/"),
        #     extra_configs={
        #         "fs.azure.account.auth.type": "OAuth",
        #         "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
        #         "fs.azure.account.oauth2.client.id": self.pulumi_config.get("databricks_app_client_id"),
        #         "fs.azure.account.oauth2.client.secret": self.pulumi_config.get_secret("databricks_app_client_secret"),
        #         "fs.azure.account.oauth2.client.endpoint": f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token",
        #     },
        #     opts=pulumi.ResourceOptions(
        #         provider=self.databricks_workspace_provider,
        #         # provider=self.databricks_account_provider,
        #         replace_on_changes=["*"],
        #         delete_before_replace=True,
        #     ),
        # )

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
