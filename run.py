import click

from loguru import logger

import chassis_app.performer


@click.group()
def cli():
    pass


@cli.command()
def perform():
    performance = chassis_app.performer.perform_something()
    logger.info(f"Performance output: {performance}")


if __name__ == "__main__":
    cli()
