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

To install moto for a specific service:
```console
$ pip install moto[ec2,s3]
```
This will install Moto, and the dependencies required for that specific service.  
If you don't care about the number of dependencies, or if you want to mock many AWS services:
```console
$ pip install moto[all]
```


## In a nutshell

Moto is a library that allows your tests to easily mock out AWS Services.

Imagine you have the following python code that you want to test:

```python
import boto3

class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.put_object(Bucket='mybucket', Key=self.name, Body=self.value)

```

Take a minute to think how you would have tested that in the past.

Now see how you could test it with Moto:

```python
import boto3
from moto import mock_s3
from mymodule import MyModel


@mock_s3
def test_my_model_save():
    conn = boto3.resource('s3', region_name='us-east-1')
    # We need to create the bucket since this is all in Moto's 'virtual' AWS account
    conn.create_bucket(Bucket='mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    body = conn.Object('mybucket', 'steve').get()['Body'].read().decode("utf-8")

    assert body == 'is awesome'
```

With the decorator wrapping the test, all the calls to s3 are automatically mocked out. The mock keeps the state of the buckets and keys.

It gets even better! Moto isn't just for Python code and it isn't just for S3. Look at the [standalone server mode](https://github.com/spulec/moto#stand-alone-server-mode) for more information about running Moto with other languages.  
Here's the partial list of the AWS services that currently have support:

| Service Name              | Decorator             | Comment                      |
|---------------------------|-----------------------|------------------------------|
| ACM                       | @mock_acm             |                              |
| API Gateway               | @mock_apigateway      |                              |
| Application Autoscaling   | @mock_applicationautoscaling |                       |
| Athena                    | @mock_athena          |                              |
| Autoscaling               | @mock_autoscaling     |                              |
| Cloudformation            | @mock_cloudformation  |                              |
| Cloudwatch                | @mock_cloudwatch      |                              |
| CloudwatchEvents          | @mock_events          |                              |
| Cognito Identity          | @mock_cognitoidentity |                              |
| Cognito Identity Provider | @mock_cognitoidp      |                              |
| Config                    | @mock_config          |                              |
| Data Pipeline             | @mock_datapipeline    |                              |
| DynamoDB                  | @mock_dynamodb        | API 20111205. Deprecated.    |
| DynamoDB2                 | @mock_dynamodb2       | API 20120810 (Latest)        |
| EC2                       | @mock_ec2             |                              |
| ECR                       | @mock_ecr             |                              |
| ECS                       | @mock_ecs             |                              |
| ELB                       | @mock_elb             |                              |
| ELBv2                     | @mock_elbv2           |                              |
| EMR                       | @mock_emr             |                              |
| Forecast                  | @mock_forecast        |                              |                  
| Glacier                   | @mock_glacier         |                              |
| Glue                      | @mock_glue            |                              |
| IAM                       | @mock_iam             |                              |
| IoT                       | @mock_iot             |                              |
| IoT data                  | @mock_iotdata         |                              |
| Kinesis                   | @mock_kinesis         |                              |
| KMS                       | @mock_kms             |                              |
| Lambda                    | @mock_lambda          | Invoking Lambdas requires docker |
| Logs                      | @mock_logs            |                              |
| Organizations             | @mock_organizations   |                              |
| Polly                     | @mock_polly           |                              |
| RAM                       | @mock_ram             |                              |
| RDS                       | @mock_rds             |                              |
| RDS2                      | @mock_rds2            |                              |
| Redshift                  | @mock_redshift        |                              |
| Route53                   | @mock_route53         |                              |
| S3                        | @mock_s3              |                              |
| SecretsManager            | @mock_secretsmanager  |                              |
| SES                       | @mock_ses             |                              |
| SNS                       | @mock_sns             |                              |
| SQS                       | @mock_sqs             |                              |
| SSM                       | @mock_ssm             |                              |
| Step Functions            | @mock_stepfunctions   |                              |
| STS                       | @mock_sts             |                              |
| SWF                       | @mock_swf             |                              |
| X-Ray                     | @mock_xray            |                              |

For a full list of endpoint [implementation coverage](https://github.com/spulec/moto/blob/master/IMPLEMENTATION_COVERAGE.md)

### Another Example

Imagine you have a function that you use to launch new ec2 instances:

```python
import boto3


def add_servers(ami_id, count):
    client = boto3.client('ec2', region_name='us-west-1')
    client.run_instances(ImageId=ami_id, MinCount=count, MaxCount=count)
```

To test it:

```python
from . import add_servers
from moto import mock_ec2

@mock_ec2
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    client = boto3.client('ec2', region_name='us-west-1')
    instances = client.describe_instances()['Reservations'][0]['Instances']
    assert len(instances) == 2
    instance1 = instances[0]
    assert instance1['ImageId'] == 'ami-1234abcd'
```

#### Using moto 1.0.X with boto2
moto 1.0.X mock decorators are defined for boto3 and do not work with boto2. Use the @mock_AWSSVC_deprecated to work with boto2.

Using moto with boto2
```python
from moto import mock_ec2_deprecated
import boto

@mock_ec2_deprecated
def test_something_with_ec2():
    ec2_conn = boto.ec2.connect_to_region('us-east-1')
    ec2_conn.get_only_instances(instance_ids='i-123456')

```

When using both boto2 and boto3, one can do this to avoid confusion:
```python
from moto import mock_ec2_deprecated as mock_ec2_b2
from moto import mock_ec2

```

## Usage

All of the services can be used as a decorator, context manager, or in a raw form.

### Decorator

```python
@mock_s3
def test_my_model_save():
    # Create Bucket so that test can run
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='mybucket')
    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()
    body = conn.Object('mybucket', 'steve').get()['Body'].read().decode()

    assert body == 'is awesome'
```

### Context Manager

```python
def test_my_model_save():
    with mock_s3():
        conn = boto3.resource('s3', region_name='us-east-1')
        conn.create_bucket(Bucket='mybucket')
        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()
        body = conn.Object('mybucket', 'steve').get()['Body'].read().decode()

        assert body == 'is awesome'
```


### Raw use

```python
def test_my_model_save():
    mock = mock_s3()
    mock.start()

    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    assert conn.Object('mybucket', 'steve').get()['Body'].read().decode() == 'is awesome'

    mock.stop()
```

## IAM-like Access Control

Moto also has the ability to authenticate and authorize actions, just like it's done by IAM in AWS. This functionality can be enabled by either setting the `INITIAL_NO_AUTH_ACTION_COUNT` environment variable or using the `set_initial_no_auth_action_count` decorator. Note that the current implementation is very basic, see [this file](https://github.com/spulec/moto/blob/master/moto/core/access_control.py) for more information.

### `INITIAL_NO_AUTH_ACTION_COUNT`

If this environment variable is set, moto will skip performing any authentication as many times as the variable's value, and only starts authenticating requests afterwards. If it is not set, it defaults to infinity, thus moto will never perform any authentication at all.

### `set_initial_no_auth_action_count`

This is a decorator that works similarly to the environment variable, but the settings are only valid in the function's scope. When the function returns, everything is restored.

```python
@set_initial_no_auth_action_count(4)
@mock_ec2
def test_describe_instances_allowed():
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "ec2:Describe*",
                "Resource": "*"
            }
        ]
    }
    access_key = ...
    # create access key for an IAM user/assumed role that has the policy above.
    # this part should call __exactly__ 4 AWS actions, so that authentication and authorization starts exactly after this

    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])

    # if the IAM principal whose access key is used, does not have the permission to describe instances, this will fail
    instances = client.describe_instances()['Reservations'][0]['Instances']
    assert len(instances) == 0
```

See [the related test suite](https://github.com/spulec/moto/blob/master/tests/test_core/test_auth.py) for more examples.

## Experimental: AWS Config Querying
For details about the experimental AWS Config support please see the [AWS Config readme here](CONFIG_README.md).

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

### Example on pytest usage?
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

### Example on unittest usage?

If you use [`unittest`](https://docs.python.org/3/library/unittest.html) to run tests, and you want to use `moto` inside `setUp` or `setUpClass`, you can do it with `.start()` and `.stop()` like:

```python
import unittest
from moto import mock_s3
import boto3

def func_to_test(bucket_name, key, content):
    s3 = boto3.resource('s3')
    object = s3.Object(bucket_name, key)
    object.put(Body=content)

class MyTest(unittest.TestCase):
    mock_s3 = mock_s3()
    bucket_name = 'test-bucket'
    def setUp(self):
        self.mock_s3.start()

        # you can use boto3.client('s3') if you prefer
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(self.bucket_name)
        bucket.create(
            CreateBucketConfiguration={
                'LocationConstraint': 'af-south-1'
            })

    def tearDown(self):
        self.mock_s3.stop()

    def test(self):
        content = b"abc"
        key = '/path/to/obj'

        # run the file which uploads to S3
        func_to_test(self.bucket_name, key, content)

        # check the file was uploaded as expected
        s3 = boto3.resource('s3')
        object = s3.Object(self.bucket_name, key)
        actual = object.get()['Body'].read()
        self.assertEqual(actual, content)
```

If your test `unittest.TestCase` has only one test method,
and you don't need to create AWS resources in `setUp`,
you can use the context manager (`with mock_s3():`) within that function,
or apply the decorator to that method, instead of `.start()` and `.stop()`.
That is simpler, however you then cannot share resource setup code (e.g. S3 bucket creation) between tests.

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
$ moto_server ec2
 * Running on http://127.0.0.1:5000/
```

You can also pass the port:

```console
$ moto_server ec2 -p3000
 * Running on http://127.0.0.1:3000/
```

If you want to be able to use the server externally you can pass an IP
address to bind to as a hostname or allow any of your external
interfaces with 0.0.0.0:

```console
$ moto_server ec2 -H 0.0.0.0
 * Running on http://0.0.0.0:5000/
```

Please be aware this might allow other network users to access your
server.

Then go to [localhost](http://localhost:5000/?Action=DescribeInstances) to see a list of running instances (it will be empty since you haven't added any yet).

If you want to use boto with this (using the simpler decorators above instead is strongly encouraged), the easiest way is to create a boto config file (`~/.boto`) with the following values:

```
[Boto]
is_secure = False
https_validate_certificates = False
proxy_port = 5000
proxy = 127.0.0.1
```

If you want to use boto3 with this, you can pass an `endpoint_url` to the resource

```python
boto3.resource(
    service_name='s3',
    region_name='us-west-1',
    endpoint_url='http://localhost:5000',
)
```

### Caveats
The standalone server has some caveats with some services. The following services
require that you update your hosts file for your code to work properly:

1. `s3-control`

For the above services, this is required because the hostname is in the form of `AWS_ACCOUNT_ID.localhost`.
As a result, you need to add that entry to your host file for your tests to function properly.

## Releases

Releases are done from Gitlab Actions. Fairly closely following this:
https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

- Commits to `master` branch do a dev deploy to pypi.
- Commits to a tag do a real deploy to pypi.
