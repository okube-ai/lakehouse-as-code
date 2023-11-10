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
        # self.app = None
        # self.app_secret = None
        self.service_account = None
        self.sp = None
        self.me = None
        self.rg = None
        self.keyvault = None
        self.bucket_landing = None
        self.bucket_metastore = None
        self.workspace = None

    def run(self):

        # https://docs.gcp.databricks.com/dev-tools/terraform/gcp-workspace.html

        # Service account
        self.set_service_account()
        #
        # Key Vault
        # self.set_keyvault()

        # Storage Account
        self.set_storage()

        # Databricks workspace
        # self.set_workspace()
        #
        # # Databricks connector
        # self.set_databricks_connector()

    # ----------------------------------------------------------------------- #
    # Service Account                                                         #
    # ----------------------------------------------------------------------- #

    def set_service_account(self):
        self.service_account = gcp.serviceaccount.Account(
            "neptune",
            account_id="neptune",
            display_name="neptune",
        )
        # pulumi.export("tenant-id", self.tenant_id)
        pulumi.export("neptune-email", self.service_account.email)
        # pulumi.export("neptune-client-id", self.app.application_id)
        #
        #  gcp.iam.Policy(
        #     "aad-sp-neptune",
        #     application_id=self.app.application_id,
        # )
        #
        # self.app_secret = azuread.ApplicationPassword(
        #     "aad-app-secret-neptune",
        #     application_object_id=self.app.object_id,
        #     end_date_relative=f"{24*30*6}h",
        # )
        # pulumi.export("neptune-client-secret", self.app_secret.value)

    # ----------------------------------------------------------------------- #
    # Storage                                                                 #
    # ----------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
