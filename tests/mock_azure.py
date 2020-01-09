import pytest
from unittest.mock import Mock

from atst.domain.csp.cloud import AzureCloudProvider

AZURE_CONFIG = {
    "AZURE_CLIENT_ID": "MOCK",
    "AZURE_SECRET_KEY": "MOCK",
    "AZURE_TENANT_ID": "MOCK",
    "AZURE_POLICY_LOCATION": "policies",
}

AUTH_CREDENTIALS = {
    "client_id": AZURE_CONFIG["AZURE_CLIENT_ID"],
    "secret_key": AZURE_CONFIG["AZURE_SECRET_KEY"],
    "tenant_id": AZURE_CONFIG["AZURE_TENANT_ID"],
}


def mock_subscription():
    from azure.mgmt import subscription

    return Mock(spec=subscription)


def mock_authorization():
    from azure.mgmt import authorization

    return Mock(spec=authorization)


def mock_managementgroups():
    from azure.mgmt import managementgroups

    return Mock(spec=managementgroups)


def mock_graphrbac():
    import azure.graphrbac as graphrbac

    return Mock(spec=graphrbac)


def mock_credentials():
    import azure.common.credentials as credentials

    return Mock(spec=credentials)


def mock_policy():
    from azure.mgmt.resource import policy

    return Mock(spec=policy)


def mock_adal():
    import adal

    return Mock(spec=adal)


def mock_requests():
    import requests

    return Mock(spec=requests)


class MockAzureSDK(object):
    def __init__(self):
        from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD

        self.subscription = mock_subscription()
        self.authorization = mock_authorization()
        self.adal = mock_adal()
        self.managementgroups = mock_managementgroups()
        self.graphrbac = mock_graphrbac()
        self.credentials = mock_credentials()
        self.policy = mock_policy()
        self.requests = mock_requests()
        # may change to a JEDI cloud
        self.cloud = AZURE_PUBLIC_CLOUD


@pytest.fixture(scope="function")
def mock_azure():
    return AzureCloudProvider(AZURE_CONFIG, azure_sdk_provider=MockAzureSDK())
