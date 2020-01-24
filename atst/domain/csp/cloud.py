import re
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, validator

from flask import current_app as app

from atst.models.user import User
from atst.models.application import Application
from atst.models.environment import Environment
from atst.models.environment_role import EnvironmentRole
from atst.utils import snake_to_camel
from .policy import AzurePolicyManager


class GeneralCSPException(Exception):
    pass


class OperationInProgressException(GeneralCSPException):
    """Throw this for instances when the CSP reports that the current entity is already
    being operated on/created/deleted/etc
    """

    def __init__(self, operation_desc):
        self.operation_desc = operation_desc

    @property
    def message(self):
        return "An operation for this entity is already in progress: {}".format(
            self.operation_desc
        )


class AuthenticationException(GeneralCSPException):
    """Throw this for instances when there is a problem with the auth credentials:
    * Missing credentials
    * Incorrect credentials
    * Other credential problems
    """

    def __init__(self, auth_error):
        self.auth_error = auth_error

    @property
    def message(self):
        return "An error occurred with authentication: {}".format(self.auth_error)


class AuthorizationException(GeneralCSPException):
    """Throw this for instances when the current credentials are not authorized
    for the current action.
    """

    def __init__(self, auth_error):
        self.auth_error = auth_error

    @property
    def message(self):
        return "An error occurred with authorization: {}".format(self.auth_error)


class ConnectionException(GeneralCSPException):
    """A general problem with the connection, timeouts or unresolved endpoints
    """

    def __init__(self, connection_error):
        self.connection_error = connection_error

    @property
    def message(self):
        return "Could not connect to cloud provider: {}".format(self.connection_error)


class UnknownServerException(GeneralCSPException):
    """An error occured on the CSP side (5xx) and we don't know why
    """

    def __init__(self, server_error):
        self.server_error = server_error

    @property
    def message(self):
        return "A server error occured: {}".format(self.server_error)


class EnvironmentCreationException(GeneralCSPException):
    """If there was an error in creating the environment
    """

    def __init__(self, env_identifier, reason):
        self.env_identifier = env_identifier
        self.reason = reason

    @property
    def message(self):
        return "The envionment {} couldn't be created: {}".format(
            self.env_identifier, self.reason
        )


class UserProvisioningException(GeneralCSPException):
    """Failed to provision a user
    """

    def __init__(self, env_identifier, user_identifier, reason):
        self.env_identifier = env_identifier
        self.user_identifier = user_identifier
        self.reason = reason

    @property
    def message(self):
        return "Failed to create user {} for environment {}: {}".format(
            self.user_identifier, self.env_identifier, self.reason
        )


class UserRemovalException(GeneralCSPException):
    """Failed to remove a user
    """

    def __init__(self, user_csp_id, reason):
        self.user_csp_id = user_csp_id
        self.reason = reason

    @property
    def message(self):
        return "Failed to suspend or delete user {}: {}".format(
            self.user_csp_id, self.reason
        )


class BaselineProvisionException(GeneralCSPException):
    """If there's any issues standing up whatever is required
    for an environment baseline
    """

    def __init__(self, env_identifier, reason):
        self.env_identifier = env_identifier
        self.reason = reason

    @property
    def message(self):
        return "Could not complete baseline provisioning for environment ({}): {}".format(
            self.env_identifier, self.reason
        )


class AliasModel(BaseModel):
    """
    This provides automatic camel <-> snake conversion for serializing to/from json
    You can override the alias generation in subclasses by providing a Config that defines
    a fields property with a dict mapping variables to their cast names, for cases like:
    * some_url:someURL
    * user_object_id:objectId
    """

    class Config:
        alias_generator = snake_to_camel
        allow_population_by_field_name = True


class BaseCSPPayload(AliasModel):
    # {"username": "mock-cloud", "pass": "shh"}
    creds: Dict

    def dict(self, *args, **kwargs):
        exclude = {"creds"}
        if "exclude" not in kwargs:
            kwargs["exclude"] = exclude
        else:
            kwargs["exclude"].update(exclude)

        return super().dict(*args, **kwargs)


class TenantCSPPayload(BaseCSPPayload):
    user_id: str
    password: str
    domain_name: str
    first_name: str
    last_name: str
    country_code: str
    password_recovery_email_address: str


class TenantCSPResult(AliasModel):
    user_id: str
    tenant_id: str
    user_object_id: str

    tenant_admin_username: Optional[str]
    tenant_admin_password: Optional[str]

    class Config:
        fields = {
            "user_object_id": "objectId",
        }

    def dict(self, *args, **kwargs):
        exclude = {"tenant_admin_username", "tenant_admin_password"}
        if "exclude" not in kwargs:
            kwargs["exclude"] = exclude
        else:
            kwargs["exclude"].update(exclude)

        return super().dict(*args, **kwargs)

    def get_creds(self):
        return {
            "tenant_admin_username": self.tenant_admin_username,
            "tenant_admin_password": self.tenant_admin_password,
            "tenant_id": self.tenant_id,
        }


