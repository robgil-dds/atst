import pytest

from tests.factories import (
    PortfolioFactory,
    PortfolioStateMachineFactory,
)

from atst.models import FSMStates
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


def test_state_machine_first_stage_create_trigger(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    first_stage_create_trigger = sm._get_first_stage_create_trigger()
    first_stage_name = list(AzureStages)[0].name.lower()
    assert "create_" + first_stage_name == first_stage_create_trigger


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
        first_stage_create_trigger = sm._get_first_stage_create_trigger()
        assert ["reset", "fail", first_stage_create_trigger] == started_triggers


def test_fsm_transition_start(portfolio):
    sm = PortfolioStateMachineFactory.create(portfolio=portfolio)
    assert sm.portfolio
    assert sm.state == FSMStates.UNSTARTED

    sm.init()
    assert sm.state == FSMStates.STARTING

    sm.start()
    assert sm.state == FSMStates.STARTED
    sm.create_tenant(a=1, b=2)
    assert sm.state == FSMStates.TENANT_CREATED
