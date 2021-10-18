# Table of Contents

- [Contributing code](#contributing-code)
  * [Running the tests locally](#running-the-tests-locally)
  * [Linting](#linting)
  * [General notes](#general-notes)
- [Missing features](#missing-features)
- [Missing services](#missing-services)
    + [Generating template code of services.](#generating-template-code-of-services)
    + [URL Indexing](#url-indexing)
- [Maintainers](#maintainers)

# Contributing code

Moto has a [Code of Conduct](https://github.com/spulec/moto/blob/master/CODE_OF_CONDUCT.md), you can expect to be treated with respect at all times when interacting with this project.

## Running the tests locally

Moto has a [Makefile](./Makefile) which has some helpful commands for getting set up.
You should be able to run `make init` to install the dependencies and then `make test` to run the tests.

*NB. On first run, some tests might take a while to execute, especially the Lambda ones, because they may need to download a Docker image before they can execute.*

## Linting

Ensure that the correct version of black is installed - `black==19.10b0`. (Different versions of black will return different results.)  
Run `make lint` to verify whether your code confirms to the guidelines.  
Use `make format` to automatically format your code, if it does not conform to `black`'s rules.

## General notes

Some tips that might help during development:
 - A dedicated TaggingService exists in `moto.utilities`, to help with storing/retrieving tags for resources. Not all services use it yet, but contributors are encouraged to  use the TaggingService for all new features.  
 - Our CI runs all tests twice - one normal run, and one run in ServerMode. In ServerMode, Moto is started as a stand-alone Flask server, and all tests are run against this Flask-instance.
To verify whether your tests pass in ServerMode, you can run the following commands:
```
pip install .[all,server]
moto_server
TEST_SERVER_MODE=true pytest -sv tests/test_service/..
```
 - When writing tests, one test should only verify a single feature/method. I.e., one test for `create_resource()`, another for `update_resource()`, etc.
 - When writing negative tests, try to use the following format:
 ```
 with pytest.raises(botocore.exceptions.ClientError) as exc:
     client.failing_call(..)
 err = exc.value.response["Error"]
 # These assertions use the 'sure' library, but any assertion style is accepted
 err["Code"].should.equal(..)
 err["Message"].should.equal(..)
 ```
 This is the best way to ensure that exceptions are dealt with correctly by Moto.
  - If a service is only partially implemented, a warning can be used to inform the user. For instance:
  ```
  import warnings
  warnings.warn("The Filters-parameter is not yet implemented for client.method()")
  ```
  - To speed up our CI, the ServerMode tests for the `awslambda`, `batch`, `ec2` and `sqs` services will run in parallel.    
    This means the following:
      - Make sure you use unique names for functions/queues/etc
      - Calls to `describe_reservations()`/`list_queues()`/etc might return unexpected results 


# Missing features

Moto is easier to contribute to than you probably think. There's [a list of which endpoints have been implemented](https://github.com/spulec/moto/blob/master/IMPLEMENTATION_COVERAGE.md) and we invite you to add new endpoints to existing services or to add new services.

How to teach Moto to support a new AWS endpoint:

* Search for an existing [issue](https://github.com/spulec/moto/issues) that matches what you want to achieve.
* If one doesn't already exist, create a new issue describing what's missing. This is where we'll all talk about the new addition and help you get it done.
* Create a [pull request](https://help.github.com/articles/using-pull-requests/) and mention the issue # in the PR description.
* Try to add a failing test case. For example, if you're trying to implement `boto3.client('acm').import_certificate()` you'll want to add a new method called `def test_import_certificate` to `tests/test_acm/test_acm.py`.
* Implementing the feature itself can be done by creating a method called `import_certificate` in `moto/acm/responses.py`. It's considered good practice to deal with input/output formatting and validation in `responses.py`, and create a method `import_certificate` in `moto/acm/models.py` that handles the actual import logic.
* If you can also implement the code that gets that test passing then great! If not, just ask the community for a hand and somebody will assist you.

# Missing services

Implementing a new service from scratch is more work, but still quite straightforward. All the code that intercepts network requests to `*.amazonaws.com` is already handled for you in `moto/core` - all that's necessary for new services to be recognized is to create a new decorator and determine which URLs should be intercepted.

See this PR for an example of what's involved in creating a new service: https://github.com/spulec/moto/pull/4076/files

Note the `urls.py` that redirects all incoming URL requests to a generic `dispatch` method, which in turn will call the appropriate method in `responses.py`. 

If you want more control over incoming requests or their bodies, it is possible to redirect specific requests to a custom method. See this PR for an example: https://github.com/spulec/moto/pull/2957/files

### Generating template code of services.

By using `scripts/scaffold.py`, you can automatically generate template code of new services and new method of existing service. The script looks up API specification of given boto3 method and adds necessary codes including request parameters and response parameters. In some cases, it fails to generate codes.
Please try out by running `python scripts/scaffold.py`

```bash
$ python scripts/scaffold.py
Select service: codedeploy

==Current Implementation Status==
[ ] add_tags_to_on_premises_instances
...
[ ] create_deployment
...[
[ ] update_deployment_group
=================================
Select Operation: create_deployment


	Initializing service	codedeploy
	creating	moto/codedeploy
	creating	moto/codedeploy/models.py
	creating	moto/codedeploy/exceptions.py
	creating	moto/codedeploy/__init__.py
	creating	moto/codedeploy/responses.py
	creating	moto/codedeploy/urls.py
	creating	tests/test_codedeploy
	creating	tests/test_codedeploy/test_server.py
	creating	tests/test_codedeploy/test_codedeploy.py
	inserting code	moto/codedeploy/responses.py
	inserting code	moto/codedeploy/models.py
You will still need to add the mock into "__init__.py"
```

### URL Indexing
In order to speed up the performance of MotoServer, all AWS URL's that need intercepting are indexed.  
When adding/replacing any URLs in `{service}/urls.py`, please run `python scripts/update_backend_index.py` to update this index.

# Maintainers

## Releasing a new version of Moto

* Ensure the CHANGELOG document mentions the new release, and lists all significant changes.
* Go to the dedicated [Release Action](https://github.com/spulec/moto/actions/workflows/release.yml) in our CI
* Click 'Run workflow' on the top right
* Provide the version you want to release
* That's it - everything else is automated.
