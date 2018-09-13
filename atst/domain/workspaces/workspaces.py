from atst.domain.roles import Roles
from atst.domain.authz import Authorization
from atst.models.permissions import Permissions
from atst.domain.users import Users
from atst.domain.workspace_users import WorkspaceUsers

from .query import WorkspaceQuery
from .scopes import ScopedWorkspace


class Workspaces(object):
    @classmethod
    def create(cls, request, name=None):
        name = name or request.id
        workspace = WorkspaceQuery.create(request=request, name=name)
        Workspaces._create_workspace_role(request.creator, workspace, "owner")
        WorkspaceQuery.add_and_commit(workspace)
        return workspace

    @classmethod
    def get(cls, user, workspace_id):
        workspace = WorkspaceQuery.get(workspace_id)
        Authorization.check_workspace_permission(
            user, workspace, Permissions.VIEW_WORKSPACE, "get workspace"
        )

        return ScopedWorkspace(user, workspace)

    @classmethod
    def get_for_update(cls, user, workspace_id):
        workspace = WorkspaceQuery.get(workspace_id)
        Authorization.check_workspace_permission(
            user, workspace, Permissions.ADD_APPLICATION_IN_WORKSPACE, "add project"
        )

        return workspace

    @classmethod
    def get_by_request(cls, request):
        return WorkspaceQuery.get_by_request(request)

    @classmethod
    def get_with_members(cls, user, workspace_id):
        workspace = WorkspaceQuery.get(workspace_id)
        Authorization.check_workspace_permission(
            user,
            workspace,
            Permissions.VIEW_WORKSPACE_MEMBERS,
            "view workspace members",
        )

        return workspace

    @classmethod
    def for_user(cls, user):
        if Authorization.has_atat_permission(user, Permissions.VIEW_WORKSPACE):
            workspaces = WorkspaceQuery.get_all()
        else:
            workspaces = WorkspaceQuery.get_for_user(user)
        return workspaces

    @classmethod
    def create_member(cls, user, workspace, data):
        Authorization.check_workspace_permission(
            user,
            workspace,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "create workspace member",
        )

        new_user = Users.get_or_create_by_dod_id(
            data["dod_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
        )
        return Workspaces.add_member(workspace, new_user, data["workspace_role"])

    @classmethod
    def add_member(cls, workspace, member, role_name):
        workspace_user = WorkspaceUsers.add(member, workspace.id, role_name)
        return workspace_user

    @classmethod
    def update_member(cls, user, workspace, member, role_name):
        Authorization.check_workspace_permission(
            user,
            workspace,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "edit workspace member",
        )

        return WorkspaceUsers.update_role(member, workspace.id, role_name)

    @classmethod
    def _create_workspace_role(cls, user, workspace, role_name):
        role = Roles.get(role_name)
        workspace_role = WorkspaceQuery.create_workspace_role(user, role, workspace)
        WorkspaceQuery.add_and_commit(workspace_role)
        return workspace_role
