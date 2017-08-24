# Moto - Mock AWS Services

[![Join the chat at https://gitter.im/awsmoto/Lobby](https://badges.gitter.im/awsmoto/Lobby.svg)](https://gitter.im/awsmoto/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

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
| ELBv2                 | @mock_elbv2      | core endpoints done               |
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
| SSM                   | @mock_ssm        | core endpoints done               |
|------------------------------------------------------------------------------|
| STS                   | @mock_sts        | core endpoints done               |
|------------------------------------------------------------------------------|
| SWF                   | @mock_swf        | basic endpoints done              |
|------------------------------------------------------------------------------|
```

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
moto 1.0.X mock docorators are defined for boto3 and do not work with boto2. Use the @mock_AWSSVC_deprecated to work with boto2.

Using moto with boto2
```python
from moto import mock_ec2_deprecated
import boto
