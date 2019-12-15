import logging
from .auth import Auth
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

class SecretsClient(Auth):
    def __init__(self, *args, **kwargs):
        super(SecretsClient, self).__init__(*args, **kwargs)
        self.secret_client = SecretClient(vault_url=self.vault_url, credential=self.credentials)

    def get_secret(self, key):
        secret = self.secret_client.get_secret(key)
        return secret.value

    def set_secret(self, key: str, value: str):
        secret = self.secret_client.set_secret(key, value)
        logger.debug('Set value for key: {}'.format(key))
        return secret

    def list_secrets(self):
        secrets = list()
        secret_properties = self.secret_client.list_properties_of_secrets()
        for secret in secret_properties:
            secrets.append(secret.name)
        return secrets