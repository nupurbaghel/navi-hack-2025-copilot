Python Template
===============

This repository is a template for Python projects and acts as a starting point for new projects.
You can use this template to create a new Python project with the following features:

- `poetry` for dependency/requirements management and virtual environment setup
- `pytest` configuration for testing
- `black` configuration for linting
- `click` for command line interface
- `loguru` for logging setup at different levels
- `Dockerfile` and `docker-compose` setup for containerization
- `Makefile` with common tasks

Installation
------------

To create a new project using this template, run the following command:

```bash
export APP_NAME=my-new-app
git clone --recursive https://github.com/ylogx/python-chassis.git ${APP_NAME} && cd ${APP_NAME} && bin/new-project
```

This will clone the repository and setup code for your new specified App Name.
This will install dependencies and setup a virtual environment for the project.
You can use `poetry` commands to manage dependencies and virtual environment.

Here's how the installation looks like:

![Installation Screenshot](https://i.imgur.com/npEvTcu.png)

Run
---

To run the project, use the following command:

```bash
make lint test # Perform linting and test
make run
```

You can find more useful commands in the `Makefile`.
