# Moto - Mock Boto

# WARNING: Moto is still in active development

# In a nutshell

Moto is a library that allows your python tests to easily mock out the boto library

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

Now see how you could test it with Moto.

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

*    DynamoDB (@mock_dynamodb)
    * Table actions - core done
*    EC2 (@mock_ec2)
    * AMI - core done
    * EBS - core done
    * Instances - completed
    * Security Groups - core done
    * Tags - completed
*    S3 (@mock_s3) - core done
*    SES (@mock_ses) - core done
*    SQS (@mock_sqs) - core done

This library has been tested on boto v2.5+.

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

#### Install

```console
    $ pip install moto
```
