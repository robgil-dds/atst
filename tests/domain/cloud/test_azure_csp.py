import pytest
from unittest.mock import Mock

from uuid import uuid4

from atst.domain.csp.cloud import (
    AzureCloudProvider,
    TenantCSPResult,
    TenantCSPPayload,
    BillingProfileCSPPayload,
    BillingProfileAddress,
    BillingProfileCreateCSPResult,
    BillingProfileVerifyCSPPayload,
    BillingProfileCSPResult,
)

from tests.mock_azure import mock_azure, AUTH_CREDENTIALS
from tests.factories import EnvironmentFactory, ApplicationFactory


# TODO: Directly test create subscription, provide all args √
# TODO: Test create environment (create management group with parent)
# TODO: Test create application (create manageemnt group with parent)
# Create reusable mock for mocking the management group calls for multiple services
#


@pytest.mark.skip()
def test_create_subscription_succeeds(mock_azure: AzureCloudProvider):
    environment = EnvironmentFactory.create()

    subscription_id = str(uuid4())

    credentials = mock_azure._get_credential_obj(AUTH_CREDENTIALS)
    display_name = "Test Subscription"
    billing_profile_id = str(uuid4())
    sku_id = str(uuid4())
    management_group_id = (
        environment.cloud_id  # environment.csp_details.management_group_id?
    )
    billing_account_name = (
        "?"  # environment.application.portfilio.csp_details.billing_account.name?
    )
    invoice_section_name = "?"  # environment.name? or something specific to billing?

    mock_azure.sdk.subscription.SubscriptionClient.return_value.subscription_factory.create_subscription.return_value.result.return_value.subscription_link = (
        f"subscriptions/{subscription_id}"
    )

    result = mock_azure._create_subscription(
        credentials,
        display_name,
        billing_profile_id,
        sku_id,
        management_group_id,
        billing_account_name,
        invoice_section_name,
    )

    assert result == subscription_id


@pytest.mark.skip()
def mock_management_group_create(mock_azure, spec_dict):
    mock_azure.sdk.managementgroups.ManagementGroupsAPI.return_value.management_groups.create_or_update.return_value.result.return_value = Mock(
        **spec_dict
    )


@pytest.mark.skip()
def test_create_environment_succeeds(mock_azure: AzureCloudProvider):
    environment = EnvironmentFactory.create()

    mock_management_group_create(mock_azure, {"id": "Test Id"})

    result = mock_azure.create_environment(
        AUTH_CREDENTIALS, environment.creator, environment
    )

    assert result.id == "Test Id"


@pytest.mark.skip()
def test_create_application_succeeds(mock_azure: AzureCloudProvider):
    application = ApplicationFactory.create()

    mock_management_group_create(mock_azure, {"id": "Test Id"})

    result = mock_azure._create_application(AUTH_CREDENTIALS, application)

    assert result.id == "Test Id"


@pytest.mark.skip()
def test_create_atat_admin_user_succeeds(mock_azure: AzureCloudProvider):
    environment_id = str(uuid4())

    csp_user_id = str(uuid4)

    mock_azure.sdk.graphrbac.GraphRbacManagementClient.return_value.service_principals.create.return_value.object_id = (
        csp_user_id
    )

    result = mock_azure.create_atat_admin_user(AUTH_CREDENTIALS, environment_id)

    assert result.get("csp_user_id") == csp_user_id


@pytest.mark.skip()
def test_create_policy_definition_succeeds(mock_azure: AzureCloudProvider):
    subscription_id = str(uuid4())
    management_group_id = str(uuid4())
    properties = {
        "policyType": "test",
        "displayName": "test policy",
    }

    result = mock_azure._create_policy_definition(
        AUTH_CREDENTIALS, subscription_id, management_group_id, properties
    )
    azure_sdk_method = (
        mock_azure.sdk.policy.PolicyClient.return_value.policy_definitions.create_or_update_at_management_group
    )
    mock_policy_definition = (
        mock_azure.sdk.policy.PolicyClient.return_value.policy_definitions.models.PolicyDefinition()
    )
    assert azure_sdk_method.called
    azure_sdk_method.assert_called_with(
        management_group_id=management_group_id,
        policy_definition_name=properties.get("displayName"),
        parameters=mock_policy_definition,
    )


