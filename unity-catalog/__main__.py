import os
import yaml

import pulumi
import pulumi_databricks as databricks
import pulumi_azure_native as azure_native
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
        self.infra_stacks = {
            "dev": pulumi.StackReference(f"okube/azure-infra/dev"),
            # "prod": pulumi.StackReference(f"okube/azure-infra/prod"),
        }
        self.metastore_name = "metastore-lakehouse"

        # Providers
        self.workspace_provider = None

        # Resources
        self.groups = None
        self.user_resources = None
        self.metastore = None
        self.metastore_grants = None
        self.workspace_groups = None
        self.catalogs = {}

    def run(self, deploy_catalog=True):
        pass
        self.set_users_and_groups()
        self.set_metastore()
        self.set_data_access()

        # There is usually a delay of a few seconds before the grants in Databricks are active which
        # cause the deployment of the catalog to fail. If you encounter this type of issue, deploy the
        # resources above this comment first and do a second deployment for the rest of them.
        if deploy_catalog:
            self.set_catalogs()
            self.set_init_scripts()

    # ----------------------------------------------------------------------- #
    # Users                                                                   #
    # ----------------------------------------------------------------------- #

    def set_users_and_groups(self):

        # ------------------------------------------------------------------- #
        # Groups                                                              #
        # ------------------------------------------------------------------- #

        with open("groups.yaml") as fp:

            self.groups = {}
            for d in yaml.safe_load(fp):
                g = models.Group.model_validate(d)
                g.deploy()
                self.groups[g.display_name] = g

        # ------------------------------------------------------------------- #
        # Users                                                               #
        # ------------------------------------------------------------------- #

        with open("./users.yaml") as fp:
            users = [models.User.model_validate(u) for u in yaml.safe_load(fp)]

        self.user_resources = []
        for u in users:
            if u.display_name is None:
                u.display_name = u.user_name
            u.deploy(
                groups=list(self.groups.values()),
            )
            self.user_resources += [u.resources]

        # ------------------------------------------------------------------- #
        # Service Principals                                                  #
        # ------------------------------------------------------------------- #

        with open("./serviceprincipals.yaml") as fp:
            service_principals = [models.ServicePrincipal.model_validate(u) for u in yaml.safe_load(fp)]

        for sp in service_principals:

            if sp.display_name == "neptune":
                sp.application_id = self.infra_stacks["dev"].get_output("neptune-client-id").apply(lambda x: f"{x}")

            sp.deploy(groups=list(self.groups.values()))
            self.user_resources += [sp.resources]

    # ----------------------------------------------------------------------- #
    # Metastore                                                               #
    # ----------------------------------------------------------------------- #

    def set_metastore(self):

        container_name = self.infra_stacks["dev"].get_output("container-metastore-name")
        storage_account_name = self.infra_stacks["dev"].get_output("container-metastore-account-name")

        self.metastore = databricks.Metastore(
            self.metastore_name,
            name=f"metastore-lakehouse",
            cloud="azure",
            storage_root=pulumi.Output.all(container_name, storage_account_name).apply(lambda x: f"abfss://{x[0]}@{x[1]}.dfs.core.windows.net/"),
            region="eastus",
            force_destroy=True,
            owner="role-metastore-admins",
            opts=pulumi.ResourceOptions(depends_on=self.user_resources)
        )

        # Explicit dependency is required to ensure role-metastore-admins is the owner/admin of the metastore
        self.workspace_provider = databricks.Provider(
            "provider-workspace-neptune",
            host=self.infra_stacks["dev"].get_output("dbks-ws-host"),
            azure_client_id=self.infra_stacks["dev"].get_output("neptune-client-id"),
            azure_client_secret=self.infra_stacks["dev"].get_output("neptune-client-secret"),
            azure_tenant_id="ab09b389-116f-42c5-9826-3505f22a906b",
            opts=pulumi.ResourceOptions(
                depends_on=[self.metastore],
            )
        )

        # Workspaces assignment
        workspace_assignments = []
        for env, infra_stack in self.infra_stacks.items():
            k = f"{self.metastore_name}-{self.org}-dbwks-{self.service}-{env}"
            workspace_assignments += [databricks.MetastoreAssignment(
                k,
                metastore_id=self.metastore.id,
                workspace_id=infra_stack.get_output('dbks-ws-id'),
            )]

        # Assign groups to workspaces
        self.workspace_groups = []
        for env, infra_stack in self.infra_stacks.items():
            for group_name, group in self.groups.items():
                k = f"permission-workspace-{env}-group-{group_name}"

                permission = "USER"
                if "workspaceadmin" in group_name:
                    permission = "ADMIN"

                self.workspace_groups += [databricks.MwsPermissionAssignment(
                    k,
                    workspace_id=infra_stack.get_output('dbks-ws-id'),
                    principal_id=group.resources.group.id,
                    permissions=[permission]
                )]

        self.metastore_grants = databricks.Grants(
            f"grants-{self.metastore_name}",
            metastore=self.metastore.id,
            grants=[
                databricks.GrantsGrantArgs(
                    principal="role-metastore-admins", privileges=[
                        "CREATE_CATALOG",
                        "CREATE_EXTERNAL_LOCATION",
                    ]
                ),
            ],
            opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
                depends_on=workspace_assignments + self.workspace_groups,
            )
        )

    def set_data_access(self):

        for env, infra_stack in self.infra_stacks.items():

            # Metastore Data Access
            # This creates a Storage Credentials and an External location if
            # the `is_default` is selected. Otherwise, external location needs
            # to be set manually.
            # Unfortunately, Pulumi, does not seem to delete / clean up
            # resources
            k = f"metastore-lakehouse-dataaccess-{env}"
            metastore_access = databricks.MetastoreDataAccess(
                k,
                name=k,
                metastore_id=self.metastore.id,
                azure_managed_identity=databricks.MetastoreDataAccessAzureManagedIdentityArgs(
                    access_connector_id=infra_stack.get_output("databricks-access-connector-id"),
                ),
                force_destroy=True,
                is_default=env=="dev",
                opts=pulumi.ResourceOptions(
                    provider=self.workspace_provider,
                    depends_on=[self.metastore_grants] + self.workspace_groups,
                )
            )

            if env != "dev":
                container_name = infra_stack.get_output("container-metastore-name")
                storage_account_name = infra_stack.get_output("container-metastore-account-name")

                location = databricks.ExternalLocation(
                    f"dbks-external-location-{env}",
                    name=f"dbks-external-location-{env}",
                    credential_name=metastore_access.name,
                    force_destroy=True,
                    url=pulumi.Output.all(container_name, storage_account_name).apply(
                        lambda x: f"abfss://{x[0]}@{x[1]}.dfs.core.windows.net/"),
                    opts=pulumi.ResourceOptions(
                        provider=self.workspace_provider,
                        depends_on=[self.metastore_grants] + self.workspace_groups,
                    ),
                )

    # ----------------------------------------------------------------------- #
    # Catalogs                                                                #
    # ----------------------------------------------------------------------- #

    def set_catalogs(self):

        with open(f"./catalogs.yaml") as fp:
            catalogs = [models.Catalog.model_validate(u) for u in yaml.safe_load(fp)]

        for catalog in catalogs:

            if catalog.name == "prod" and "prod" in self.infra_stacks:
                container_name = self.infra_stacks["prod"].get_output("container-metastore-name")
                storage_account_name = self.infra_stacks["prod"].get_output("container-metastore-account-name")
                catalog.storage_root = pulumi.Output.all(container_name, storage_account_name).apply(
                    lambda x: f"abfss://{x[0]}@{x[1]}.dfs.core.windows.net/")

            catalog.deploy(opts=pulumi.ResourceOptions(
                provider=self.workspace_provider,
                depends_on=[self.metastore_grants]
            ))
            self.catalogs[catalog.name] = catalog

    # ----------------------------------------------------------------------- #
    # Volume Files                                                            #
    # ----------------------------------------------------------------------- #

    def set_init_scripts(self):

        root_dir = "./init_scripts"

        resource_group_name = self.infra_stacks["dev"].get_output("resource-group-name")
        container_name = self.infra_stacks["dev"].get_output("container-metastore-name")
        storage_account_name = self.infra_stacks["dev"].get_output("container-metastore-account-name")
        volume = self.catalogs["libraries"].schemas[0].volumes[0].resources.volume

        for filename in os.listdir(root_dir):
            key = filename.split(".")[0].replace("_", "-")
            filepath = os.path.join(root_dir, filename)

            blob_name = pulumi.Output.all(volume.storage_location, filename).apply(lambda args:
                f"{args[0].split('windows.net')[-1]}/{args[1]}"
            )

            blob = azure_native.storage.Blob(
                f"tg-blob-{key}",
                account_name=storage_account_name,
                container_name=container_name,
                blob_name=blob_name,
                source=pulumi.FileAsset(filepath),
                resource_group_name=resource_group_name,
                opts=pulumi.ResourceOptions(
                    depends_on=[volume],
                ),

            )

            # TODO: Directly write BDFS file when supported
            # script = databricks.DbfsFile(
            #     f"init-script-{key}-2",
            #     # path=f"/init_scripts/{filename}",
            #     path=f"dbfs:/Volumes/libraries/default/init_scripts/{filename}",
            #     source=filepath,
            #     opts=pulumi.ResourceOptions(provider=self.workspace_provider),
            # )


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run(deploy_catalog=True)
