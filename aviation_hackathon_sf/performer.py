import random

from loguru import logger


def perform_something():
    logger.debug("Performing something")

    noise = value_generator(add_noise=True)
    logger.info(f"Noise is {noise}.")

    return ["Everything everywhere all at once.", noise]


def value_generator(add_noise: bool = False) -> float:
    noise = random.random() if add_noise else 0.0
    logger.debug(f"Current noise value: {noise}")
    return 42.0 + noise
