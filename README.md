# Moto - Mock Boto

[![Build Status](https://travis-ci.org/spulec/moto.png?branch=master)](https://travis-ci.org/spulec/moto)

# WARNING: Moto is still in active development

# In a nutshell

Moto is a library that allows your python tests to easily mock out the boto library.

Imagine you have the following code that you want to test:

```python
import boto
from boto.s3.key import Key

class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        conn = boto.connect_s3()
        bucket = conn.get_bucket('mybucket')
        k = Key(bucket)
        k.key = self.name
        k.set_contents_from_string(self.value)
```

Take a minute to think how you would have tested that in the past.

Now see how you could test it with Moto:

```python
import boto
from moto import mock_s3
from mymodule import MyModel

@mock_s3
def test_my_model_save():
    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn = boto.connect_s3()
    assert conn.get_bucket('mybucket').get_key('steve') == 'is awesome'
```

With the decorator wrapping the test, all the calls to s3 are automatically mocked out. The mock keeps the state of the buckets and keys.

It gets even better! Moto isn't just S3. Here's the status of the other AWS services implemented.

```gherkin
|---------------------------------------------------------------------------|
| Service Name          | Decorator      | Development Status               |
|---------------------------------------------------------------------------|
| DynamoDB              | @mock_dynamodb | Table actions core done          |
|---------------------------------------------------------------------------|
| EC2                   | @mock_ec2      | core done                        |
|     - AMI             |                | core done                        |
|     - EBS             |                | core done                        |
|     - Instances       |                | completed                        |
|     - Security Groups |                | core done                        |
|     - Tags            |                | completed                        |
|---------------------------------------------------------------------------|
| S3                    | @mock_s3       | core done                        |
|---------------------------------------------------------------------------|
| SES                   | @mock_ses      | core done                        |
|---------------------------------------------------------------------------|
| SQS                   | @mock_sqs      | core done                        |
|---------------------------------------------------------------------------|
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
    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn = boto.connect_s3()
    assert conn.get_bucket('mybucket').get_key('steve') == 'is awesome'
```

### Context Manager

```python
def test_my_model_save():
    with mock_s3():
        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()

        conn = boto.connect_s3()
        assert conn.get_bucket('mybucket').get_key('steve') == 'is awesome'
```


### Raw use

```python
def test_my_model_save():
    mock = mock_s3()
    mock.start()

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn = boto.connect_s3()
    assert conn.get_bucket('mybucket').get_key('steve') == 'is awesome'

    mock.stop()
```

## Stand-alone Server Mode

Moto also comes with a stand-alone server mode. This allows you to utilize the backend structure of Moto even if you don't use Python.

To run a service:

```console
$ moto_server ec2
 * Running on http://127.0.0.1:5000/
```

Then go to [localhost](http://localhost:5000/?Action=DescribeInstances) to see a list of running instances (it will be empty since you haven't added any yet).

## Install

```console
$ pip install moto
```

This library has been tested on boto v2.5+.


## Thanks

A huge thanks to [Gabriel Falcão](https://github.com/gabrielfalcao) and his [HTTPretty](https://github.com/gabrielfalcao/HTTPretty) library. Moto would not exist without it.
