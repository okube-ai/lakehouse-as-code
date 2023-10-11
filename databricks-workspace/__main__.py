"""A Python Pulumi program"""

import pulumi

"""
        self.databricks_workspace_provider = databricks.Provider(
            "azure-workspace-provider",
            host=self.workspace.workspace_url,
            azure_client_id=self.pulumi_config.get("neptune_client_id"),
            azure_client_secret=self.pulumi_config.get_secret("neptune_client_secret"),
            azure_tenant_id=self.tenant_id,
        )
"""

"""


    def set_databricks_secrets(self):

        app = self._set_secrets_scope("azure")

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
            string_value=self.app.application_id,
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

        databricks.Secret(
            "dbks-secret-client-secret",
            key="client-secret",
            string_value=self.app_secret.value,
            scope=app.id,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )

    # TODO: Move to workspace configuration
    def _set_secrets_scope(self, name):
        # TODO: Create a Laktory component
        app = databricks.SecretScope(
            f"dbks-secret-scope-{name}",
            name=name,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )
        databricks.SecretAcl(
            f"dbks-secret-scope-acl-{name}",
            permission="READ",
            principal="role-store-admins",
            scope=app.name,
            opts=pulumi.ResourceOptions(provider=self.databricks_workspace_provider),
        )
        return app

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