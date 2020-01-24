import logging
from azure.keyvault.keys import KeyClient
from .auth import Auth

logger = logging.getLogger(__name__)

KEY_SIZE=2048
KEY_TYPE='rsa'

class keys(Auth):
    def __init__(self, *args, **kwargs):
        super(keys, self).__init__(*args, **kwargs)
        self.key_client = KeyClient(vault_url=self.vault_url, credential=self.credentials)

    def get_key(self):
        return self.key_client

    def create_key(self):
        pass