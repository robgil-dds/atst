import logging

from azure.identity import InteractiveBrowserCredential

logger = logging.getLogger(__name__)

class Auth:
    def __init__(self, vault_url, *args, **kwargs):
        self.credentials = InteractiveBrowserCredential()
        self.vault_url = vault_url