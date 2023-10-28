# 🚀 Contributing to Moto

Welcome to the Moto community! We're excited to have you as part of our project. This guide will help you get started, so let's dive in! 😄

## Table of Contents

- [🚀 Contributing to Moto](#-contributing-to-moto)
- [📜 Code of Conduct](#-code-of-conduct)
- [🔧 Development Guide](#-development-guide)
  - [🚀 TL;DR](#-tldr)
  - [🧹 Linting](#-linting)
- [👩‍💻 Maintainers](#-maintainers)

## 📜 Code of Conduct

Moto has a [Code of Conduct](https://github.com/getmoto/moto/blob/master/CODE_OF_CONDUCT.md), and you can expect to be treated with respect at all times when interacting with this project.

## 🔧 Development Guide

Please see our [documentation](https://docs.getmoto.org/en/latest/docs/contributing) for information on how to contribute.

### 🚀 TL;DR

Moto has a [Makefile](./Makefile) with some helpful commands for getting set up. You can run `make init` to install the dependencies and then `make test` to run the tests.

*NB. On the first run, some tests might take a while to execute, especially the Lambda ones, because they may need to download a Docker image before they can execute.*

### 🧹 Linting

Make sure the correct version of `black` is installed (see `requirements-dev.txt`). Different versions of `black` will return different results. Run `make lint` to verify whether your code conforms to the guidelines. Use `make format` to automatically format your code if it doesn't conform to `black`'s rules.

## 👩‍💻 Maintainers

### Releasing a new version of Moto

Here's how to have some fun while releasing a new version of Moto:

1. Ensure the CHANGELOG document mentions the new release and lists all significant changes.

2. Go to the dedicated [Release Action](https://github.com/getmoto/moto/actions/workflows/release.yml) in our CI.

3. Click 'Run workflow' on the top right.

4. Provide the version you want to release.

5. That's it - everything else is automated.

Thank you for being a part of the Moto community! We can't wait to see your contributions and have a great time together! 🎉
