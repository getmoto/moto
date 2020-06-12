.. _getting_started:

=========================
Getting Started with Moto
=========================

Installing Moto
---------------

You can use ``pip`` to install the latest released version of ``moto``::

    pip install moto

If you want to install ``moto`` from source::

    git clone git://github.com/spulec/moto.git
    cd moto
    python setup.py install

Moto usage
----------

For example, we have the following code we want to test:

.. sourcecode:: python

    import boto3

    class MyModel(object):
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def save(self):
            s3 = boto3.client('s3', region_name='us-east-1')
            s3.put_object(Bucket='mybucket', Key=self.name, Body=self.value)

There are several ways to do this, but you should keep in mind that Moto creates a full, blank environment.

Decorator
~~~~~~~~~

With a decorator wrapping, all the calls to S3 are automatically mocked out.

.. sourcecode:: python

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

        body = conn.Object('mybucket', 'steve').get()[
            'Body'].read().decode("utf-8")

        assert body == 'is awesome'

Context manager
~~~~~~~~~~~~~~~

Same as the Decorator, every call inside the ``with`` statement is mocked out.

.. sourcecode:: python

    def test_my_model_save():
        with mock_s3():
            conn = boto3.resource('s3', region_name='us-east-1')
            conn.create_bucket(Bucket='mybucket')

            model_instance = MyModel('steve', 'is awesome')
            model_instance.save()

            body = conn.Object('mybucket', 'steve').get()[
                'Body'].read().decode("utf-8")

            assert body == 'is awesome'

Raw
~~~

You can also start and stop the mocking manually.

.. sourcecode:: python

    def test_my_model_save():
        mock = mock_s3()
        mock.start()

        conn = boto3.resource('s3', region_name='us-east-1')
        conn.create_bucket(Bucket='mybucket')

        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()

        body = conn.Object('mybucket', 'steve').get()[
            'Body'].read().decode("utf-8")

        assert body == 'is awesome'

        mock.stop()

Stand-alone server mode
~~~~~~~~~~~~~~~~~~~~~~~

Moto also comes with a stand-alone server allowing you to mock out an AWS HTTP endpoint. For testing purposes, it's extremely useful even if you don't use Python.

.. sourcecode:: bash

    $ moto_server ec2 -p3000
     * Running on http://127.0.0.1:3000/

However, this method isn't encouraged if you're using ``boto``, the best solution would be to use a decorator method.
