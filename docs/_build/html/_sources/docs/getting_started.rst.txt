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

For example we have the following code we want to test:

.. sourcecode:: python

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

There are several method to do this, just keep in mind Moto creates a full blank environment.

Decorator
~~~~~~~~~

With a decorator wrapping all the calls to S3 are automatically mocked out.

.. sourcecode:: python

    import boto
    from moto import mock_s3
    from mymodule import MyModel

    @mock_s3
    def test_my_model_save():
        conn = boto.connect_s3()
        # We need to create the bucket since this is all in Moto's 'virtual' AWS account
        conn.create_bucket('mybucket')

        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()

        assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'

Context manager
~~~~~~~~~~~~~~~

Same as decorator, every call inside ``with`` statement are mocked out.

.. sourcecode:: python

    def test_my_model_save():
        with mock_s3():
            conn = boto.connect_s3()
            conn.create_bucket('mybucket')

            model_instance = MyModel('steve', 'is awesome')
            model_instance.save()

            assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'

Raw
~~~

You can also start and stop manually the mocking.

.. sourcecode:: python

    def test_my_model_save():
        mock = mock_s3()
        mock.start()

        conn = boto.connect_s3()
        conn.create_bucket('mybucket')

        model_instance = MyModel('steve', 'is awesome')
        model_instance.save()

        assert conn.get_bucket('mybucket').get_key('steve').get_contents_as_string() == 'is awesome'

        mock.stop()

Stand-alone server mode
~~~~~~~~~~~~~~~~~~~~~~~

Moto comes with a stand-alone server allowing you to mock out an AWS HTTP endpoint. It is very useful to test even if you don't use Python.

.. sourcecode:: bash

    $ moto_server ec2 -p3000
     * Running on http://127.0.0.1:3000/

This method isn't encouraged if you're using ``boto``, best is to use decorator method.
