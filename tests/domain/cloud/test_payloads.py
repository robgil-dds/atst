import pytest

from pydantic import ValidationError

from atst.domain.csp.cloud import (
    AZURE_MGMNT_PATH,
    ManagementGroupCSPPayload,
    ManagementGroupCSPResponse,
)


def test_ManagementGroupCSPPayload_management_group_name():
    # supplies management_group_name when absent
    payload = ManagementGroupCSPPayload(
        creds={}, display_name="Council of Naboo", parent_id="Galactic_Senate"
    )
    assert payload.management_group_name
    # validates management_group_name
    with pytest.raises(ValidationError):
        payload = ManagementGroupCSPPayload(
            creds={},
            management_group_name="council of Naboo 1%^&",
            display_name="Council of Naboo",
            parent_id="Galactic_Senate",
        )
    # shortens management_group_name to fit
    name = "council_of_naboo"
    for _ in range(90):
        name = f"{name}1"

    assert len(name) > 90
    payload = ManagementGroupCSPPayload(
        creds={},
        management_group_name=name,
        display_name="Council of Naboo",
        parent_id="Galactic_Senate",
    )
    assert len(payload.management_group_name) == 90


def test_ManagementGroupCSPPayload_display_name():
    # shortens display_name to fit
    name = "Council of Naboo"
    for _ in range(90):
        name = f"{name}1"
    assert len(name) > 90
    payload = ManagementGroupCSPPayload(
        creds={}, display_name=name, parent_id="Galactic_Senate"
    )
    assert len(payload.display_name) == 90


def test_ManagementGroupCSPPayload_parent_id():
    full_path = f"{AZURE_MGMNT_PATH}Galactic_Senate"
    # adds full path
    payload = ManagementGroupCSPPayload(
        creds={}, display_name="Council of Naboo", parent_id="Galactic_Senate"
    )
    assert payload.parent_id == full_path
    # keeps full path
    payload = ManagementGroupCSPPayload(
        creds={}, display_name="Council of Naboo", parent_id=full_path
    )
    assert payload.parent_id == full_path


def test_ManagementGroupCSPResponse_id():
    full_id = "/path/to/naboo-123"
    response = ManagementGroupCSPResponse(
        **{"id": "/path/to/naboo-123", "other": "stuff"}
    )
    assert response.id == full_id
