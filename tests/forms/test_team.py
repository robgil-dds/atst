from wtforms.validators import ValidationError
import pytest

from atst.domain.permission_sets import PermissionSets
from atst.forms.team import *


def test_permissions_form_permission_sets():
    form_data = {
        "perms_team_mgmt": PermissionSets.EDIT_APPLICATION_TEAM,
        "perms_env_mgmt": PermissionSets.VIEW_APPLICATION,
        "perms_del_env": "View only",
    }
    form = PermissionsForm(data=form_data)

    assert form.validate()
    assert form.data == [
        PermissionSets.EDIT_APPLICATION_TEAM,
        PermissionSets.VIEW_APPLICATION,
        "View only",
    ]


def test_permissions_form_invalid():
    form_data = {
        "perms_team_mgmt": PermissionSets.EDIT_APPLICATION_TEAM,
        "perms_env_mgmt": "not a real choice",
        "perms_del_env": "View only",
    }
    form = PermissionsForm(data=form_data)
    assert not form.validate()
