.. _releases:

.. role:: bash(code)
   :language: bash

.. role:: raw-html(raw)
    :format: html

================================
Releases and Upgrade Paths
================================


Release Schedule
------------------

There is no fixed release schedule, although we try to release a new version every 1 or 2 weeks.

Specific release intervals will be influenced by 1) high-priority bugs, 2) number of new features and 3) maintainer availability.


Development Releases
----------------------

Every commit should result in a development release, marked as `Pre-releases in PyPi <https://pypi.org/project/moto/#history>`_ and with the `latest`-tag `in DockerHub <https://hub.docker.com/r/motoserver/moto/tags>`_.

Note that old development releases will be periodically deleted. There is a limit on how much disk space we can use on PyPi, and we've already hit that limit in the past because of the large number of dev releases we do - deleting old development releases is the only way to keep disk usage under control.


Versioning scheme
----------------------

Moto follows a `semver` scheme: `major.minor.patch`.
 - A major releases indicates a breaking change
 - A minor release indicates a big change, but nothing breaking
 - A patch release will contain new features and bug fixes


Breaking Changes
-----------------

A full list of all changes in a specific release can be found on Github: https://github.com/getmoto/moto/blob/master/CHANGELOG.md

A overview of the breaking changes between major versions:

For Moto 2.x:
 - A change in the installation method. Use `pip install moto[service]` to only install the required dependencies for that service, or `pip install moto[all]` to install all (1.x behaviour)

For Moto 3.x:
 - Removed compatibility with `boto`. Specifically: all `service_deprecated`-decorators were removed.
 - The class-decorator now resets the state before every test-method (before, the state was global - shared between class-methods).
 - ECS ARN's now use the new (long) format by default

For Moto 4.x:
 - Removed decorators `mock_dynamodb2` and `mock_rds2` (they were functionally equivalent with `mock_dynamodb` and `mock_rds` since 3.x)

For Moto 5.x:
 - All decorators have been replaced with `mock_aws`
 - The `batch_simple` decorator has been replaced with: `@mock_aws(config={"batch": {"use_docker": False}})`
 - The `awslambda_simple` decorator has been replaced with: `@mock_aws(config={"lambda": {"use_docker": False}})`
 - AWS IAM managed Policies are no longer loaded by default. To load them set `@mock_aws(config={"iam": {"load_aws_managed_policies": True}})` or set environment variable `MOTO_IAM_LOAD_MANAGED_POLICIES=true`
 - When starting the MotoServer, the `service`-argument (i.e.: `motoserver s3`) is no longer supported. A single MotoServer-instance can be used for all AWS-services.