class BillingProfileAddress(AliasModel):
    company_name: str
    address_line_1: str
    city: str
    region: str
    country: str
    postal_code: str


class BillingProfileCLINBudget(AliasModel):
    clin_budget: Dict
    """
        "clinBudget": {
            "amount": 0,
            "startDate": "2019-12-18T16:47:40.909Z",
            "endDate": "2019-12-18T16:47:40.909Z",
            "externalReferenceId": "string"
        }
    """


class BillingProfileCreationCSPPayload(BaseCSPPayload):
    tenant_id: str
    billing_profile_display_name: str
    billing_account_name: str
    enabled_azure_plans: Optional[List[str]]
    address: BillingProfileAddress

    @validator("enabled_azure_plans", pre=True, always=True)
    def default_enabled_azure_plans(cls, v):
        """
        Normally you'd implement this by setting the field with a value of:
            dataclasses.field(default_factory=list)
        but that prevents the object from being correctly pickled, so instead we need
        to rely on a validator to ensure this has an empty value when not specified
        """
        return v or []

    class Config:
        fields = {"billing_profile_display_name": "displayName"}


class BillingProfileCreationCSPResult(AliasModel):
    billing_profile_verify_url: str
    billing_profile_retry_after: int

    class Config:
        fields = {
            "billing_profile_verify_url": "Location",
            "billing_profile_retry_after": "Retry-After",
        }


class BillingProfileVerificationCSPPayload(BaseCSPPayload):
    billing_profile_verify_url: str


class BillingInvoiceSection(AliasModel):
    invoice_section_id: str
    invoice_section_name: str

    class Config:
        fields = {"invoice_section_id": "id", "invoice_section_name": "name"}


class BillingProfileProperties(AliasModel):
    address: BillingProfileAddress
    billing_profile_display_name: str
    invoice_sections: List[BillingInvoiceSection]

    class Config:
        fields = {"billing_profile_display_name": "displayName"}


class BillingProfileVerificationCSPResult(AliasModel):
    billing_profile_id: str
    billing_profile_name: str
    billing_profile_properties: BillingProfileProperties

    class Config:
        fields = {
            "billing_profile_id": "id",
            "billing_profile_name": "name",
            "billing_profile_properties": "properties",
        }


class BillingProfileTenantAccessCSPPayload(BaseCSPPayload):
    tenant_id: str
    user_object_id: str
    billing_account_name: str
    billing_profile_name: str


class BillingProfileTenantAccessCSPResult(AliasModel):
    billing_role_assignment_id: str
    billing_role_assignment_name: str

    class Config:
        fields = {
            "billing_role_assignment_id": "id",
            "billing_role_assignment_name": "name",
        }


class TaskOrderBillingCreationCSPPayload(BaseCSPPayload):
    billing_account_name: str
    billing_profile_name: str


class TaskOrderBillingCreationCSPResult(AliasModel):
    task_order_billing_verify_url: str
    task_order_retry_after: int

    class Config:
        fields = {
            "task_order_billing_verify_url": "Location",
            "task_order_retry_after": "Retry-After",
        }


class TaskOrderBillingVerificationCSPPayload(BaseCSPPayload):
    task_order_billing_verify_url: str


class BillingProfileEnabledPlanDetails(AliasModel):
    enabled_azure_plans: List[Dict]


class TaskOrderBillingVerificationCSPResult(AliasModel):
    billing_profile_id: str
    billing_profile_name: str
    billing_profile_enabled_plan_details: BillingProfileEnabledPlanDetails

    class Config:
        fields = {
            "billing_profile_id": "id",
            "billing_profile_name": "name",
            "billing_profile_enabled_plan_details": "properties",
        }


class BillingInstructionCSPPayload(BaseCSPPayload):
    initial_clin_amount: float
    initial_clin_start_date: str
    initial_clin_end_date: str
    initial_clin_type: str
    initial_task_order_id: str
    billing_account_name: str
    billing_profile_name: str


class BillingInstructionCSPResult(AliasModel):
    reported_clin_name: str

    class Config:
        fields = {
            "reported_clin_name": "name",
        }


