import json
import pulumi
from dataclasses import dataclass
from dataclasses import field

import pulumi_databricks as databricks


# --------------------------------------------------------------------------- #
# Data Classes                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class UsersGroup:
    display_name: str
    allow_cluster_create: bool = False
    workspace_access: bool = True


@dataclass
class User:
    user_name: str
    display_name: str = None
    first_name: str = None
    last_name: str = None
    account_admin: bool = False
    groups: list[str] = field(default_factory=lambda: [])


@dataclass
class ServicePrincipal:
    display_name: str
    account_admin: bool = False
    application_id: str = None
    groups: list[str] = field(default_factory=lambda: [])

# --------------------------------------------------------------------------- #
# Service                                                                     #
# --------------------------------------------------------------------------- #


class Service:
    def __init__(self):
        self.pulumi_config = pulumi.Config()
        self.env = pulumi.get_stack()

        # Resources
        self.groups = None

    def run(self):
        self.set_users_and_groups()
        self.set_metastore()

    # ----------------------------------------------------------------------- #
    # Users                                                                   #
    # ----------------------------------------------------------------------- #

    def set_users_and_groups(self):

        groups = [
            UsersGroup("role-store-admins"),
            UsersGroup("role-consumers"),
            UsersGroup("role-engineers"),
            UsersGroup("role-analysts"),
        ]

        users = [
            User(
                "data.engineer@com.gmail",
                groups=[
                    "role-consumers",
                    "role-engineers",
                ]
            ),
        ]

        service_principals = [

            ServicePrincipal(
                "neptune-dev",
                application_id="9a64bd51-03f1-4925-a99b-de48797c78f0",
                groups=[
                    "role-store-admins",
                    "role-consumers",
                ]
            ),

        ]

        # ------------------------------------------------------------------- #
        # Groups                                                              #
        # ------------------------------------------------------------------- #

        self.groups = {}
        for g in groups:
            self.groups[g.display_name] = databricks.Group(
                g.display_name,
                display_name=g.display_name,
                allow_cluster_create=g.allow_cluster_create,
            )

        # ------------------------------------------------------------------- #
        # Users                                                               #
        # ------------------------------------------------------------------- #

        for u in users:
            # TODO: Review why deletion not working
            user = databricks.User(
                u.user_name,
                user_name=u.user_name,
                force=True,
                # account_admin=u.account_admin,
            )

            # Group Member
            for g in u.groups:
                databricks.GroupMember(
                    f"{u.user_name}-{g}",
                    group_id=self.groups[g].id,
                    member_id=user.id,
                )

        # ------------------------------------------------------------------- #
        # Service Principals                                                  #
        # ------------------------------------------------------------------- #

        for sp in service_principals:
            # TODO: Review why deletion not working
            _sp = databricks.ServicePrincipal(
                sp.display_name,
                display_name=sp.display_name,
                application_id=sp.application_id,
                # account_admin=sp.account_admin,
            )

            # Group Member
            for g in sp.groups:
                databricks.GroupMember(
                    f"{sp.display_name}-{g}",
                    group_id=self.groups[g].id,
                    member_id=_sp.id,
                )

    def set_metastore(self):

        metastore = databricks.Metastore(
            f"metastore-lakehouse",
            name=f"metastore-lakehouse",
            cloud="azure",
            storage_root="abfss://metastore@test.dfs.core.windows.net/",
            # storage_root="abfss://metastore@tgstglakehousedev.dfs.core.windows.net/",
            region="eastus",
            force_destroy=True,
        )

        # TODO: Set metatore-admins group as the admin of this metastore


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    service = Service()
    service.run()
