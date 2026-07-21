import click
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.command.worker_command import WorkerCommand

@click.group()
def cli() -> None:
    """CLI root command group."""
    pass

# Initialize container and add commands
container = DefaultContainer.getInstance()
worker_cmd = container.get(WorkerCommand)
cli.add_command(worker_cmd.to_click_command())

if __name__ == "__main__":
    cli()
