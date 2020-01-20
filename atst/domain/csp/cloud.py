import re
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, validator

from atst.models.user import User
from atst.models.environment import Environment
from atst.models.environment_role import EnvironmentRole
from atst.utils import snake_to_camel


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

    tenant_admin_username: str
    tenant_admin_password: str

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


class BillingProfileCSPPayload(BaseCSPPayload):
    tenant_id: str
    billing_profile_display_name: str
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


class BillingProfileCreateCSPResult(AliasModel):
    billing_profile_validate_url: str
    retry_after: int

    class Config:
        fields = {
            "billing_profile_validate_url": "Location",
            "retry_after": "Retry-After",
        }


class BillingProfileVerifyCSPPayload(BaseCSPPayload):
    billing_profile_validate_url: str


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


class BillingProfileCSPResult(AliasModel):
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


class TaskOrderBillingCSPPayload(BaseCSPPayload):
    billing_account_name: str
    billing_profile_name: str


class EnableTaskOrderBillingCSPResult(AliasModel):
    task_order_billing_validation_url: str
    retry_after: int

    class Config:
        fields = {
            "task_order_billing_validation_url": "Location",
            "retry_after": "Retry-After",
        }


class TaskOrderBillingCSPResult(BaseCSPPayload):
    task_order_billing_validation_url: str


class BillingProfileEnabledPlanDetails(AliasModel):
    enabled_azure_plans: List[Dict]


class TaskOrderBillingCSPResult(AliasModel):
    billing_profile_id: str
    billing_profile_name: str
    billing_profile_enabled_plan_details: BillingProfileEnabledPlanDetails

    class Config:
        fields = {
            "billing_profile_id": "id",
            "billing_profile_name": "name",
            "billing_profile_enabled_plan_details": "properties",
        }


class ReportCLINCSPPayload(BaseCSPPayload):
    amount: float
    start_date: str
    end_date: str
    clin_type: str
    task_order_id: str
    billing_account_name: str
    billing_profile_name: str


class ReportCLINCSPResult(AliasModel):
    reported_clin_name: str

    class Config:
        fields = {
            "reported_clin_name": "name",
        }