class CloudProviderInterface:
    def set_secret(self, secret_key: str, secret_value: str):
        raise NotImplementedError()

    def get_secret(self, secret_key: str):
        raise NotImplementedError()

    def root_creds(self) -> Dict:
        raise NotImplementedError()

    def create_environment(
        self, auth_credentials: Dict, user: User, environment: Environment
    ) -> str:
        """Create a new environment in the CSP.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            user -- ATAT user authorizing the environment creation
            environment -- ATAT Environment model

        Returns:
            string: ID of created environment

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            EnvironmentExistsException: Environment already exists and has been created
        """
        raise NotImplementedError()

    def create_atat_admin_user(
        self, auth_credentials: Dict, csp_environment_id: str
    ) -> Dict:
        """Creates a new, programmatic user in the CSP. Grants this user full permissions to administer
        the CSP.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_environment_id -- ID of the CSP Environment the admin user should be created in

        Returns:
            object: Object representing new remote admin user, including credentials
            Something like:
            {
                "user_id": string,
                "credentials": dict, # structure TBD based on csp
            }

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserProvisioningException: Problem creating the root user
        """
        raise NotImplementedError()

    def create_or_update_user(
        self, auth_credentials: Dict, user_info: EnvironmentRole, csp_role_id: str
    ) -> str:
        """Creates a user or updates an existing user's role.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            user_info -- instance of EnvironmentRole containing user data
                         if it has a csp_user_id it will try to update that user
            csp_role_id -- The id of the role the user should be given in the CSP

        Returns:
            string: Returns the interal csp_user_id of the created/updated user account

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserProvisioningException: User couldn't be created or modified
        """
        raise NotImplementedError()

    def disable_user(self, auth_credentials: Dict, csp_user_id: str) -> bool:
        """Revoke all privileges for a user. Used to prevent user access while a full
        delete is being processed.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_user_id -- CSP internal user identifier

        Returns:
            bool -- True on success

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserRemovalException: User couldn't be suspended
        """
        raise NotImplementedError()

    def get_calculator_url(self) -> str:
        """Returns the calculator url for the CSP.
        This will likely be a static property elsewhere once a CSP is chosen.
        """
        raise NotImplementedError()

    def get_environment_login_url(self, environment) -> str:
        """Returns the login url for a given environment
        This may move to be a computed property on the Environment domain object
        """
        raise NotImplementedError()

    def create_subscription(self, environment):
        """Returns True if a new subscription has been created or raises an
        exception if an error occurs while creating a subscription.
        """
        raise NotImplementedError()


