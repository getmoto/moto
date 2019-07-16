### Contributing code

Moto has a [Code of Conduct](https://github.com/spulec/moto/blob/master/CODE_OF_CONDUCT.md), you can expect to be treated with respect at all times when interacting with this project.

## Feature Requests

Because of the large number of feature requests for new services/endpoints that are opened against Moto, we handle triaging of issues slightly differently than most projects. Feature requests should be submitted in the [issue tracker](https://github.com/spulec/moto/issues), with a description of the expected behavior & use case, where they’ll remain closed until sufficient interest, measured by 👍 reactions, has been [shown by the community](https://github.com/spulec/moto/issues?utf8=%E2%9C%93&q=label%3A%22enhancement%22+sort%3Areactions-%2B1-desc+). Before submitting a request, please search for similar ones in the [closed issues](https://github.com/spulec/moto/issues?q=is%3Aissue+is%3Aclosed+label%3Aenhancement).

This means that all feature request issues opened will be closed as above. Issues that will not be closed include bugs, questions, and cleanup.

Moto has a philosophy of accepting partial features (a half-implemented endpoint is better than nothing). As a result, we consider many things feature requests that one might think of as bugs in a different library. We have a strict definition of bugs limited to regressions. These will be marked as bugs and will be prioritized over features.

## Running the tests locally

Moto has a Makefile which has some helpful commands for getting setup. You should be able to run `make init` to install the dependencies and then `make test` to run the tests.

## Is there a missing feature?

Moto is easier to contribute to than you probably think. There's [a list of which endpoints have been implemented](https://github.com/spulec/moto/blob/master/IMPLEMENTATION_COVERAGE.md) and we invite you to add new endpoints to existing services or to add new services.

How to teach Moto to support a new AWS endpoint:

* Create an issue describing what's missing. This is where we'll all talk about the new addition and help you get it done.
* Create a [pull request](https://help.github.com/articles/using-pull-requests/) and mention the issue # in the PR description.
* Try to add a failing test case. For example, if you're trying to implement `boto3.client('acm').import_certificate()` you'll want to add a new method called `def test_import_certificate` to `tests/test_acm/test_acm.py`.
* If you can also implement the code that gets that test passing that's great. If not, just ask the community for a hand and somebody will assist you.

# Maintainers

## Releasing a new version of Moto

You'll need a PyPi account and a Dockerhub account to release Moto. After we release a new PyPi package we build and push the [motoserver/moto](https://hub.docker.com/r/motoserver/moto/) Docker image.

* First, `scripts/bump_version` modifies the version and opens a PR
* Then, merge the new pull request
* Finally, generate and ship the new artifacts with `make publish`

