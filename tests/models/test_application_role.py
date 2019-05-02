from atst.domain.permission_sets import PermissionSets
from atst.models.audit_event import AuditEvent

from tests.factories import PortfolioFactory, UserFactory


def test_has_application_role_history(session):
    owner = UserFactory.create()
    user = UserFactory.create()

    PortfolioFactory.create(
        owner=owner,
        applications=[
            {
                "name": "starkiller",
                "environments": [
                    {
                        "name": "bridge",
                        "members": [{"user": user, "role_name": "developer"}],
                    }
                ],
            }
        ],
    )

    app_role = user.application_roles[0]
    app_role.permission_sets = [
        PermissionSets.get(PermissionSets.EDIT_APPLICATION_TEAM)
    ]
    session.add(app_role)
    session.commit()

    changed_event = (
        session.query(AuditEvent)
        .filter(AuditEvent.resource_id == app_role.id, AuditEvent.action == "update")
        .one()
    )
    old_state, new_state = changed_event.changed_state["permission_sets"]
    assert old_state == [PermissionSets.VIEW_APPLICATION]
    assert new_state == [PermissionSets.EDIT_APPLICATION_TEAM]