from flask import render_template, request as http_request, g, redirect, url_for

from .blueprint import portfolios_bp
from atst.domain.portfolios import Portfolios
from atst.domain.portfolio_roles import PortfolioRoles
from atst.models.portfolio_role import Status as PortfolioRoleStatus
from atst.domain.invitations import PortfolioInvitations
from atst.domain.permission_sets import PermissionSets
from atst.domain.audit_log import AuditLog
from atst.domain.common import Paginator
from atst.forms.portfolio import PortfolioForm
import atst.forms.portfolio_member as member_forms
from atst.models.permissions import Permissions
from atst.domain.authz.decorator import user_can_access_decorator as user_can
from atst.utils import first_or_none
from atst.utils.flash import formatted_flash as flash
from atst.domain.exceptions import UnauthorizedError


def filter_perm_sets_data(member):
    perm_sets_data = {
        "perms_portfolio_mgmt": bool(
            member.has_permission_set(PermissionSets.EDIT_PORTFOLIO_ADMIN)
        ),
        "perms_app_mgmt": bool(
            member.has_permission_set(
                PermissionSets.EDIT_PORTFOLIO_APPLICATION_MANAGEMENT
            )
        ),
        "perms_funding": bool(
            member.has_permission_set(PermissionSets.EDIT_PORTFOLIO_FUNDING)
        ),
        "perms_reporting": bool(
            member.has_permission_set(PermissionSets.EDIT_PORTFOLIO_REPORTS)
        ),
    }

    return perm_sets_data


def filter_members_data(members_list):
    members_data = []
    for member in members_list:
        members_data.append(
            {
                "role_id": member.id,
                "user_name": member.user_name,
                "permission_sets": filter_perm_sets_data(member),
                # add in stuff here for forms
            }
        )

    return sorted(members_data, key=lambda member: member["user_name"])


def render_admin_page(portfolio, form=None):
    pagination_opts = Paginator.get_pagination_opts(http_request)
    audit_events = AuditLog.get_portfolio_events(portfolio, pagination_opts)
    portfolio_form = PortfolioForm(obj=portfolio)
    ppoc = filter_members_data([portfolio.owner_role])[0]
    member_list = portfolio.members
    member_list.remove(portfolio.owner_role)
    assign_ppoc_form = member_forms.AssignPPOCForm()

    for pf_role in portfolio.roles:
        if pf_role.user != portfolio.owner and pf_role.is_active:
            assign_ppoc_form.role_id.choices += [(pf_role.id, pf_role.full_name)]

    current_member = first_or_none(
        lambda m: m.user_id == g.current_user.id, portfolio.members
    )
    current_member_id = current_member.id if current_member else None

    return render_template(
        "portfolios/admin.html",
        form=form,
        portfolio_form=portfolio_form,
        ppoc=ppoc,
        members=filter_members_data(member_list),
        member_form=member_forms.NewForm(),
        assign_ppoc_form=assign_ppoc_form,
        portfolio=portfolio,
        audit_events=audit_events,
        user=g.current_user,
        current_member_id=current_member_id,
        applications_count=len(portfolio.applications),
    )


@portfolios_bp.route("/portfolios/<portfolio_id>/admin")
@user_can(Permissions.VIEW_PORTFOLIO_ADMIN, message="view portfolio admin page")
def admin(portfolio_id):
    portfolio = Portfolios.get_for_update(portfolio_id)
    return render_admin_page(portfolio)


@portfolios_bp.route("/portfolios/<portfolio_id>/admin", methods=["POST"])
@user_can(Permissions.EDIT_PORTFOLIO_USERS, message="view portfolio admin page")
def edit_members(portfolio_id):
    portfolio = Portfolios.get_for_update(portfolio_id)
    member_perms_form = member_forms.MembersPermissionsForm(http_request.form)

    if member_perms_form.validate():
        for subform in member_perms_form.members_permissions:
            member_id = subform.member_id.data
            member = PortfolioRoles.get_by_id(member_id)
            if member is not portfolio.owner_role:
                new_perm_set = subform.data["permission_sets"]
                PortfolioRoles.update(member, new_perm_set)

        flash("update_portfolio_members", portfolio=portfolio)

        return redirect(
            url_for(
                "portfolios.admin",
                portfolio_id=portfolio_id,
                fragment="portfolio-members",
                _anchor="portfolio-members",
            )
        )
    else:
        return render_admin_page(portfolio)


@portfolios_bp.route("/portfolios/<portfolio_id>/update_ppoc", methods=["POST"])
@user_can(Permissions.EDIT_PORTFOLIO_POC, message="update portfolio ppoc")
def update_ppoc(portfolio_id):
    role_id = http_request.form.get("role_id")

    portfolio = Portfolios.get(g.current_user, portfolio_id)
    new_ppoc_role = PortfolioRoles.get_by_id(role_id)

    PortfolioRoles.make_ppoc(portfolio_role=new_ppoc_role)

    flash("primary_point_of_contact_changed", ppoc_name=new_ppoc_role.full_name)

    return redirect(
        url_for(
            "portfolios.admin",
            portfolio_id=portfolio.id,
            fragment="primary-point-of-contact",
            _anchor="primary-point-of-contact",
        )
    )


@portfolios_bp.route("/portfolios/<portfolio_id>/edit", methods=["POST"])
@user_can(Permissions.EDIT_PORTFOLIO_NAME, message="edit portfolio")
def edit(portfolio_id):
    portfolio = Portfolios.get_for_update(portfolio_id)
    form = PortfolioForm(http_request.form)
    if form.validate():
        Portfolios.update(portfolio, form.data)
        return redirect(
            url_for("applications.portfolio_applications", portfolio_id=portfolio.id)
        )
    else:
        # rerender portfolio admin page
        return render_admin_page(portfolio, form)


@portfolios_bp.route(
    "/portfolios/<portfolio_id>/members/<portfolio_role_id>/delete", methods=["POST"]
)
@user_can(Permissions.EDIT_PORTFOLIO_USERS, message="update portfolio members")
def remove_member(portfolio_id, portfolio_role_id):
    portfolio_role = PortfolioRoles.get_by_id(portfolio_role_id)

    if g.current_user.id == portfolio_role.user_id:
        raise UnauthorizedError(
            g.current_user, "you cant remove yourself from the portfolio"
        )

    portfolio = Portfolios.get(user=g.current_user, portfolio_id=portfolio_id)
    if portfolio_role.user_id == portfolio.owner.id:
        raise UnauthorizedError(
            g.current_user, "you can't delete the portfolios PPoC from the portfolio"
        )

    if (
        portfolio_role.latest_invitation
        and portfolio_role.status == PortfolioRoleStatus.PENDING
    ):
        PortfolioInvitations.revoke(portfolio_role.latest_invitation.token)
    else:
        PortfolioRoles.disable(portfolio_role=portfolio_role)

    flash("portfolio_member_removed", member_name=portfolio_role.full_name)

    return redirect(
        url_for(
            "portfolios.admin",
            portfolio_id=portfolio_id,
            _anchor="portfolio-members",
            fragment="portfolio-members",
        )
    )
