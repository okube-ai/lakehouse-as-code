import uuid

import pulumi
import pulumi_gcp as gcp
import pulumi_databricks as databricks


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #

class Service:
    def __init__(self):
        self.org = "o3"
        self.service = "lakehouse"
        self.pulumi_config = pulumi.Config()
        self.databricks_config = pulumi.Config("databricks")
        self.env = pulumi.get_stack()

        # Providers
        self.databricks_workspace_provider = None

        # Resources
        self.app = None
        self.app_secret = None
        self.sp = None
        self.me = None
        self.rg = None
        self.keyvault = None
        self.bucket_landing = None
        self.bucket_metastore = None
        self.workspace = None

    def run(self):
        # Service principals
        # self.set_service_principal()
        #
        # Key Vault
        # self.set_keyvault()

        # Storage Account
        self.set_storage()

        # Databricks workspace
        self.set_workspace()
        #
        # # Databricks connector
        # self.set_databricks_connector()

    def set_storage(self):
        k = f"{self.org}-bucket-{self.service}-landing"
        self.bucket_landing = gcp.storage.Bucket(
            k,
            name=k,
            location="US",
            uniform_bucket_level_access=True,
            # force_destroy=True,
        )
        pulumi.export("bucket-landing-id", self.bucket_landing.id)
        pulumi.export("bucket-landing-name", self.bucket_landing.name)

        k = f"{self.org}-bucket-{self.service}-metastore"
        self.bucket_metastore = gcp.storage.Bucket(
            k,
            name=k,
            location="US",
            uniform_bucket_level_access=True,
            # force_destroy=True,
        )
        pulumi.export("bucket-metastore-id", self.bucket_metastore.id)
        pulumi.export("bucket-metastore-name", self.bucket_metastore.name)

        # TODO: Set RBAC on bucket
        # # RBAC - Databricks App - Storage Blob Data Contributor
        # # https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
        # self._set_rbac(
        #     name="rbac-neptune-storage",
        #     role_id="ba92f5b4-2d11-453d-a403-e96b0029c9fe",
        #     principal_id=self.sp.object_id,
        #     scope=self.storage_account.id,
        # )
        #
        # # Save secrets
        # secret = self._set_secret(
        #     "lakehouse-sa-conn-str",
        #     self.storage_account.primary_connection_string.apply(lambda x: x),
        # )

    # ----------------------------------------------------------------------- #
    # Workspace                                                               #
    # ----------------------------------------------------------------------- #

    def set_workspace(self):

        k = f"{self.org}-dbksws-{self.service}"
        # self.workspace = databricks.MwsWorkspaces(
        #     k,
        #     account_id=self.databricks_config.get("account_id"),
        #     cloud="gcp",
        #     # aws_region=aws.get_region().id,
        #     workspace_name=k,
        #     location="US",
        #     # credentials_id=self.credentials.credentials_id,
        #     # storage_configuration_id=self.bms.root.conf.storage_configuration_id,
        #     # network_id=self.network.network_id,
        #     opts=pulumi.ResourceOptions(delete_before_replace=True)
        # )
        # pulumi.export(f"dbks-ws-host", self.workspace.workspace_url)
        # pulumi.export(f"dbks-ws-name", self.workspace.workspace_name)
        #
        # self.databricks_workspace_provider = databricks.Provider(
        #     "workspace",
        #     host=self.workspace.workspace_url,
        #     username=self.databricks_config.get("username"),
        #     password=self.databricks_config.get("password"),
        # )
        #
        # # Token
        # name = self.rnp.get_name(ResourceTypes.DBKS_WORKSPACE_PAT, "lakehouse")
        # self.workspace_pat = databricks.Token(
        #     name,
        #     comment="pulumi-ci-cd",
        #     lifetime_seconds=3600*24*364,
        #     opts=pulumi.ResourceOptions(
        #         provider=self.databricks_workspace_provider,
        #         depends_on=[self.workspace],
        #     ),
        # )
        # pulumi.export(f"dbks-ws-token", self.workspace_pat.token_value)


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
