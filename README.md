# Moto - Mock AWS Services

[![Join the chat at https://gitter.im/awsmoto/Lobby](https://badges.gitter.im/awsmoto/Lobby.svg)](https://gitter.im/awsmoto/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Build Status](https://github.com/spulec/moto/workflows/TestNDeploy/badge.svg)](https://github.com/spulec/moto/actions)
[![Coverage Status](https://codecov.io/gh/spulec/moto/branch/master/graph/badge.svg)](https://codecov.io/gh/spulec/moto)
[![Docs](https://readthedocs.org/projects/pip/badge/?version=stable)](http://docs.getmoto.org)
[![PyPI](https://img.shields.io/pypi/v/moto.svg)](https://pypi.org/project/moto/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/moto.svg)](#)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/moto.svg)](https://pypistats.org/packages/moto)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Install

```console
$ pip install moto[ec2,s3,all]
```

## In a nutshell

```python
import boto3
from moto import mock_ec2


def add_servers(ami_id, count):
    client = boto3.client('ec2', region_name='us-west-1')
    client.run_instances(ImageId=ami_id, MinCount=count, MaxCount=count)


@mock_ec2
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    client = boto3.client('ec2', region_name='us-west-1')
    instances = client.describe_instances()['Reservations'][0]['Instances']
    assert len(instances) == 2
    instance1 = instances[0]
    assert instance1['ImageId'] == 'ami-1234abcd'
```



## Very Important -- Recommended Usage
There are some important caveats to be aware of when using moto:

*Failure to follow these guidelines could result in your tests mutating your __REAL__ infrastructure!*

### How do I avoid tests from mutating my real infrastructure?
You need to ensure that the mocks are actually in place. Changes made to recent versions of `botocore`
have altered some of the mock behavior. In short, you need to ensure that you _always_ do the following:

1. Ensure that your tests have dummy environment variables set up:

        export AWS_ACCESS_KEY_ID='testing'
        export AWS_SECRET_ACCESS_KEY='testing'
        export AWS_SECURITY_TOKEN='testing'
        export AWS_SESSION_TOKEN='testing'

1. __VERY IMPORTANT__: ensure that you have your mocks set up __BEFORE__ your `boto3` client is established.
   This can typically happen if you import a module that has a `boto3` client instantiated outside of a function.
   See the pesky imports section below on how to work around this.

### Example on usage?
If you are a user of [pytest](https://pytest.org/en/latest/), you can leverage [pytest fixtures](https://pytest.org/en/latest/fixture.html#fixture)
to help set up your mocks and other AWS resources that you would need.

Here is an example:
```python
@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client('s3', region_name='us-east-1')


@pytest.fixture(scope='function')
def sts(aws_credentials):
    with mock_sts():
        yield boto3.client('sts', region_name='us-east-1')


@pytest.fixture(scope='function')
def cloudwatch(aws_credentials):
    with mock_cloudwatch():
        yield boto3.client('cloudwatch', region_name='us-east-1')

... etc.
```

In the code sample above, all of the AWS/mocked fixtures take in a parameter of `aws_credentials`,
which sets the proper fake environment variables. The fake environment variables are used so that `botocore` doesn't try to locate real
credentials on your system.

Next, once you need to do anything with the mocked AWS environment, do something like:
```python
def test_create_bucket(s3):
    # s3 is a fixture defined above that yields a boto3 s3 client.
    # Feel free to instantiate another boto3 S3 client -- Keep note of the region though.
    s3.create_bucket(Bucket="somebucket")

    result = s3.list_buckets()
    assert len(result['Buckets']) == 1
    assert result['Buckets'][0]['Name'] == 'somebucket'
```

### What about those pesky imports?
Recall earlier, it was mentioned that mocks should be established __BEFORE__ the clients are set up. One way
to avoid import issues is to make use of local Python imports -- i.e. import the module inside of the unit
test you want to run vs. importing at the top of the file.

Example:
```python
def test_something(s3):
   from some.package.that.does.something.with.s3 import some_func # <-- Local import for unit test
   # ^^ Importing here ensures that the mock has been established.      

   some_func()  # The mock has been established from the "s3" pytest fixture, so this function that uses
                # a package-level S3 client will properly use the mock and not reach out to AWS.
```

### Other caveats
For Tox, Travis CI, and other build systems, you might need to also perform a `touch ~/.aws/credentials`
command before running the tests. As long as that file is present (empty preferably) and the environment
variables above are set, you should be good to go.

## Stand-alone Server Mode

Moto also has a stand-alone server mode. This allows you to utilize
the backend structure of Moto even if you don't use Python.

It uses flask, which isn't a default dependency. You can install the
server 'extra' package with:

```python
pip install "moto[server]"
```

You can then start it running a service:

```console
$ moto_server
 * Running on http://127.0.0.1:5000/
```


## Releases

Releases are done from Gitlab Actions. Fairly closely following this:
https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

- Commits to `master` branch do a dev deploy to pypi.
- Commits to a tag do a real deploy to pypi.