class MockCloudProvider(CloudProviderInterface):

    # TODO: All of these constants
    AUTHENTICATION_EXCEPTION = AuthenticationException("Authentication failure.")
    AUTHORIZATION_EXCEPTION = AuthorizationException("Not authorized.")
    NETWORK_EXCEPTION = ConnectionException("Network failure.")
    SERVER_EXCEPTION = UnknownServerException("Not our fault.")

    SERVER_FAILURE_PCT = 1
    NETWORK_FAILURE_PCT = 7
    ENV_CREATE_FAILURE_PCT = 12
    ATAT_ADMIN_CREATE_FAILURE_PCT = 12
    UNAUTHORIZED_RATE = 2

    def __init__(
        self, config, with_delay=True, with_failure=True, with_authorization=True
    ):
        from time import sleep
        import random

        self._with_delay = with_delay
        self._with_failure = with_failure
        self._with_authorization = with_authorization
        self._sleep = sleep
        self._random = random

    def root_creds(self):
        return self._auth_credentials

    def set_secret(self, secret_key: str, secret_value: str):
        pass

    def get_secret(self, secret_key: str, default=dict()):
        return default

    def create_environment(self, auth_credentials, user, environment):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ENV_CREATE_FAILURE_PCT,
            EnvironmentCreationException(
                environment.id, "Could not create environment."
            ),
        )

        csp_environment_id = self._id()

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            BaselineProvisionException(
                csp_environment_id, "Could not create environment baseline."
            ),
        )
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return csp_environment_id

    def create_atat_admin_user(self, auth_credentials, csp_environment_id):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserProvisioningException(
                csp_environment_id, "atat_admin", "Could not create admin user."
            ),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return {"id": self._id(), "credentials": self._auth_credentials}

    def create_tenant(self, payload: TenantCSPPayload):
        """
        payload is an instance of TenantCSPPayload data class
        """

        self._authorize(payload.creds)

        self._delay(1, 5)

        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return TenantCSPResult(
            **{
                "tenant_id": "",
                "user_id": "",
                "user_object_id": "",
                "tenant_admin_username": "test",
                "tenant_admin_password": "test",
            }
        )

    def create_billing_profile_creation(
        self, payload: BillingProfileCreationCSPPayload
    ):
        # response will be mostly the same as the body, but we only really care about the id
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return BillingProfileCreationCSPResult(
            **dict(
                billing_profile_verify_url="https://zombo.com",
                billing_profile_retry_after=10,
            )
        )

    def create_billing_profile_verification(
        self, payload: BillingProfileVerificationCSPPayload
    ):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        return BillingProfileVerificationCSPResult(
            **{
                "id": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/KQWI-W2SU-BG7-TGB",
                "name": "KQWI-W2SU-BG7-TGB",
                "properties": {
                    "address": {
                        "addressLine1": "123 S Broad Street, Suite 2400",
                        "city": "Philadelphia",
                        "companyName": "Promptworks",
                        "country": "US",
                        "postalCode": "19109",
                        "region": "PA",
                    },
                    "currency": "USD",
                    "displayName": "Test Billing Profile",
                    "enabledAzurePlans": [],
                    "hasReadAccess": True,
                    "invoiceDay": 5,
                    "invoiceEmailOptIn": False,
                    "invoiceSections": [
                        {
                            "id": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/KQWI-W2SU-BG7-TGB/invoiceSections/CHCO-BAAR-PJA-TGB",
                            "name": "CHCO-BAAR-PJA-TGB",
                            "properties": {"displayName": "Test Billing Profile"},
                            "type": "Microsoft.Billing/billingAccounts/billingProfiles/invoiceSections",
                        }
                    ],
                },
                "type": "Microsoft.Billing/billingAccounts/billingProfiles",
            }
        )

    def create_billing_profile_tenant_access(self, payload):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return BillingProfileTenantAccessCSPResult(
            **{
                "id": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/KQWI-W2SU-BG7-TGB/billingRoleAssignments/40000000-aaaa-bbbb-cccc-100000000000_0a5f4926-e3ee-4f47-a6e3-8b0a30a40e3d",
                "name": "40000000-aaaa-bbbb-cccc-100000000000_0a5f4926-e3ee-4f47-a6e3-8b0a30a40e3d",
                "properties": {
                    "createdOn": "2020-01-14T14:39:26.3342192+00:00",
                    "createdByPrincipalId": "82e2b376-3297-4096-8743-ed65b3be0b03",
                    "principalId": "0a5f4926-e3ee-4f47-a6e3-8b0a30a40e3d",
                    "principalTenantId": "60ff9d34-82bf-4f21-b565-308ef0533435",
                    "roleDefinitionId": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/KQWI-W2SU-BG7-TGB/billingRoleDefinitions/40000000-aaaa-bbbb-cccc-100000000000",
                    "scope": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/KQWI-W2SU-BG7-TGB",
                },
                "type": "Microsoft.Billing/billingRoleAssignments",
            }
        )

    def create_task_order_billing_creation(
        self, payload: TaskOrderBillingCreationCSPPayload
    ):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return TaskOrderBillingCreationCSPResult(
            **{"Location": "https://somelocation", "Retry-After": "10"}
        )

    def create_task_order_billing_verification(
        self, payload: TaskOrderBillingVerificationCSPPayload
    ):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return TaskOrderBillingVerificationCSPResult(
            **{
                "id": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/XC36-GRNZ-BG7-TGB",
                "name": "XC36-GRNZ-BG7-TGB",
                "properties": {
                    "address": {
                        "addressLine1": "123 S Broad Street, Suite 2400",
                        "city": "Philadelphia",
                        "companyName": "Promptworks",
                        "country": "US",
                        "postalCode": "19109",
                        "region": "PA",
                    },
                    "currency": "USD",
                    "displayName": "First Portfolio Billing Profile",
                    "enabledAzurePlans": [
                        {
                            "productId": "DZH318Z0BPS6",
                            "skuId": "0001",
                            "skuDescription": "Microsoft Azure Plan",
                        }
                    ],
                    "hasReadAccess": True,
                    "invoiceDay": 5,
                    "invoiceEmailOptIn": False,
                },
                "type": "Microsoft.Billing/billingAccounts/billingProfiles",
            }
        )

    def create_billing_instruction(self, payload: BillingInstructionCSPPayload):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return BillingInstructionCSPResult(
            **{
                "name": "TO1:CLIN001",
                "properties": {
                    "amount": 1000.0,
                    "endDate": "2020-03-01T00:00:00+00:00",
                    "startDate": "2020-01-01T00:00:00+00:00",
                },
                "type": "Microsoft.Billing/billingAccounts/billingProfiles/billingInstructions",
            }
        )

    def create_or_update_user(self, auth_credentials, user_info, csp_role_id):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserProvisioningException(
                user_info.environment.id,
                user_info.application_role.user_id,
                "Could not create user.",
            ),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        return self._id()

    def disable_user(self, auth_credentials, csp_user_id):
        self._authorize(auth_credentials)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)

        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserRemovalException(csp_user_id, "Could not disable user."),
        )

        return self._maybe(12)

    def create_subscription(self, environment):
        self._maybe_raise(self.UNAUTHORIZED_RATE, GeneralCSPException)

        return True

    def get_calculator_url(self):
        return "https://www.rackspace.com/en-us/calculator"

    def get_environment_login_url(self, environment):
        """Returns the login url for a given environment
        """
        return "https://www.mycloud.com/my-env-login"

    def _id(self):
        return uuid4().hex

    def _delay(self, min_secs, max_secs):
        if self._with_delay:
            duration = self._random.randrange(min_secs, max_secs)
            self._sleep(duration)

    def _maybe(self, pct):
        return not self._with_failure or self._random.randrange(0, 100) < pct

    def _maybe_raise(self, pct, exc):
        if self._with_failure and self._maybe(pct):
            raise exc

    @property
    def _auth_credentials(self):
        return {"username": "mock-cloud", "password": "shh"}  # pragma: allowlist secret

    def _authorize(self, credentials):
        self._delay(1, 5)
        if self._with_authorization and credentials != self._auth_credentials:
            raise self.AUTHENTICATION_EXCEPTION


