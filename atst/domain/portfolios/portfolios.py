from atst.domain.roles import Roles
from atst.domain.authz import Authorization
from atst.models.permissions import Permissions
from atst.domain.users import Users
from atst.domain.portfolio_roles import PortfolioRoles
from atst.domain.environments import Environments
from atst.models.portfolio_role import Status as PortfolioRoleStatus

from .query import PortfoliosQuery
from .scopes import ScopedPortfolio


class PortfolioError(Exception):
    pass


class Portfolios(object):
    @classmethod
    def create(cls, user, name):
        portfolio = PortfoliosQuery.create(name=name)
        Portfolios._create_portfolio_role(
            user, portfolio, "owner", status=PortfolioRoleStatus.ACTIVE
        )
        PortfoliosQuery.add_and_commit(portfolio)
        return portfolio

    @classmethod
    def create_from_request(cls, request, name=None):
        name = name or request.displayname
        portfolio = PortfoliosQuery.create(request=request, name=name)
        Portfolios._create_portfolio_role(
            request.creator, portfolio, "owner", status=PortfolioRoleStatus.ACTIVE
        )
        PortfoliosQuery.add_and_commit(portfolio)
        return portfolio

    @classmethod
    def get(cls, user, portfolio_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user, portfolio, Permissions.VIEW_PORTFOLIO, "get portfolio"
        )

        return ScopedPortfolio(user, portfolio)

    @classmethod
    def get_for_update_applications(cls, user, portfolio_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user, portfolio, Permissions.ADD_APPLICATION_IN_PORTFOLIO, "add application"
        )

        return portfolio

    @classmethod
    def get_for_update_information(cls, user, portfolio_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.EDIT_PORTFOLIO_INFORMATION,
            "update portfolio information",
        )

        return portfolio

    @classmethod
    def get_for_update_member(cls, user, portfolio_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "update a portfolio member",
        )

        return portfolio

    @classmethod
    def get_by_request(cls, request):
        return PortfoliosQuery.get_by_request(request)

    @classmethod
    def get_with_members(cls, user, portfolio_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.VIEW_PORTFOLIO_MEMBERS,
            "view portfolio members",
        )

        return portfolio

    @classmethod
    def for_user(cls, user):
        if Authorization.has_atat_permission(user, Permissions.VIEW_PORTFOLIO):
            portfolios = PortfoliosQuery.get_all()
        else:
            portfolios = PortfoliosQuery.get_for_user(user)
        return portfolios

    @classmethod
    def create_member(cls, user, portfolio, data):
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "create portfolio member",
        )

        new_user = Users.get_or_create_by_dod_id(
            data["dod_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            atat_role_name="default",
            provisional=True,
        )
        return Portfolios.add_member(portfolio, new_user, data["portfolio_role"])

    @classmethod
    def add_member(cls, portfolio, member, role_name):
        portfolio_role = PortfolioRoles.add(member, portfolio.id, role_name)
        return portfolio_role

    @classmethod
    def update_member(cls, user, portfolio, member, role_name):
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "edit portfolio member",
        )

        return PortfolioRoles.update_role(member, role_name)

    @classmethod
    def _create_portfolio_role(
        cls, user, portfolio, role_name, status=PortfolioRoleStatus.PENDING
    ):
        role = Roles.get(role_name)
        portfolio_role = PortfoliosQuery.create_portfolio_role(
            user, role, portfolio, status=status
        )
        PortfoliosQuery.add_and_commit(portfolio_role)
        return portfolio_role

    @classmethod
    def update(cls, portfolio, new_data):
        if "name" in new_data:
            portfolio.name = new_data["name"]

        PortfoliosQuery.add_and_commit(portfolio)

    @classmethod
    def can_revoke_access_for(cls, portfolio, portfolio_role):
        return (
            portfolio_role.user != portfolio.owner
            and portfolio_role.status == PortfolioRoleStatus.ACTIVE
        )

    @classmethod
    def revoke_access(cls, user, portfolio_id, portfolio_role_id):
        portfolio = PortfoliosQuery.get(portfolio_id)
        Authorization.check_portfolio_permission(
            user,
            portfolio,
            Permissions.ASSIGN_AND_UNASSIGN_ATAT_ROLE,
            "revoke portfolio access",
        )
        portfolio_role = PortfolioRoles.get_by_id(portfolio_role_id)

        if not Portfolios.can_revoke_access_for(portfolio, portfolio_role):
            raise PortfolioError("cannot revoke portfolio access for this user")

        portfolio_role.status = PortfolioRoleStatus.DISABLED
        for environment in portfolio.all_environments:
            Environments.revoke_access(user, environment, portfolio_role.user)
        PortfoliosQuery.add_and_commit(portfolio_role)

        return portfolio_role