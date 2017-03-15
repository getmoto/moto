# Moto - Mock AWS Services

[![Build Status](https://travis-ci.org/spulec/moto.png?branch=master)](https://travis-ci.org/spulec/moto)
[![Coverage Status](https://coveralls.io/repos/spulec/moto/badge.png?branch=master)](https://coveralls.io/r/spulec/moto)
[![Docs](https://readthedocs.org/projects/pip/badge/?version=stable)](http://docs.getmoto.org)

# In a nutshell

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

    assert body == b'is awesome'
```

With the decorator wrapping the test, all the calls to s3 are automatically mocked out. The mock keeps the state of the buckets and keys.

It gets even better! Moto isn't just for Python code and it isn't just for S3. Look at the [standalone server mode](https://github.com/spulec/moto#stand-alone-server-mode) for more information about running Moto with other languages. Here's the status of the other AWS services implemented:

```gherkin
|------------------------------------------------------------------------------|
| Service Name          | Decorator        | Development Status                |
|------------------------------------------------------------------------------|
| API Gateway           | @mock_apigateway | core endpoints done               |
|------------------------------------------------------------------------------|
| Autoscaling           | @mock_autoscaling| core endpoints done               |
|------------------------------------------------------------------------------|
| Cloudformation        | @mock_cloudformation| core endpoints done            |
|------------------------------------------------------------------------------|
| Cloudwatch            | @mock_cloudwatch | basic endpoints done              |
|------------------------------------------------------------------------------|
| Data Pipeline         | @mock_datapipeline| basic endpoints done             |
|------------------------------------------------------------------------------|
| DynamoDB              | @mock_dynamodb   | core endpoints done               |
| DynamoDB2             | @mock_dynamodb2  | core endpoints + partial indexes  |
|------------------------------------------------------------------------------|
| EC2                   | @mock_ec2        | core endpoints done               |
|     - AMI             |                  | core endpoints done               |
|     - EBS             |                  | core endpoints done               |
|     - Instances       |                  | all  endpoints done               |
|     - Security Groups |                  | core endpoints done               |
|     - Tags            |                  | all  endpoints done               |
|------------------------------------------------------------------------------|
| ECS                   | @mock_ecs        | basic endpoints done              |
|------------------------------------------------------------------------------|
| ELB                   | @mock_elb        | core endpoints done               |
|------------------------------------------------------------------------------|
| EMR                   | @mock_emr        | core endpoints done               |
|------------------------------------------------------------------------------|
| Glacier               | @mock_glacier    | core endpoints done               |
|------------------------------------------------------------------------------|
| IAM                   | @mock_iam        | core endpoints done               |
|------------------------------------------------------------------------------|
| Lambda                | @mock_lambda     | basic endpoints done              |
|------------------------------------------------------------------------------|
| Kinesis               | @mock_kinesis    | core endpoints done               |
|------------------------------------------------------------------------------|
| KMS                   | @mock_kms        | basic endpoints done              |
|------------------------------------------------------------------------------|
| RDS                   | @mock_rds        | core endpoints done               |
|------------------------------------------------------------------------------|
| RDS2                  | @mock_rds2       | core endpoints done               |
|------------------------------------------------------------------------------|
| Redshift              | @mock_redshift   | core endpoints done               |
|------------------------------------------------------------------------------|
| Route53               | @mock_route53    | core endpoints done               |
|------------------------------------------------------------------------------|
| S3                    | @mock_s3         | core endpoints done               |
|------------------------------------------------------------------------------|
| SES                   | @mock_ses        | core endpoints done               |
|------------------------------------------------------------------------------|
| SNS                   | @mock_sns        | core endpoints done               |
|------------------------------------------------------------------------------|
| SQS                   | @mock_sqs        | core endpoints done               |
|------------------------------------------------------------------------------|
| STS                   | @mock_sts        | core endpoints done               |
|------------------------------------------------------------------------------|
| SWF                   | @mock_sfw        | basic endpoints done              |
|------------------------------------------------------------------------------|
```

### Another Example

Imagine you have a function that you use to launch new ec2 instances:

```python
import boto

def add_servers(ami_id, count):
    conn = boto.connect_ec2('the_key', 'the_secret')
    for index in range(count):
        conn.run_instances(ami_id)
```

To test it:

```python
from . import add_servers

@mock_ec2
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    conn = boto.connect_ec2('the_key', 'the_secret')
    reservations = conn.get_all_instances()
    assert len(reservations) == 2
    instance1 = reservations[0].instances[0]
    assert instance1.image_id == 'ami-1234abcd'
```

## Usage

All of the services can be used as a decorator, context manager, or in a raw form.

### Decorator

```python
@mock_s3
def test_my_model_save():
    conn = boto.connect_s3()
    conn.create_bucket('mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'
```

### Context Manager

```python
def test_my_model_save():
    with mock_s3():
        conn = boto.connect_s3()
        conn.create_bucket('mybucket')

        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()

        assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'
```


### Raw use

```python
def test_my_model_save():
    mock = mock_s3()
    mock.start()

    conn = boto.connect_s3()
    conn.create_bucket('mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'

    mock.stop()
```

## Stand-alone Server Mode

Moto also has a stand-alone server mode. This allows you to utilize
the backend structure of Moto even if you don't use Python.

It uses flask, which isn't a default dependency. You can install the
server 'extra' package with:

```python
pip install moto[server]
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

## Install

```console
$ pip install moto
```
