from flask import url_for

from atst.domain.permission_sets import PermissionSets
from atst.domain.portfolio_roles import PortfolioRoles
from atst.domain.portfolios import Portfolios
from atst.models.permissions import Permissions
from atst.models.portfolio_role import Status as PortfolioRoleStatus
from atst.utils.localization import translate

from tests.factories import PortfolioFactory, PortfolioRoleFactory, UserFactory


def test_member_table_access(client, user_session):
    admin = UserFactory.create()
    portfolio = PortfolioFactory.create(owner=admin)
    rando = UserFactory.create()
    PortfolioRoleFactory.create(
        user=rando,
        portfolio=portfolio,
        permission_sets=[PermissionSets.get(PermissionSets.VIEW_PORTFOLIO_ADMIN)],
    )

    url = url_for("portfolios.admin", portfolio_id=portfolio.id)

    # editable
    user_session(admin)
    edit_resp = client.get(url)
    assert "<select" in edit_resp.data.decode()

    # not editable
    user_session(rando)
    view_resp = client.get(url)
    assert "<select" not in view_resp.data.decode()


def test_update_member_permissions(client, user_session):
    portfolio = PortfolioFactory.create()
    rando = UserFactory.create()
    rando_pf_role = PortfolioRoleFactory.create(
        user=rando,
        portfolio=portfolio,
        permission_sets=[PermissionSets.get(PermissionSets.VIEW_PORTFOLIO_ADMIN)],
    )

    user = UserFactory.create()
    PortfolioRoleFactory.create(
        user=user,
        portfolio=portfolio,
        permission_sets=PermissionSets.get_many(
            [PermissionSets.EDIT_PORTFOLIO_ADMIN, PermissionSets.VIEW_PORTFOLIO_ADMIN]
        ),
    )
    user_session(user)

    form_data = {
        "members_permissions-0-user_id": rando.id,
        "members_permissions-0-perms_app_mgmt": "edit_portfolio_application_management",
        "members_permissions-0-perms_funding": "view_portfolio_funding",
        "members_permissions-0-perms_reporting": "view_portfolio_reports",
        "members_permissions-0-perms_portfolio_mgmt": "view_portfolio_admin",
    }

    response = client.post(
        url_for("portfolios.edit_members", portfolio_id=portfolio.id),
        data=form_data,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert rando_pf_role.has_permission_set(
        PermissionSets.EDIT_PORTFOLIO_APPLICATION_MANAGEMENT
    )


def test_no_update_member_permissions_without_edit_access(client, user_session):
    portfolio = PortfolioFactory.create()
    rando = UserFactory.create()
    rando_pf_role = PortfolioRoleFactory.create(
        user=rando,
        portfolio=portfolio,
        permission_sets=[PermissionSets.get(PermissionSets.VIEW_PORTFOLIO_ADMIN)],
    )

    user = UserFactory.create()
    PortfolioRoleFactory.create(
        user=user,
        portfolio=portfolio,
        permission_sets=[PermissionSets.get(PermissionSets.VIEW_PORTFOLIO_ADMIN)],
    )
    user_session(user)

    form_data = {
        "members_permissions-0-user_id": rando.id,
        "members_permissions-0-perms_app_mgmt": "edit_portfolio_application_management",
        "members_permissions-0-perms_funding": "view_portfolio_funding",
        "members_permissions-0-perms_reporting": "view_portfolio_reports",
        "members_permissions-0-perms_portfolio_mgmt": "view_portfolio_admin",
    }

    response = client.post(
        url_for("portfolios.edit_members", portfolio_id=portfolio.id),
        data=form_data,
        follow_redirects=True,
    )

    assert response.status_code == 404
    assert not rando_pf_role.has_permission_set(
        PermissionSets.EDIT_PORTFOLIO_APPLICATION_MANAGEMENT
    )


def test_rerender_admin_page_if_member_perms_form_does_not_validate(
    client, user_session
):
    portfolio = PortfolioFactory.create()
    user = UserFactory.create()
    PortfolioRoleFactory.create(
        user=user,
        portfolio=portfolio,
        permission_sets=[PermissionSets.get(PermissionSets.EDIT_PORTFOLIO_ADMIN)],
    )
    user_session(user)
    form_data = {
        "members_permissions-0-user_id": user.id,
        "members_permissions-0-perms_app_mgmt": "bad input",
        "members_permissions-0-perms_funding": "view_portfolio_funding",
        "members_permissions-0-perms_reporting": "view_portfolio_reports",
        "members_permissions-0-perms_portfolio_mgmt": "view_portfolio_admin",
    }

    response = client.post(
        url_for("portfolios.edit_members", portfolio_id=portfolio.id),
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Portfolio Administration" in response.data.decode()


def test_cannot_update_portfolio_ppoc_perms(client, user_session):
    portfolio = PortfolioFactory.create()
    ppoc = portfolio.owner
    ppoc_pf_role = PortfolioRoles.get(portfolio_id=portfolio.id, user_id=ppoc.id)
    user = UserFactory.create()
    PortfolioRoleFactory.create(portfolio=portfolio, user=user)

    user_session(user)

    assert ppoc_pf_role.has_permission_set(PermissionSets.PORTFOLIO_POC)

    member_perms_data = {
        "members_permissions-0-user_id": ppoc.id,
        "members_permissions-0-perms_app_mgmt": "view_portfolio_application_management",
        "members_permissions-0-perms_funding": "view_portfolio_funding",
        "members_permissions-0-perms_reporting": "view_portfolio_reports",
        "members_permissions-0-perms_portfolio_mgmt": "view_portfolio_admin",
    }

    response = client.post(
        url_for("portfolios.edit_members", portfolio_id=portfolio.id),
        data=member_perms_data,
        follow_redirects=True,
    )

    assert response.status_code == 404
    assert ppoc_pf_role.has_permission_set(PermissionSets.PORTFOLIO_POC)


def test_update_portfolio_name(client, user_session):
    portfolio = PortfolioFactory.create()
    user_session(portfolio.owner)
    response = client.post(
        url_for("portfolios.edit", portfolio_id=portfolio.id),
        data={"name": "a cool new name"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert portfolio.name == "a cool new name"


def updating_ppoc_successfully(client, old_ppoc, new_ppoc, portfolio):
    response = client.post(
        url_for("portfolios.update_ppoc", portfolio_id=portfolio.id, _external=True),
        data={"user_id": new_ppoc.id},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == url_for(
        "portfolios.admin",
        portfolio_id=portfolio.id,
        fragment="primary-point-of-contact",
        _anchor="primary-point-of-contact",
        _external=True,
    )
    assert portfolio.owner.id == new_ppoc.id
    assert (
        Permissions.EDIT_PORTFOLIO_POC
        in PortfolioRoles.get(
            portfolio_id=portfolio.id, user_id=new_ppoc.id
        ).permissions
    )
    assert (
        Permissions.EDIT_PORTFOLIO_POC
        not in PortfolioRoles.get(portfolio.id, old_ppoc.id).permissions
    )


def test_update_ppoc_no_user_id_specified(client, user_session):
    portfolio = PortfolioFactory.create()

    user_session(portfolio.owner)

    response = client.post(
        url_for("portfolios.update_ppoc", portfolio_id=portfolio.id, _external=True),
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_update_ppoc_to_member_not_on_portfolio(client, user_session):
    portfolio = PortfolioFactory.create()
    original_ppoc = portfolio.owner
    non_portfolio_member = UserFactory.create()

    user_session(original_ppoc)

    response = client.post(
        url_for("portfolios.update_ppoc", portfolio_id=portfolio.id, _external=True),
        data={"user_id": non_portfolio_member.id},
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert portfolio.owner.id == original_ppoc.id


def test_update_ppoc_when_ppoc(client, user_session):
    portfolio = PortfolioFactory.create()
    original_ppoc = portfolio.owner
    new_ppoc = UserFactory.create()
    Portfolios.add_member(
        member=new_ppoc,
        portfolio=portfolio,
        permission_sets=[PermissionSets.VIEW_PORTFOLIO],
    )

    user_session(original_ppoc)

    updating_ppoc_successfully(
        client=client, new_ppoc=new_ppoc, old_ppoc=original_ppoc, portfolio=portfolio
    )


def test_update_ppoc_when_cpo(client, user_session):
    ccpo = UserFactory.create_ccpo()
    portfolio = PortfolioFactory.create()
    original_ppoc = portfolio.owner
    new_ppoc = UserFactory.create()
    Portfolios.add_member(
        member=new_ppoc,
        portfolio=portfolio,
        permission_sets=[PermissionSets.VIEW_PORTFOLIO],
    )

    user_session(ccpo)

    updating_ppoc_successfully(
        client=client, new_ppoc=new_ppoc, old_ppoc=original_ppoc, portfolio=portfolio
    )


def test_update_ppoc_when_not_ppoc(client, user_session):
    portfolio = PortfolioFactory.create()
    new_owner = UserFactory.create()

    user_session(new_owner)

    response = client.post(
        url_for("portfolios.update_ppoc", portfolio_id=portfolio.id, _external=True),
        data={"dod_id": new_owner.dod_id},
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_portfolio_admin_screen_when_ppoc(client, user_session):
    portfolio = PortfolioFactory.create()
    user_session(portfolio.owner)
    response = client.get(url_for("portfolios.admin", portfolio_id=portfolio.id))
    assert response.status_code == 200
    assert portfolio.name in response.data.decode()
    assert translate("fragments.ppoc.update_btn").encode("utf8") in response.data


def test_portfolio_admin_screen_when_not_ppoc(client, user_session):
    portfolio = PortfolioFactory.create()
    user = UserFactory.create()
    permission_sets = PermissionSets.get_many(
        [PermissionSets.EDIT_PORTFOLIO_ADMIN, PermissionSets.VIEW_PORTFOLIO_ADMIN]
    )
    PortfolioRoleFactory.create(
        portfolio=portfolio, user=user, permission_sets=permission_sets
    )
    user_session(user)
    response = client.get(url_for("portfolios.admin", portfolio_id=portfolio.id))
    assert response.status_code == 200
    assert portfolio.name in response.data.decode()
    assert translate("fragments.ppoc.update_btn").encode("utf8") not in response.data


def test_remove_portfolio_member(client, user_session):
    portfolio = PortfolioFactory.create()

    user = UserFactory.create()
    PortfolioRoleFactory.create(portfolio=portfolio, user=user)

    user_session(portfolio.owner)

    response = client.post(
        url_for("portfolios.remove_member", portfolio_id=portfolio.id, user_id=user.id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == url_for(
        "portfolios.admin",
        portfolio_id=portfolio.id,
        _anchor="portfolio-members",
        fragment="portfolio-members",
        _external=True,
    )
    assert (
        PortfolioRoles.get(portfolio_id=portfolio.id, user_id=user.id).status
        == PortfolioRoleStatus.DISABLED
    )


def test_remove_portfolio_member_self(client, user_session):
    portfolio = PortfolioFactory.create()

    user_session(portfolio.owner)

    response = client.post(
        url_for(
            "portfolios.remove_member",
            portfolio_id=portfolio.id,
            user_id=portfolio.owner.id,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert (
        PortfolioRoles.get(portfolio_id=portfolio.id, user_id=portfolio.owner.id).status
        == PortfolioRoleStatus.ACTIVE
    )