def test_create_tenant(mock_azure: AzureCloudProvider):
    mock_azure.sdk.adal.AuthenticationContext.return_value.context.acquire_token_with_client_credentials.return_value = {
        "accessToken": "TOKEN"
    }

    mock_result = Mock()
    mock_result.json.return_value = {
        "objectId": "0a5f4926-e3ee-4f47-a6e3-8b0a30a40e3d",
        "tenantId": "60ff9d34-82bf-4f21-b565-308ef0533435",
        "userId": "1153801116406515559",
    }
    mock_result.status_code = 200
    mock_azure.sdk.requests.post.return_value = mock_result
    payload = TenantCSPPayload(
        **dict(
            creds={"username": "mock-cloud", "pass": "shh"},
            user_id="123",
            password="123",
            domain_name="123",
            first_name="john",
            last_name="doe",
            country_code="US",
            password_recovery_email_address="password@email.com",
        )
    )
    result = mock_azure.create_tenant(payload)
    print(result)
    body: TenantCSPResult = result.get("body")
    assert body.tenant_id == "60ff9d34-82bf-4f21-b565-308ef0533435"


def test_create_billing_profile(mock_azure: AzureCloudProvider):
    # mock_azure.sdk.adal.AuthenticationContext.return_value.context.acquire_token_with_client_credentials.return_value = {
    #     "accessToken": "TOKEN"
    # }

    # mock_result = Mock()
    # mock_result.headers = {
    #     "Location": "http://retry-url",
    #     "Retry-After": "10",
    # }
    # mock_result.status_code = 202
    # mock_azure.sdk.requests.post.return_value = mock_result
    payload = BillingProfileCSPPayload(
        **dict(
            address=dict(
                address_line_1="123 S Broad Street, Suite 2400",
                company_name="Promptworks",
                city="Philadelphia",
                region="PA",
                country="US",
                postal_code="19109",
            ),
            creds={"username": "mock-cloud", "pass": "shh"},
            tenant_id="60ff9d34-82bf-4f21-b565-308ef0533435",
            display_name="Test Billing Profile",
        )
    )
    result = mock_azure.create_billing_profile(payload)
    print(result)
    body: BillingProfileCreateCSPResult = result.get("body")
    assert body.retry_after == 10


def test_validate_billing_profile_creation(mock_azure: AzureCloudProvider):
    mock_azure.sdk.adal.AuthenticationContext.return_value.context.acquire_token_with_client_credentials.return_value = {
        "accessToken": "TOKEN"
    }

    mock_result = Mock()
    mock_result.status_code = 200
    mock_result.json.return_value = {
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
            "enabledAzurePlans": [],
            "hasReadAccess": True,
            "invoiceDay": 5,
            "invoiceEmailOptIn": False,
            "invoiceSections": [
                {
                    "id": "/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/billingProfiles/XC36-GRNZ-BG7-TGB/invoiceSections/6HMZ-2HLO-PJA-TGB",
                    "name": "6HMZ-2HLO-PJA-TGB",
                    "properties": {"displayName": "First Portfolio Billing Profile"},
                    "type": "Microsoft.Billing/billingAccounts/billingProfiles/invoiceSections",
                }
            ],
        },
        "type": "Microsoft.Billing/billingAccounts/billingProfiles",
    }
    mock_azure.sdk.requests.get.return_value = mock_result

    payload = BillingProfileVerifyCSPPayload(
        **dict(
            creds={
                "username": "username",
                "password": "password",
                "tenant_id": "tenant_id",
            },
            location="https://management.azure.com/providers/Microsoft.Billing/billingAccounts/7c89b735-b22b-55c0-ab5a-c624843e8bf6:de4416ce-acc6-44b1-8122-c87c4e903c91_2019-05-31/operationResults/createBillingProfile_478d5706-71f9-4a8b-8d4e-2cbaca27a668?api-version=2019-10-01-preview",
        )
    )

    result = mock_azure.validate_billing_profile_created(payload)
    body: BillingProfileCreateCSPResult = result.get("body")
    assert body.billing_profile_name == "XC36-GRNZ-BG7-TGB"
    assert (
        body.billing_profile_properties.display_name
        == "First Portfolio Billing Profile"
    )