AZURE_ENVIRONMENT = "AZURE_PUBLIC_CLOUD"  # TBD
AZURE_SKU_ID = "?"  # probably a static sku specific to ATAT/JEDI
SUBSCRIPTION_ID_REGEX = re.compile(
    "subscriptions\/([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})",
    re.I,
)

# This needs to be a fully pathed role definition identifier, not just a UUID
REMOTE_ROOT_ROLE_DEF_ID = "/providers/Microsoft.Authorization/roleDefinitions/00000000-0000-4000-8000-000000000000"
AZURE_MANAGEMENT_API = "https://management.azure.com"


class AzureSDKProvider(object):
    def __init__(self):
        from azure.mgmt import subscription, authorization, managementgroups
        from azure.mgmt.resource import policy
        import azure.graphrbac as graphrbac
        import azure.common.credentials as credentials
        import azure.identity as identity
        from azure.keyvault import secrets

        from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD
        import adal
        import requests

        self.subscription = subscription
        self.policy = policy
        self.managementgroups = managementgroups
        self.authorization = authorization
        self.adal = adal
        self.graphrbac = graphrbac
        self.credentials = credentials
        self.identity = identity
        self.exceptions = exceptions
        self.secrets = secrets
        self.requests = requests
        # may change to a JEDI cloud
        self.cloud = AZURE_PUBLIC_CLOUD


