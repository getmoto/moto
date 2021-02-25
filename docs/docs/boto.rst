.. _boto:

=============
Boto vs Boto3
=============

Boto3 is the latest Python SDK, and as such the SDK targeted by Moto. All our `@mock_`-decorators should be usable against any boto3-version.

Still stuck on boto, the former SDK? Moto does have some support, in the form of our deprecated services:

.. sourcecode:: python

    from moto import mock_ec2_deprecated
    import boto

    @mock_ec2_deprecated
    def test_something_with_ec2():
        ec2_conn = boto.ec2.connect_to_region('us-east-1')
        ec2_conn.get_only_instances(instance_ids='i-123456')



When using both boto2 and boto3, one can do this to avoid confusion:

.. sourcecode:: python

    from moto import mock_ec2_deprecated as mock_ec2_b2
    from moto import mock_ec2

If you want to use Server Mode, the easiest way is to create a boto config file (`~/.boto`) with the following values:

.. code-block:: bash

    [Boto]
    is_secure = False
    https_validate_certificates = False
    proxy_port = 5000
    proxy = 127.0.0.1
