# Moto - **Mo**ck Bo**to**

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

# Available Moto services:
*    S3
*    EC2
*    DynamoDB

HTTPretty is a HTTP client mock library for Python 100% inspired on ruby's [FakeWeb](http://fakeweb.rubyforge.org/).
If you come from ruby this would probably sound familiar :smiley:

#### Install

```console
pip install moto
```
