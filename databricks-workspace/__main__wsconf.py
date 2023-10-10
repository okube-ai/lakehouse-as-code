import os
import yaml
import pulumi
import pulumi_databricks as databricks
from pulumi import Output


# --------------------------------------------------------------------------- #
# Data Classes                                                                #
# --------------------------------------------------------------------------- #

from laktory.models.base import BaseModel


class Grant(BaseModel):
    principal: str
    privileges: list[str] = None


class Catalog(BaseModel):
    name: str
    isolation_mode: str = "OPEN"
    storage_root: str = None
    grants: list[Grant] = []


class Database(BaseModel):
    name: str
    catalog_name: str = None
    grants: list[Grant] = []


# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #

class Service:

    def __init__(self):
        self.pulumi_config = pulumi.Config()
        self.env = pulumi.get_stack()
        self.infra_stack = pulumi.StackReference(f"taigamotors/dna-lakehouse-azure/{self.env}")

        # Providers
        self.databricks_provider = databricks.Provider(
            "provider-token-workspace",
            host=self.infra_stack.get_output("dbks-ws-host"),
            token=self.infra_stack.get_output("dbks-ws-neptune-token"),
        )

        # Resources
        self.catalogs = {}

    def run(self):
        self.set_init_scripts()
        self.set_clusters()
        self.set_warehouses()
        self.set_permissions()

    # ----------------------------------------------------------------------- #
    # Properties                                                              #
    # ----------------------------------------------------------------------- #

    @property
    def cluster_env_vars(self):
        return {
            "AZURE_DEVOPS_TOKEN": "{{secrets/azure/devops-token}}",
            "AZURE_KEYVAULT_URL": "{{secrets/azure/keyvault-url}}",
            "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
            "AZURE_CLIENT_ID": "{{secrets/azure/client-id}}",
            "AZURE_CLIENT_SECRET": "{{secrets/azure/client-secret}}",
        }

    @property
    def laktory(self):
        return databricks.ClusterLibraryArgs(
            pypi=databricks.ClusterLibraryPypiArgs(
                package="laktory"
            )
        )

    @property
    def pip_config(self):
        return databricks.ClusterInitScriptArgs(
            volumes=databricks.ClusterInitScriptVolumesArgs(
                destination="/Volumes/libraries/default/init_scripts/update_pip_config.sh"
            )
        )

    @property
    def install_ionclient(self):
        return databricks.ClusterInitScriptArgs(
            volumes=databricks.ClusterInitScriptVolumesArgs(
                destination="/Volumes/libraries/default/init_scripts/install_ionclient.sh"
            )
        )

    @property
    def ion_jar(self):
        return databricks.ClusterLibraryArgs(
            jar="/Volumes/libraries/default/jar/infor-compass-jdbc.jar"
        )

    # ----------------------------------------------------------------------- #
    # Resources                                                               #
    # ----------------------------------------------------------------------- #

    def set_init_scripts(self):
        """
        Init scripts are installed in Unity Catalog Volumes in the unity
        catalog stack. However, no isolation clusters can't connect to UC and
        require a different location.
        """

        root_dir = "../dna-lakehouse-unity-catalog/init_scripts"

        for filename in os.listdir(root_dir):
            key = filename.split(".")[0].replace("_", "-")
            filepath = os.path.join(root_dir, filename)

            script = databricks.WorkspaceFile(
                f"init-script-{key}",
                path=f"/init_scripts/{filename}",
                source=filepath,
                opts=pulumi.ResourceOptions(provider=self.databricks_provider),
            )

            self._set_permissions(key, workspace_file_path=script.path)

    def set_clusters(self):

        k = "default"
        cluster = databricks.Cluster(
            f"cluster-{k}",
            cluster_name=k,
            spark_version="14.0.x-scala2.12",
            data_security_mode="USER_ISOLATION",
            node_type_id="Standard_DS3_v2",
            autoscale=databricks.ClusterAutoscaleArgs(
                min_workers=1,
                max_workers=4,
            ),
            autotermination_minutes=30,
            is_pinned=True,
            spark_env_vars=self.cluster_env_vars,
            libraries=[self.laktory],
            init_scripts=[
                self.pip_config,
            ],
            opts=pulumi.ResourceOptions(provider=self.databricks_provider),
        )
        self._set_permissions(k, cluster_id=cluster.id)

        k = "ion"
        cluster = databricks.Cluster(
            f"cluster-{k}",
            cluster_name=k,
            spark_version="14.0.x-scala2.12",
            data_security_mode="USER_ISOLATION",
            node_type_id="Standard_DS3_v2",
            autoscale=databricks.ClusterAutoscaleArgs(
                min_workers=1,
                max_workers=4,
            ),
            autotermination_minutes=30,
            is_pinned=True,
            spark_env_vars=self.cluster_env_vars,
            libraries=[
                self.ion_jar,
                self.laktory,
            ],
            init_scripts=[
                self.pip_config,
                self.install_ionclient,
            ],
            opts=pulumi.ResourceOptions(provider=self.databricks_provider),
        )
        self._set_permissions(k, cluster_id=cluster.id)

    def set_warehouses(self):
        k = "default"
        warehouse = databricks.SqlEndpoint(
            f"warehouse-{k}",
            name=k,
            cluster_size="2X-Small",
            auto_stop_mins=10,
            channel=databricks.SqlEndpointChannelArgs(name="CHANNEL_NAME_PREVIEW"),
            enable_photon=False,
            enable_serverless_compute=True,
            min_num_clusters=1,
            max_num_clusters=2,
            opts=pulumi.ResourceOptions(provider=self.databricks_provider),
        )
        pulumi.export(f"warehouse-{k}-id", warehouse.id)
        self._set_permissions(k, sql_endpoint_id=warehouse.id)

    def _set_permissions(self, k, cluster_id=None, sql_endpoint_id=None, workspace_file_path=None):
        access_controls = []

        if cluster_id is not None:
            k = f"cluster-{k}"
            access_controls = [
                databricks.PermissionsAccessControlArgs(
                    permission_level="CAN_RESTART",
                    group_name="role-analysts"
                ),
                databricks.PermissionsAccessControlArgs(
                    permission_level="CAN_RESTART",
                    group_name="role-engineers"
                ),
            ]

        elif sql_endpoint_id is not None:
            k = f"warehouse-{k}"
            access_controls = [
                databricks.PermissionsAccessControlArgs(
                    permission_level="CAN_USE",
                    group_name="account users"
                ),
            ]

        elif workspace_file_path is not None:
            k = f"workspace-file-{k}"
            access_controls = [
                databricks.PermissionsAccessControlArgs(
                    permission_level="CAN_READ",
                    group_name="account users"
                ),
            ]

        databricks.Permissions(
            f"permissions-{k}",
            cluster_id=cluster_id,
            sql_endpoint_id=sql_endpoint_id,
            access_controls=access_controls,
            workspace_file_path=workspace_file_path,
            opts=pulumi.ResourceOptions(provider=self.databricks_provider),
        )

    def set_permissions(self):

        # TODO: Remove when mount is disabled
        # Permissions
        privileges = ["SELECT"]
        principal = "role-engineers"

        this = databricks.SqlPermissions(
            "permissions-any-file",
            privilege_assignments=[
                databricks.SqlPermissionsPrivilegeAssignmentArgs(principal=principal, privileges=privileges),
            ],
            any_file=True,
            opts=pulumi.ResourceOptions(
                provider=self.databricks_provider,
            )
        )

        # name = self.rnp.get_name(ResourceTypes.DBKS_SQL_PERMISSIONS, principal + "-anonymous-function")
        # this = databricks.SqlPermissions(
        #     name,
        #     privilege_assignments=[
        #         databricks.SqlPermissionsPrivilegeAssignmentArgs(principal=principal, privileges=privileges),
        #     ],
        #     anonymous_function=True,
        #     opts=pulumi.ResourceOptions(
        #         provider=self.databricks_provider,
        #     )
        # )

# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
