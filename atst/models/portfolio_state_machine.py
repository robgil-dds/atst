from random import choice, choices
import re
import string

from sqlalchemy import Column, ForeignKey, Enum as SQLAEnum
from sqlalchemy.orm import relationship, reconstructor
from sqlalchemy.dialects.postgresql import UUID

from pydantic import ValidationError as PydanticValidationError
from transitions import Machine
from transitions.extensions.states import add_state_features, Tags

from flask import current_app as app

from atst.domain.csp.cloud import ConnectionException, UnknownServerException
from atst.domain.csp import MockCSP, AzureCSP, get_stage_csp_class
from atst.database import db
from atst.models.types import Id
from atst.models.base import Base
import atst.models.mixins as mixins
from atst.models.mixins.state_machines import FSMStates, AzureStages, _build_transitions


def make_password():
    return choice(string.ascii_letters) + "".join(
        choices(string.ascii_letters + string.digits + string.punctuation, k=15)
    )


def fetch_portfolio_creds(portfolio):
    return dict(username="mock-cloud", password="shh")


@add_state_features(Tags)
class StateMachineWithTags(Machine):
    pass


class PortfolioStateMachine(
    Base,
    mixins.TimestampsMixin,
    mixins.AuditableMixin,
    mixins.DeletableMixin,
    mixins.FSMMixin,
):
    __tablename__ = "portfolio_state_machines"

    id = Id()

    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"),)
    portfolio = relationship("Portfolio", back_populates="state_machine")

    state = Column(
        SQLAEnum(FSMStates, native_enum=False, create_constraint=False),
        default=FSMStates.UNSTARTED,
        nullable=False,
    )

    def __init__(self, portfolio, csp=None, **kwargs):
        self.portfolio = portfolio
        self.attach_machine()

    def after_state_change(self, event):
        db.session.add(self)
        db.session.commit()

    @reconstructor
    def attach_machine(self):
        """
        This is called as a result of a sqlalchemy query.
        Attach a machine depending on the current state.
        """
        self.machine = StateMachineWithTags(
            model=self,
            send_event=True,
            initial=self.current_state if self.state else FSMStates.UNSTARTED,
            auto_transitions=False,
            after_state_change="after_state_change",
        )
        states, transitions = _build_transitions(AzureStages)
        self.machine.add_states(self.system_states + states)
        self.machine.add_transitions(self.system_transitions + transitions)

    @property
    def current_state(self):
        if isinstance(self.state, str):
            return getattr(FSMStates, self.state)
        return self.state

    def trigger_next_transition(self, **kwargs):
        state_obj = self.machine.get_state(self.state)

        if state_obj.is_system:
            if self.current_state in (FSMStates.UNSTARTED, FSMStates.STARTING):
                # call the first trigger availabe for these two system states
                trigger_name = self.machine.get_triggers(self.current_state.name)[0]
                self.trigger(trigger_name, **kwargs)

            elif self.current_state == FSMStates.STARTED:
                # get the first trigger that starts with 'create_'
                create_trigger = self._get_first_stage_create_trigger()
                if create_trigger:
                    self.trigger(create_trigger, **kwargs)
                else:
                    self.fail_stage(stage)

        elif state_obj.is_CREATED:
            # the create trigger for the next stage should be in the available
            # triggers for the current state
            triggers = self.machine.get_triggers(state_obj.name)
            create_trigger = list(
                filter(
                    lambda trigger: trigger.startswith("create_"),
                    self.machine.get_triggers(self.state.name),
                )
            )[0]
            if create_trigger:
                self.trigger(create_trigger, **kwargs)

    # @with_payload
    def after_in_progress_callback(self, event):
        stage = self.current_state.name.split("_IN_PROGRESS")[0].lower()

        # Accumulate payload w/ creds
        payload = event.kwargs.get("csp_data")
        payload["creds"] = event.kwargs.get("creds")

        payload_data_cls = get_stage_csp_class(stage, "payload")
        if not payload_data_cls:
            print("could not resolve payload data class")
            self.fail_stage(stage)
        try:
            payload_data = payload_data_cls(**payload)
        except PydanticValidationError as exc:
            print("Payload Validation Error:")
            print(exc.json())
            print("got")
            print(payload)
            self.fail_stage(stage)

        # TODO: Determine best place to do this, maybe @reconstructor
        csp = event.kwargs.get("csp")
        if csp is not None:
            self.csp = AzureCSP(app).cloud
        else:
            self.csp = MockCSP(app).cloud

        for attempt in range(5):
            try:
                func_name = f"create_{stage}"
                response = getattr(self.csp, func_name)(payload_data)
            except (ConnectionException, UnknownServerException) as exc:
                print("caught exception. retry", attempt)
                continue
            else:
                break
        else:
            # failed all attempts
            print("failed")
            self.fail_stage(stage)

        if self.portfolio.csp_data is None:
            self.portfolio.csp_data = {}
        self.portfolio.csp_data.update(response)
        db.session.add(self.portfolio)
        db.session.commit()

        # store any updated creds, if necessary

        self.finish_stage(stage)

    def is_csp_data_valid(self, event):
        # check portfolio csp details json field for fields

        if self.portfolio.csp_data is None or not isinstance(
            self.portfolio.csp_data, dict
        ):
            print("no csp data")
            return False

        stage = self.current_state.name.split("_IN_PROGRESS")[0].lower()
        stage_data = self.portfolio.csp_data
        cls = get_stage_csp_class(stage, "result")
        if not cls:
            return False

        try:
            dc = cls(**stage_data)
            if getattr(dc, "get_creds", None) is not None:
                new_creds = dc.get_creds()
                # TODO: how/where to store these
                # TODO: credential schema
                # self.store_creds(self.portfolio, new_creds)

        except PydanticValidationError as exc:
            print(exc.json())
            return False

        return True

        # print('failed condition', self.portfolio.csp_data)

    @property
    def application_id(self):
        return None