class CloudProviderInterface:


    def set_secret(secret_key: str, secret_value: str):
        raise NotImplementedError()

    def get_secret(secret_key: str, secret_value: str):
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

    def create_tenant(self, payload):
        """
        payload is an instance of TenantCSPPayload data class
        """

        self._authorize(payload.creds)

        self._delay(1, 5)

        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        # return tenant id, tenant owner id and tenant owner object id from:
        response = {"tenantId": "string", "userId": "string", "objectId": "string"}
        return {
            "tenant_id": response["tenantId"],
            "user_id": response["userId"],
            "user_object_id": response["objectId"],
            "tenant_admin_username": "test",
            "tenant_admin_password": "test",
        }

    def create_billing_profile(self, payload):
        # call billing profile creation endpoint, specifying owner
        # Payload:
        """
        {
            "displayName": "string",
            "poNumber": "string",
            "address": {
                "firstName": "string",
                "lastName": "string",
                "companyName": "string",
                "addressLine1": "string",
                "addressLine2": "string",
                "addressLine3": "string",
                "city": "string",
                "region": "string",
                "country": "string",
                "postalCode": "string"
            },
            "invoiceEmailOptIn": true,
            Note: These last 2 are also the body for adding/updating new TOs/clins
            "enabledAzurePlans": [
                {
                "skuId": "string"
                }
            ],
            "clinBudget": {
                "amount": 0,
                "startDate": "2019-12-18T16:47:40.909Z",
                "endDate": "2019-12-18T16:47:40.909Z",
                "externalReferenceId": "string"
            }
        }
        """
        # response will be mostly the same as the body, but we only really care about the id
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        response = {"id": "string"}
        # return {"billing_profile_id": response["id"]}
        return {
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

    def create_billing_profile_tenant_access(self, payload):
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return {
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
        return {"username": "mock-cloud", "password": "shh"}

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


class AzureSDKProvider(object):
    def __init__(self):
        from azure.mgmt import subscription, authorization
        import azure.graphrbac as graphrbac
        import azure.common.credentials as credentials
        import azure.identity as identity
        from azure.keyvault import secrets import secrets

        from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD
        import adal
        import requests

        self.subscription = subscription
        self.authorization = authorization
        self.adal = adal
        self.graphrbac = graphrbac
        self.credentials = credentials
        self.identity = identity
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

    def set_secret(secret_key, secret_value):
        credential = self._get_client_secret_credential_obj()
        secret_client = self.secrets.SecretClient(
            vault_url=self.vault_url,
            credential=credential,
        )
        return secret_client.set_secret(secret_key, secret_value)

    def get_secret(secret_key)
        credential = self._get_client_secret_credential_obj()
        secret_client = self.secrets.SecretClient(
            vault_url=self.vault_url,
            credential=credential,
        )
        return secret_client.get_secret(secret_key).value

    def create_environment(
        self, auth_credentials: Dict, user: User, environment: Environment
    ):
        credentials = self._get_credential_obj(self._root_creds)
        sub_client = self.sdk.subscription.SubscriptionClient(credentials)

        display_name = f"{environment.application.name}_{environment.name}_{environment.id}"  # proposed format

        billing_profile_id = "?"  # something chained from environment?
        sku_id = AZURE_SKU_ID
        # we want to set AT-AT as an owner here
        # we could potentially associate subscriptions with "management groups" per DOD component
        body = self.sdk.subscription.models.ModernSubscriptionCreationParameters(
            display_name,
            billing_profile_id,
            sku_id,
            # owner=<AdPrincipal: for AT-AT user>
        )

        # These 2 seem like something that might be worthwhile to allow tiebacks to
        # TOs filed for the environment
        billing_account_name = "?"
        invoice_section_name = "?"
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

        print("create tenant result")
        print(result.json())

        if result.status_code == 200:
            return self._ok(TenantCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_billing_profile(self, payload: BillingProfileCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for billing profile creation"
            )

        create_billing_account_body = payload.dict(by_alias=True)

        create_billing_account_headers = {
            "Authorization": f"Bearer {sp_token}",
        }

        # TODO: unsure if this is a static value or needs to be constructed/configurable
        BILLING_ACCOUT_NAME = "7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31"
        billing_account_create_url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{BILLING_ACCOUT_NAME}/billingProfiles?api-version=2019-10-01-preview"

        result = self.sdk.requests.post(
            billing_account_create_url,
            json=create_billing_account_body,
            headers=create_billing_account_headers,
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(BillingProfileCreateCSPResult(**result.headers))
        elif result.status_code == 200:
            # NB: Swagger docs imply call can sometimes resolve immediately
            return self._ok(BillingProfileCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def validate_billing_profile_created(self, payload: BillingProfileVerifyCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for billing profile validation"
            )

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.get(
            payload.billing_profile_validate_url, headers=auth_header
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(BillingProfileCreateCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(BillingProfileCSPResult(**result.json()))
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

    def enable_task_order_billing(self, payload: TaskOrderBillingCSPPayload):
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
            return self._ok(BillingProfileCreateCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(TaskOrderBillingCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def validate_task_order_billing_enabled(self, payload: TaskOrderBillingCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for task order billing validation"
            )

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.get(
            payload.task_order_billing_validation_url, headers=auth_header
        )

        if result.status_code == 202:
            # 202 has location/retry after headers
            return self._ok(TaskOrderBillingCSPResult(**result.headers))
        elif result.status_code == 200:
            return self._ok(TaskOrderBillingCSPResult(**result.json()))
        else:
            return self._error(result.json())

    def create_billing_instruction(self, payload: ReportCLINCSPPayload):
        sp_token = self._get_sp_token(payload.creds)
        if sp_token is None:
            raise AuthenticationException(
                "Could not resolve token for task order billing validation"
            )

        request_body = {
            "properties": {
                "amount": payload.amount,
                "startDate": payload.start_date,
                "endDate": payload.end_date,
            }
        }

        url = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{payload.billing_account_name}/billingProfiles/{payload.billing_profile_name}/instructions/{payload.task_order_id}:CLIN00{payload.clin_type}?api-version=2019-10-01-preview"

        auth_header = {
            "Authorization": f"Bearer {sp_token}",
        }

        result = self.sdk.requests.put(url, headers=auth_header, json=request_body)

        if result.status_code == 200:
            return self._ok(ReportCLINCSPResult(**result.json()))
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
        home_tenant_id = creds.get(
            "home_tenant_id"
        )
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
    def _get_client_secret_credential_obj():
        return self.sdk.identity.ClientSecretCredential(
            tenant_id=creds.get("tenant_id"),
            client_id =creds.get("client_id"),
            client_secret = creds.get("secret_key"),
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
