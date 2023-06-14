# Moto - Mock AWS Services

[![Join the chat at https://gitter.im/awsmoto/Lobby](https://badges.gitter.im/awsmoto/Lobby.svg)](https://gitter.im/awsmoto/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Build Status](https://github.com/getmoto/moto/workflows/TestNDeploy/badge.svg)](https://github.com/getmoto/moto/actions)
[![Coverage Status](https://codecov.io/gh/getmoto/moto/branch/master/graph/badge.svg)](https://codecov.io/gh/getmoto/moto)
[![Docs](https://readthedocs.org/projects/pip/badge/?version=stable)](http://docs.getmoto.org)
[![PyPI](https://img.shields.io/pypi/v/moto.svg)](https://pypi.org/project/moto/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/moto.svg)](#)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/moto.svg)](https://pypistats.org/packages/moto)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Financial Contributors](https://opencollective.com/moto/tiers/badge.svg)](https://opencollective.com/moto)


## Install

```console
$ pip install 'moto[ec2,s3,all]'
```

## In a nutshell


Moto is a library that allows your tests to easily mock out AWS Services.

Imagine you have the following python code that you want to test:

```python
import boto3


class MyModel:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.put_object(Bucket="mybucket", Key=self.name, Body=self.value)
```

Take a minute to think how you would have tested that in the past.

Now see how you could test it with Moto:

```python
import boto3
from moto import mock_s3
from mymodule import MyModel


@mock_s3
def test_my_model_save():
    conn = boto3.resource("s3", region_name="us-east-1")
    # We need to create the bucket since this is all in Moto's 'virtual' AWS account
    conn.create_bucket(Bucket="mybucket")
    model_instance = MyModel("steve", "is awesome")
    model_instance.save()
    body = conn.Object("mybucket", "steve").get()["Body"].read().decode("utf-8")
    assert body == "is awesome"
```

With the decorator wrapping the test, all the calls to s3 are automatically mocked out. The mock keeps the state of the buckets and keys.

For a full list of which services and features are covered, please see our [implementation coverage](https://github.com/getmoto/moto/blob/master/IMPLEMENTATION_COVERAGE.md).


### Documentation
The full documentation can be found here:

[http://docs.getmoto.org/en/latest/](http://docs.getmoto.org/en/latest/)


### Financial Contributions
Support this project and continued development, by sponsoring us!

Click the `Sponsor`-button at the top of the page for more information.

Our finances are managed by OpenCollective, which means you have full visibility into all our contributions and expenses:
https://opencollective.com/moto

### Security contact information

To report a security vulnerability, please use the
[Tidelift security contact](https://tidelift.com/security).
Tidelift will coordinate the fix and disclosure.
