import pytest
import re

from tests.factories import (
    PortfolioFactory,
    PortfolioStateMachineFactory,
)

from atst.models import FSMStates, PortfolioStateMachine
from atst.models.mixins.state_machines import AzureStages, StageStates, compose_state
from atst.domain.csp import get_stage_csp_class


@pytest.fixture(scope="function")
def portfolio():
    portfolio = PortfolioFactory.create()
    return portfolio


def test_fsm_creation(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    assert sm.portfolio


def test_state_machine_trigger_next_transition(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)

    sm.trigger_next_transition()
    assert sm.current_state == FSMStates.STARTING

    sm.trigger_next_transition()
    assert sm.current_state == FSMStates.STARTED


def test_state_machine_compose_state(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    assert (
        compose_state(AzureStages.TENANT, StageStates.CREATED)
        == FSMStates.TENANT_CREATED
    )


def test_state_machine_valid_data_classes_for_stages(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    for stage in AzureStages:
        assert get_stage_csp_class(stage.name.lower(), "payload") is not None
        assert get_stage_csp_class(stage.name.lower(), "result") is not None


def test_state_machine_initialization(portfolio):

    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    for stage in AzureStages:

        # check that all stages have a 'create' and 'fail' triggers
        stage_name = stage.name.lower()
        for trigger_prefix in ["create", "fail"]:
            assert hasattr(sm, trigger_prefix + "_" + stage_name)

        # check that machine
        in_progress_triggers = sm.machine.get_triggers(stage.name + "_IN_PROGRESS")
        assert [
            "reset",
            "fail",
            "finish_" + stage_name,
            "fail_" + stage_name,
        ] == in_progress_triggers

        started_triggers = sm.machine.get_triggers("STARTED")
        create_trigger = next(
            filter(
                lambda trigger: trigger.startswith("create_"),
                sm.machine.get_triggers(FSMStates.STARTED.name),
            ),
            None,
        )
        assert ["reset", "fail", create_trigger] == started_triggers


def test_fsm_transition_start(portfolio):
    sm: PortfolioStateMachine = PortfolioStateMachineFactory.create(portfolio=portfolio)
    assert sm.portfolio
    assert sm.state == FSMStates.UNSTARTED

    sm.init()
    assert sm.state == FSMStates.STARTING

    sm.start()
    assert sm.state == FSMStates.STARTED

    # Should source all creds for portfolio? might be easier to manage than per-step specific ones
    creds = {"username": "mock-cloud", "password": "shh"}
    if portfolio.csp_data is not None:
        csp_data = portfolio.csp_data
    else:
        csp_data = {}

    # ppoc = portfolio.owner
    # user_id = f"{ppoc.first_name[0]}{ppoc.last_name}".lower()
    user_id = "abcdefg"
    domain_name = re.sub("[^0-9a-zA-Z]+", "", portfolio.name).lower()

    portfolio_data = {
        "user_id": user_id,
        "password": "jklfsdNCVD83nklds2#202",
        "domain_name": domain_name,
        "first_name": "john",  # ppoc.first_name,
        "last_name": "doe",  # ppoc.last_name,
        "country_code": "US",
        "password_recovery_email_address": "email@example.com",  # ppoc.email,
        "address": {
            "company_name": "",
            "address_line_1": "",
            "city": "",
            "region": "",
            "country": "",
            "postal_code": "",
        },
        "billing_profile_display_name": "My Billing Profile",
    }

    config = {"billing_account_name": "billing_account_name"}

    collected_data = dict(
        list(csp_data.items()) + list(portfolio_data.items()) + list(config.items())
    )
    sm.trigger_next_transition(creds=creds, csp_data=collected_data)

    assert sm.state == FSMStates.TENANT_CREATED
    assert portfolio.csp_data.get("tenant_id", None) is not None
    #print(portfolio.csp_data.keys())
    if portfolio.csp_data is not None:
        csp_data = portfolio.csp_data
    else:
        csp_data = {}
    collected_data = dict(
        list(csp_data.items()) + list(portfolio_data.items()) + list(config.items())
    )
    sm.trigger_next_transition(creds=creds, csp_data=collected_data)
    assert sm.state == FSMStates.BILLING_PROFILE_CREATION_CREATED

    #print(portfolio.csp_data.keys())
