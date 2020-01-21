import os
import logging
import subprocess

logger = logging.getLogger(__name__)

class TFWrapper:
    """
    Command wrapper for terraform that injects secrets 
    from keyvault in to environment variables which
    can then be used by terraform
    """
    def __init__(self, keyvault: object):
        self.keyvault = keyvault
        self.env = ''
        self.terraform_path = 'terraform'

        self._set_env()

    def _set_env(self):
        # Prefix variables with TF_VAR_
        for secret in self.keyvault.list_secrets():
            name = 'TF_VAR_' + secret
            val = self.keyvault.get_secret(secret)
            os.environ[name] = val
        # Set the environment with new vars
        self.env = os.environ.copy()
        return None

    def _run_tf(self, option: str):
        try:
            command = '{} {}'.format(self.terraform_path, option)
            with subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE, shell=True) as proc:
                for line in proc.stdout:
                    logging.info(line.decode("utf-8"))
        except Exception as e:
            print(e)

    def plan(self):
        """
        terraform plan
        """
        self._run_tf(option='plan')

    def init(self):
        """
        terraform init
        """
        self._run_tf(option='init')
        
    def apply(self):
        """
        terraform apply
        """
        self._run_tf(option='apply -auto-approve')

    def destroy(self):
        """
        terraform destroy
        """
        self._run_tf(option='destroy')