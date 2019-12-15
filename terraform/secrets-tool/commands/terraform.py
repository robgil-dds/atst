import os
import click
import logging
import subprocess

from utils.keyvault.secrets import SecretsClient

logger = logging.getLogger(__name__)

PROCESS='terraform'

@click.group()
@click.pass_context
def terraform(ctx):
    pass

@click.command('plan')
@click.pass_context
def plan(ctx):
    keyvault = SecretsClient(vault_url="https://cloudzero-dev-keyvault.vault.azure.net/")
    # Set env variables for TF
    for secret in keyvault.list_secrets():
        name = 'TF_VAR_' + secret
        val = keyvault.get_secret(secret)
        #print(val)
        os.environ[name] = val
    env = os.environ.copy() 
    command = "{} {}".format(PROCESS, 'plan')
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, shell=True) as proc:
        for line in proc.stdout:
            logging.info(line.decode("utf-8") )

@click.command('apply')
@click.pass_context
def apply(ctx):
    keyvault = SecretsClient(vault_url="https://cloudzero-dev-keyvault.vault.azure.net/")
    # Set env variables for TF
    for secret in keyvault.list_secrets():
        name = 'TF_VAR_' + secret
        val = keyvault.get_secret(secret)
        #print(val)
        os.environ[name] = val
    env = os.environ.copy() 
    command = "{} {}".format(PROCESS, 'apply -auto-approve')
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, shell=True) as proc:
        for line in proc.stdout:
            logging.info(line.decode("utf-8") )

@click.command('destroy')
@click.pass_context
def destroy(ctx):
    keyvault = SecretsClient(vault_url="https://cloudzero-dev-keyvault.vault.azure.net/")
    # Set env variables for TF
    for secret in keyvault.list_secrets():
        name = 'TF_VAR_' + secret
        val = keyvault.get_secret(secret)
        #print(val)
        os.environ[name] = val
    env = os.environ.copy() 
    command = "{} {}".format(PROCESS, 'destroy')
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, shell=True) as proc:
        for line in proc.stdout:
            logging.info(line.decode("utf-8") )

terraform.add_command(plan)
terraform.add_command(apply)
terraform.add_command(destroy)