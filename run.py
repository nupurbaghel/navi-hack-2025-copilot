import click

from loguru import logger

import aviation_hackathon_sf.performer


@click.group()
def cli():
    pass


@cli.command()
def perform():
    performance = aviation_hackathon_sf.performer.perform_something()
    logger.info(f"Performance output: {performance}")


if __name__ == "__main__":
    cli()
