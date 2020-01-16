import click
import logging

from utils.keyvault.secrets import SecretsClient
from utils.terraform.wrapper import TFWrapper

logger = logging.getLogger(__name__)

PROCESS='terraform'

@click.group()
@click.option('--keyvault', required=True, help="Specify the keyvault to operate on")
@click.pass_context
def terraform(ctx, keyvault):
    ctx.ensure_object(dict)
    ctx.obj['keyvault'] = keyvault

@click.command('plan')
@click.pass_context
def plan(ctx):
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    tf = TFWrapper(keyvault)
    tf.plan()

@click.command('apply')
@click.pass_context
def apply(ctx):
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    tf = TFWrapper(keyvault)
    tf.apply()

@click.command('destroy')
@click.pass_context
def destroy(ctx):
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    tf = TFWrapper(keyvault)
    tf.destroy()

@click.command('init')
@click.pass_context
def init(ctx):
    keyvault = SecretsClient(vault_url=ctx.obj['keyvault'])
    tf = TFWrapper(keyvault)
    tf.init()

terraform.add_command(plan)
terraform.add_command(apply)
terraform.add_command(destroy)
terraform.add_command(init)