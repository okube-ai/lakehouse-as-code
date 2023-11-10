import uuid

import pulumi
import pulumi_gcp as gcp


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #

class Service:
    def __init__(self):
        self.org = "o3"
        self.service = "lakehouse"
        self.pulumi_config = pulumi.Config()
        # self.gcp_config = gcp.authorization.get_client_config()
        self.env = pulumi.get_stack()
        # self.tenant_id = self.azure_config.tenant_id
        # self.subscription_id = self.azure_config.subscription_id

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
        # self.set_service_principal()
        #
        # Key Vault
        # self.set_keyvault()

        # Storage Account
        self.set_storage()
        #
        # # Databricks workspace
        # self.set_databricks_workspace()
        #
        # # Databricks connector
        # self.set_databricks_connector()

    def set_storage(self):
        k = f"{self.org}-bucket-{self.service}-landing"

        static_site = gcp.storage.Bucket(
            k,
            name=k,
            location="US",
            uniform_bucket_level_access=True,
            # force_destroy=True,
            # cors=[gcp.storage.BucketCorArgs(
            #     max_age_seconds=3600,
            #     methods=[
            #         "GET",
            #         "HEAD",
            #         "PUT",
            #         "POST",
            #         "DELETE",
            #     ],
            #     origins=["http://image-store.com"],
            #     response_headers=["*"],
            # )],
            # location="EU",
            # website=gcp.storage.BucketWebsiteArgs(
            #     main_page_suffix="index.html",
            #     not_found_page="404.html",
            # )
        )

        # self.storage_account = gcp.storage.Account(
        #     k,
        #     name=f"{k}{self.env}",
        #     resource_group_name=self.rg.name,
        #     location=self.rg.location,
        #     account_tier="Standard",
        #     account_replication_type="LRS",
        #     is_hns_enabled=True,  # required for Datalake Gen 2
        # )
        #
        # self.container_landing = azure.storage.Container(
        #     "landing",
        #     name="landing",
        #     storage_account_name=self.storage_account.name,
        #     container_access_type="private",
        # )
        # pulumi.export("container-landing-id", self.container_landing.id)
        # pulumi.export("container-landing-name", self.container_landing.name)
        # pulumi.export(
        #     "container-landing-account-name",
        #     self.container_landing.storage_account_name,
        # )
        #
        # self.container_metastore = azure.storage.Container(
        #     "metastore",
        #     name="metastore",
        #     storage_account_name=self.storage_account.name,
        #     container_access_type="private",
        # )
        # pulumi.export("container-metastore-id", self.container_metastore.id)
        # pulumi.export("container-metastore-name", self.container_metastore.name)
        # pulumi.export(
        #     "container-metastore-account-name",
        #     self.container_metastore.storage_account_name,
        # )
        #
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



# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