class AzureCloudProvider(CloudProviderInterface):
    def __init__(self, config, azure_sdk_provider=None):
        self.config = config

        self.client_id = config["AZURE_CLIENT_ID"]
        self.secret_key = config["AZURE_SECRET_KEY"]
        self.tenant_id = config["AZURE_TENANT_ID"]
        self.vault_url = config["AZURE_VAULT_URL"]

        if azure_sdk_provider is None:
            self.sdk = AzureSDKProvider()
        else:
            self.sdk = azure_sdk_provider

        self.policy_manager = AzurePolicyManager(config["AZURE_POLICY_LOCATION"])

    def set_secret(self, secret_key, secret_value):
        credential = self._get_client_secret_credential_obj({})
        secret_client = self.secrets.SecretClient(
            vault_url=self.vault_url, credential=credential,
        )
        try:
            return secret_client.set_secret(secret_key, secret_value)
        except self.exceptions.HttpResponseError:
            app.logger.error(
                f"Could not SET secret in Azure keyvault for key {secret_key}.",
                exc_info=1,
            )

    def get_secret(self, secret_key):
        credential = self._get_client_secret_credential_obj({})
        secret_client = self.secrets.SecretClient(
            vault_url=self.vault_url, credential=credential,
        )
        try:
            return secret_client.get_secret(secret_key).value
        except self.exceptions.HttpResponseError:
            app.logger.error(
                f"Could not GET secret in Azure keyvault for key {secret_key}.",
                exc_info=1,
            )

    def create_environment(
        self, auth_credentials: Dict, user: User, environment: Environment
    ):
        # since this operation would only occur within a tenant, should we source the tenant
        # via lookup from environment once we've created the portfolio csp data schema
        # something like this:
        # environment_tenant = environment.application.portfolio.csp_data.get('tenant_id', None)
        # though we'd probably source the whole credentials for these calls from the portfolio csp
        # data, as it would have to be where we store the creds for the at-at user within the portfolio tenant
        # credentials = self._get_credential_obj(environment.application.portfolio.csp_data.get_creds())
        credentials = self._get_credential_obj(self._root_creds)
        display_name = f"{environment.application.name}_{environment.name}_{environment.id}"  # proposed format
        management_group_id = "?"  # management group id chained from environment
        parent_id = "?"  # from environment.application

        management_group = self._create_management_group(
            credentials, management_group_id, display_name, parent_id,
        )

        return management_group

    def create_atat_admin_user(
        self, auth_credentials: Dict, csp_environment_id: str
    ) -> Dict:
        root_creds = self._root_creds
        credentials = self._get_credential_obj(root_creds)

        sub_client = self.sdk.subscription.SubscriptionClient(credentials)
        subscription = sub_client.subscriptions.get(csp_environment_id)

        managment_principal = self._get_management_service_principal()

        auth_client = self.sdk.authorization.AuthorizationManagementClient(
            credentials,
            # TODO: Determine which subscription this needs to point at
            # Once we're in a multi-sub environment
            subscription.id,
        )

        # Create role assignment for
        role_assignment_id = str(uuid4())
        role_assignment_create_params = auth_client.role_assignments.models.RoleAssignmentCreateParameters(
            role_definition_id=REMOTE_ROOT_ROLE_DEF_ID,
            principal_id=managment_principal.id,
        )

        auth_client.role_assignments.create(
            scope=f"/subscriptions/{subscription.id}/",
            role_assignment_name=role_assignment_id,
            parameters=role_assignment_create_params,
        )

        return {
            "csp_user_id": managment_principal.object_id,
            "credentials": managment_principal.password_credentials,
            "role_name": role_assignment_id,
        }

    def _create_application(self, auth_credentials: Dict, application: Application):
        management_group_name = str(uuid4())  # can be anything, not just uuid
        display_name = application.name  # Does this need to be unique?
        credentials = self._get_credential_obj(auth_credentials)
        parent_id = "?"  # application.portfolio.csp_details.management_group_id

        return self._create_management_group(
            credentials, management_group_name, display_name, parent_id,
        )

    def _create_management_group(
        self, credentials, management_group_id, display_name, parent_id=None,
    ):
        mgmgt_group_client = self.sdk.managementgroups.ManagementGroupsAPI(credentials)
        create_parent_grp_info = self.sdk.managementgroups.models.CreateParentGroupInfo(
            id=parent_id
        )
        create_mgmt_grp_details = self.sdk.managementgroups.models.CreateManagementGroupDetails(
            parent=create_parent_grp_info
        )
        mgmt_grp_create = self.sdk.managementgroups.models.CreateManagementGroupRequest(
            name=management_group_id,
            display_name=display_name,
            details=create_mgmt_grp_details,
        )
        create_request = mgmgt_group_client.management_groups.create_or_update(
            management_group_id, mgmt_grp_create
        )

        # result is a synchronous wait, might need to do a poll instead to handle first mgmt group create
        # since we were told it could take 10+ minutes to complete, unless this handles that polling internally
        return create_request.result()

    def _create_subscription(
        self,
        credentials,
        display_name,
        billing_profile_id,
        sku_id,
        management_group_id,
        billing_account_name,
        invoice_section_name,
    ):
        sub_client = self.sdk.subscription.SubscriptionClient(credentials)

        billing_profile_id = "?"  # where do we source this?
        sku_id = AZURE_SKU_ID
        # These 2 seem like something that might be worthwhile to allow tiebacks to
        # TOs filed for the environment
        billing_account_name = "?"  # from TO?
        invoice_section_name = "?"  # from TO?

        body = self.sdk.subscription.models.ModernSubscriptionCreationParameters(
            display_name=display_name,
            billing_profile_id=billing_profile_id,
            sku_id=sku_id,
            management_group_id=management_group_id,
        )

        # We may also want to create billing sections in the enrollment account
        sub_creation_operation = sub_client.subscription_factory.create_subscription(
            billing_account_name, invoice_section_name, body
        )

        # the resulting object from this process is a link to the new subscription
        # not a subscription model, so we'll have to unpack the ID
        new_sub = sub_creation_operation.result()

        subscription_id = self._extract_subscription_id(new_sub.subscription_link)
        if subscription_id:
            return subscription_id
        else:
            # troublesome error, subscription should exist at this point
            # but we just don't have a valid ID
            pass

    def _create_policy_definition(
        self, credentials, subscription_id, management_group_id, properties,
    ):
        """
        Requires credentials that have AZURE_MANAGEMENT_API
        specified as the resource. The Service Principal
        specified in the credentials must have the "Resource
        Policy Contributor" role assigned with a scope at least
        as high as the management group specified by
        management_group_id.

        Arguments:
            credentials -- ServicePrincipalCredentials
            subscription_id -- str, ID of the subscription (just the UUID, not the path)
            management_group_id -- str, ID of the management group (just the UUID, not the path)
            properties -- dictionary, the "properties" section of a valid Azure policy definition document

        Returns:
            azure.mgmt.resource.policy.[api version].models.PolicyDefinition: the PolicyDefinition object provided to Azure

        Raises:
            TBD
        """
        # TODO: which subscription would this be?
        client = self.sdk.policy.PolicyClient(credentials, subscription_id)

        definition = client.policy_definitions.models.PolicyDefinition(
            policy_type=properties.get("policyType"),
            mode=properties.get("mode"),
            display_name=properties.get("displayName"),
            description=properties.get("description"),
            policy_rule=properties.get("policyRule"),
            parameters=properties.get("parameters"),
        )

        name = properties.get("displayName")

        return client.policy_definitions.create_or_update_at_management_group(
            policy_definition_name=name,
            parameters=definition,
            management_group_id=management_group_id,
        )

    def create_tenant(self, payload: TenantCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException("Could not resolve token for tenant creation")

        create_tenant_body = payload.dict(by_alias=True)

        create_tenant_headers = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.post(
            "https://management.azure.com/providers/Microsoft.SignUp/createTenant?api-version=2020-01-01-preview",
            json=create_tenant_body,
            headers=create_tenant_headers,
        )

        if result.status_code == 200:
            return self._ok(
                TenantCSPResult(
                    **result.json(),
                    tenant_admin_password=payload.password,
                    tenant_admin_username=payload.user_id,
                )
            )
        else:
            return self._error(result.json())

    def create_billing_profile_creation(
        self, payload: BillingProfileCreationCSPPayload
    ):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for billing profile creation"
            )

        create_billing_account_body = payload.dict(by_alias=True)

        create_billing_account_headers = {
            "Authorization": f"Bearer {sp_token}",
        }

        billing_account_create_url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles?api-version=2019-10-01-preview"

        result = self.sdk.requests.post(
            billing_account_create_url,
            json=create_billing_account_body,
            headers=create_billing_account_headers,
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(BillingProfileCreationCSPResult(**result.headers))
        elif result.status_code == 200:
            # NB: Swagger docs imply call can sometimes resolve immediately
            return self._ok(BillingProfileVerificationCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_billing_profile_verification(
        self, payload: BillingProfileVerificationCSPPayload
    ):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for billing profile validation"
            )

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.get(
            payload.billing_profile_verify_url, headers=auth_header
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(BillingProfileCreationCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(BillingProfileVerificationCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_billing_profile_tenant_access(
        self, payload: BillingProfileTenantAccessCSPPayload
    ):
        sp_token = self._get_sp_token(payload.creds)
        request_body = {
            "properties": {
                "principalTenantId": payload.tenant_id,  # from tenant creation
                "principalId": payload.user_object_id,  # from tenant creationn
                "roleDefinitionId": f"/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles/{payload.billing_profile_name}/billingRoleDefinitions/40000000-aaaa-bbbb-cccc-100000000000",
            }
        }

        headers = {
            "Authorization": f"Bearer {sp_token}",
        }

        url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles/{payload.billing_profile_name}/createBillingRoleAssignment?api-version=2019-10-01-preview"

        result = self.sdk.requests.post(url, headers=headers, json=request_body)
        if result.status_code == 201:
            return self._ok(BillingProfileTenantAccessCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_task_order_billing_creation(
        self, payload: TaskOrderBillingCreationCSPPayload
    ):
        sp_token = self._get_sp_token(payload.creds)
        request_body = [
            {
                "op": "replace",
                "path": "/enabledAzurePlans",
                "value": [{"skuId": "0001"}],
            }
        ]

        request_headers = {
            "Authorization": f"Bearer {sp_token}",
        }

        url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles/{payload.billing_profile_name}?api-version=2019-10-01-preview"

        result = self.sdk.requests.patch(
            url, headers=request_headers, json=request_body
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(TaskOrderBillingCreationCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(TaskOrderBillingVerificationCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_task_order_billing_verification(
        self, payload: TaskOrderBillingVerificationCSPPayload
    ):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for task order billing validation"
            )

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.get(
            payload.task_order_billing_verify_url, headers=auth_header
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(TaskOrderBillingCreationCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(TaskOrderBillingVerificationCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_billing_instruction(self, payload: BillingInstructionCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for task order billing validation"
            )

        request_body = {
            "properties": {
                "amount": payload.initial_clin_amount,
                "startDate": payload.initial_clin_start_date,
                "endDate": payload.initial_clin_end_date,
            }
        }

        url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles/{payload.billing_profile_name}/instructions/{payload.initial_task_order_id}:CLIN00{payload.initial_clin_type}?api-version=2019-10-01-preview"

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.put(url, headers=auth_header, json=request_body)

        if result.status_code == 200:
            return self._ok(BillingInstructionCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_remote_admin(self, creds, tenant_details):
        # create app/service principal within tenant, with name constructed from tenant details
        # assign principal global admin

        # needs to call out to CLI with tenant owner username/password, prototyping for that underway

        # return identifier and creds to consumer for storage
        response = {"clientId": "string", "secretKey": "string", "tenantId": "string"}
        return self._ok(
            {
                "client_id": response["clientId"],
                "secret_key": response["secret_key"],
                "tenant_id": response["tenantId"],
            }
        )

    def force_tenant_admin_pw_update(self, creds, tenant_owner_id):
        # use creds to update to force password recovery?
        # not sure what the endpoint/method for this is, yet

        return self._ok()

    def create_billing_alerts(self, TBD):
        # TODO: Add azure-mgmt-consumption for Budget and Notification entities/operations
        # TODO: Determine how to auth against that API using the SDK, doesn't seeem possible at the moment
        # TODO: billing alerts are registered as Notifications on Budget objects, which have start/end dates
        # TODO: determine what the keys in the Notifications dict are supposed to be
        # we may need to rotate budget objects when new TOs/CLINs are reported?

        # we likely only want the budget ID, can be updated or replaced?
        response = {"id": "id"}
        return self._ok({"budget_id": response["id"]})

    def _get_management_service_principal(self):
        # we really should be using graph.microsoft.com, but i'm getting
        # "expired token" errors for that
        # graph_resource = "https://graph.microsoft.com"
        graph_resource = "https://graph.windows.net"
        graph_creds = self._get_credential_obj(
            self._root_creds, resource=graph_resource
        )
        # I needed to set permissions for the graph.windows.net API before I
        # could get this to work.

        # how do we scope the graph client to the new subscription rather than
        # the cloud0 subscription? tenant id seems to be separate from subscription id
        graph_client = self.sdk.graphrbac.GraphRbacManagementClient(
            graph_creds, self._root_creds.get("tenant_id")
        )

        # do we need to create a new application to manage each subscripition
        # or should we manage access to each subscription from a single service
        # principal with multiple role assignments?
        app_display_name = "?"  # name should reflect the subscription it exists
        app_create_param = self.sdk.graphrbac.models.ApplicationCreateParameters(
            display_name=app_display_name
        )

        # we need the appropriate perms here:
        # https://docs.microsoft.com/en-us/graph/api/application-post-applications?view=graph-rest-beta&tabs=http
        # https://docs.microsoft.com/en-us/graph/permissions-reference#microsoft-graph-permission-names
        # set app perms in app registration portal
        # https://docs.microsoft.com/en-us/graph/auth-v2-service#2-configure-permissions-for-microsoft-graph
        app: self.sdk.graphrbac.models.Application = graph_client.applications.create(
            app_create_param
        )

        # create a new service principle for the new application, which should be scoped
        # to the new subscription
        app_id = app.app_id
        sp_create_params = self.sdk.graphrbac.models.ServicePrincipalCreateParameters(
            app_id=app_id, account_enabled=True
        )

        service_principal = graph_client.service_principals.create(sp_create_params)

        return service_principal

    def _extract_subscription_id(self, subscription_url):
        sub_id_match = SUBSCRIPTION_ID_REGEX.match(subscription_url)

        if sub_id_match:
            return sub_id_match.group(1)

    def _get_sp_token(self, creds):
        home_tenant_id = creds.get("home_tenant_id")
        client_id = creds.get("client_id")
        secret_key = creds.get("secret_key")

        # TODO: Make endpoints consts or configs
        authentication_endpoint = "https://login.microsoftonline.com/"
        resource = "https://management.azure.com/"

        context = self.sdk.adal.AuthenticationContext(
            authentication_endpoint + home_tenant_id
        )

        # TODO: handle failure states here
        token_response = context.acquire_token_with_client_credentials(
            resource, client_id, secret_key
        )

        return token_response.get("accessToken", None)

    def _get_credential_obj(self, creds, resource=None):
        return self.sdk.credentials.ServicePrincipalCredentials(
            client_id=creds.get("client_id"),
            secret=creds.get("secret_key"),
            tenant=creds.get("tenant_id"),
            resource=resource,
            cloud_environment=self.sdk.cloud,
        )

    def _get_client_secret_credential_obj(self, creds):
        return self.sdk.identity.ClientSecretCredential(
            tenant_id=creds.get("tenant_id"),
            client_id=creds.get("client_id"),
            client_secret=creds.get("secret_key"),
        )

    def _make_tenant_admin_cred_obj(self, username, password):
        return self.sdk.credentials.UserPassCredentials(username, password)

    def _ok(self, body=None):
        return self._make_response("ok", body)

    def _error(self, body=None):
        return self._make_response("error", body)

    def _make_response(self, status, body=dict()):
        """Create body for responses from API

        Arguments:
            status {string} -- "ok" or "error"
            body {dict} -- dict containing details of response or error, if applicable

        Returns:
            dict -- status of call with body containing details
        """
        return {"status": status, "body": body}

    @property
    def _root_creds(self):
        return {
            "client_id": self.client_id,
            "secret_key": self.secret_key,
            "tenant_id": self.tenant_id,
        }
