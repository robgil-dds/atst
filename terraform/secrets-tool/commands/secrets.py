import click
import logging
from utils.keyvault.secrets import SecretsClient
from utils.keyvault.secrets import SecretsLoader

logger = logging.getLogger(__name__)

#loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
#print(loggers)

@click.group()
@click.option('--keyvault', required=True, help="Specify the keyvault to operate on")
@click.pass_context
def secrets(ctx, keyvault):
    ctx.ensure_object(dict)
    ctx.obj['keyvault'] = keyvault

@click.command('create')
@click.option('--key', 'key', required=True, help="Key for the secret to create")
@click.option('--value', 'value', required=True, prompt=True, hide_input=True, confirmation_prompt=True, help="Value for the secret to create")
@click.pass_context
def create_secret(ctx, key, value):
    """Creates a secret in the specified KeyVault"""
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    keyvault.set_secret(key, value)

@click.command('list')
@click.pass_context
def list_secrets(ctx):
    """Lists the secrets in the specified KeyVault"""
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    click.echo(keyvault.list_secrets())

@click.command('load')
@click.option('-f', 'file', required=True, help="YAML file with secrets definitions")
@click.pass_context
def load_secrets(ctx, file):
    """Generate and load secrets from yaml definition"""
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    loader = SecretsLoader(yaml_file=file, keyvault=keyvault)
    loader.load_secrets()



secrets.add_command(create_secret)
secrets.add_command(list_secrets)
secrets.add_command(load_secrets)