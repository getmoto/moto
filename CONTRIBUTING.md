# Table of Contents

- [Contributing code](#contributing-code)
- [Development Guide](#development-guide)
  * [TLDR](#tldr)
  * [Linting](#linting)
- [Maintainers](#maintainers)

# Contributing code

Moto has a [Code of Conduct](https://github.com/spulec/moto/blob/master/CODE_OF_CONDUCT.md), you can expect to be treated with respect at all times when interacting with this project.

# Development Guide
Please see our documentation for information on how to contribute:
https://docs.getmoto.org/en/latest/docs/contributing

## TLDR

Moto has a [Makefile](./Makefile) which has some helpful commands for getting set up.
You should be able to run `make init` to install the dependencies and then `make test` to run the tests.

*NB. On first run, some tests might take a while to execute, especially the Lambda ones, because they may need to download a Docker image before they can execute.*

## Linting

Ensure that the correct version of black is installed (see `requirements-dev.txt`). Different versions of black will return different results.  
Run `make lint` to verify whether your code confirms to the guidelines.  
Use `make format` to automatically format your code, if it does not conform to `black`'s rules.


# Maintainers

## Releasing a new version of Moto

* Ensure the CHANGELOG document mentions the new release, and lists all significant changes.
* Go to the dedicated [Release Action](https://github.com/spulec/moto/actions/workflows/release.yml) in our CI
* Click 'Run workflow' on the top right
* Provide the version you want to release
* That's it - everything else is automated.
