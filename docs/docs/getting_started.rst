.. _getting_started:


.. role:: raw-html(raw)
    :format: html


=========================
Getting Started with Moto
=========================

Installing Moto
---------------

You can use ``pip`` to install the latest released version of ``moto``, and specify which service(s) you will use::

    pip install 'moto[ec2,s3,..]'

This will install Moto, and the dependencies required for that specific service.

If you don't care about the number of dependencies, or if you want to mock many AWS services::

    pip install 'moto[all]'

If you want to install ``moto`` from source::

    git clone git://github.com/getmoto/moto.git
    cd moto
    pip install '.[all]'


Moto usage
----------

For example, we have the following code we want to test:

.. sourcecode:: python

    import boto3

    class MyModel:
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def save(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.put_object(Bucket="mybucket", Key=self.name, Body=self.value)

There are several ways to verify that the value will be persisted successfully.

Decorator
~~~~~~~~~

With a simple decorator wrapping, all calls to AWS are automatically mocked out.

.. sourcecode:: python

    import boto3
    from moto import mock_aws
    from mymodule import MyModel

    @mock_aws
    def test_my_model_save():
        conn = boto3.resource("s3", region_name="us-east-1")
        # We need to create the bucket since this is all in Moto's 'virtual' AWS account
        conn.create_bucket(Bucket="mybucket")

        model_instance = MyModel("steve", "is awesome")
        model_instance.save()

        body = conn.Object("mybucket", "steve").get()[
            "Body"].read().decode("utf-8")

        assert body == "is awesome"

Context manager
~~~~~~~~~~~~~~~

Same as the Decorator, every call inside the ``with`` statement is mocked out.

.. sourcecode:: python

    def test_my_model_save():
        with mock_aws():
            conn = boto3.resource("s3", region_name="us-east-1")
            conn.create_bucket(Bucket="mybucket")

            model_instance = MyModel("steve", "is awesome")
            model_instance.save()

            body = conn.Object("mybucket", "steve").get()[
                "Body"].read().decode("utf-8")

            assert body == "is awesome"

Raw
~~~

You can also start and stop the mocking manually.

.. sourcecode:: python

    def test_my_model_save():
        mock = mock_aws()
        mock.start()

        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="mybucket")

        model_instance = MyModel("steve", "is awesome")
        model_instance.save()

        body = conn.Object("mybucket", "steve").get()[
            "Body"].read().decode("utf-8")

        assert body == "is awesome"

        mock.stop()

Unittest usage
~~~~~~~~~~~~~~

If you use `unittest`_ to run tests, and you want to use `moto` inside `setUp`, you can do it with `.start()` and `.stop()` like:

.. sourcecode:: python

    import unittest
    from moto import mock_aws
    import boto3

    def func_to_test(bucket_name, key, content):
        s3 = boto3.resource("s3")
        object = s3.Object(bucket_name, key)
        object.put(Body=content)

    class MyTest(unittest.TestCase):

        bucket_name = "test-bucket"
        def setUp(self):
            self.mock_aws = mock_aws()
            self.mock_aws.start()

            # you can use boto3.client("s3") if you prefer
            s3 = boto3.resource("s3")
            bucket = s3.Bucket(self.bucket_name)
            bucket.create()

        def tearDown(self):
            self.mock_aws.stop()

        def test(self):
            content = b"abc"
            key = "/path/to/obj"

            # run the file which uploads to S3
            func_to_test(self.bucket_name, key, content)

            # check the file was uploaded as expected
            s3 = boto3.resource("s3")
            object = s3.Object(self.bucket_name, key)
            actual = object.get()["Body"].read()
            self.assertEqual(actual, content)

Class Decorator
~~~~~~~~~~~~~~~~~

It is also possible to use decorators on the class-level.

The decorator is effective for every test-method inside your class. State is not shared across test-methods.

.. sourcecode:: python

    @mock_aws
    class TestMockClassLevel(unittest.TestCase):
        def setUp(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="mybucket")

        def test_creating_a_bucket(self):
            # 'mybucket', created in setUp, is accessible in this test
            # Other clients can be created at will

            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucket_inside")

        def test_accessing_a_bucket(self):
            # The state has been reset before this method has started
            # 'mybucket' is recreated as part of the setUp-method
            # 'bucket_inside' however, created inside the other test, no longer exists
            pass

.. note:: A tearDown-method can be used to destroy any buckets/state, but because state is automatically destroyed before a test-method start, this is not strictly necessary.

Stand-alone server mode
~~~~~~~~~~~~~~~~~~~~~~~

Moto also comes with a stand-alone server allowing you to mock out the AWS HTTP endpoints. This is useful if you are using any other language than Python.

.. sourcecode:: bash

    $ moto_server -p3000
     * Running on http://127.0.0.1:3000/

See :doc:`server_mode` for more information.

Recommended Usage
-----------------
There are some important caveats to be aware of when using moto:

How do I avoid tests from mutating my real infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You need to ensure that the mocks are actually in place.

 #. Ensure that your tests have dummy environment variables set up:

    .. sourcecode:: bash

        export AWS_ACCESS_KEY_ID='testing'
        export AWS_SECRET_ACCESS_KEY='testing'
        export AWS_SECURITY_TOKEN='testing'
        export AWS_SESSION_TOKEN='testing'
        export AWS_DEFAULT_REGION='us-east-1'

 #. Do not embed credentials directly in your code. This is always considered bad practice, regardless of whether you use Moto. It also makes it impossible to configure fake credentials for testing purposes.


 #. **VERY IMPORTANT**: ensure that you have your mocks set up *BEFORE* your `boto3` client is established.
    This can typically happen if you import a module that has a `boto3` client instantiated outside of a function.
    See :ref:`pesky_imports_section` below on how to work around this.

.. note:: By default, the region must be one supported by AWS, see :ref:`Can I mock the default AWS region?` for how to change this.

Example on usage
~~~~~~~~~~~~~~~~
If you are a user of `pytest`_, you can leverage `pytest fixtures`_ to help set up your mocks and other AWS resources that you would need.

Here is an example:

.. sourcecode:: python

    @pytest.fixture(scope="function")
    def aws_credentials():
        """Mocked AWS Credentials for moto."""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture(scope="function")
    def aws(aws_credentials):
        with mock_aws():
            yield boto3.client("s3", region_name="us-east-1")

    @pytest.fixture
    def create_bucket1(aws):
        boto3.client("s3").create_bucket(Bucket="bb1")

    @pytest.fixture
    def create_bucket2(aws):
        boto3.client("s3").create_bucket(Bucket="bb2")

    def test_s3_directly(aws):
        s3.create_bucket(Bucket="somebucket")

        result = s3.list_buckets()
        assert len(result["Buckets"]) == 1

    def test_bucket_creation(create_bucket1, create_bucket2):
        result = boto3.client("s3").list_buckets()
        assert len(result["Buckets"]) == 2


In the code sample above, all of the AWS/mocked fixtures take in a parameter of `aws_credentials`,
which sets the proper fake environment variables. The fake environment variables are used so that `botocore` doesn't try to locate real
credentials on your system.

With Moto activated within the fixture, we can pass it to a test-method to ensure that any other AWS-calls are also mocked inside that test method.
We can also combine multiple fixtures that use the same Moto-fixture.

Moto will delete any data after the mock ends, so the state is not shared across methods.


.. _pesky_imports_section:

What about those pesky imports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
As mentioned earlier, mocks should be established *BEFORE* the clients are set up.

Some background on why this is necessary:  :raw-html:`<br />`
Moto intercepts HTTP requests using a custom event handler that hooks into botocore's event-system.  :raw-html:`<br />`
When creating clients/resources, `boto3` gathers all event handlers that have been registered at that point, and injects those handlers into the created client/resource. Event handlers registered after a client is created, are not used.

The `moto.core`-package registers our event handler on initialization. So to be pedantic: `moto.core` should be imported before a client is created, in order for `boto3` to call our custom handler and therefore for Moto to be active.  :raw-html:`<br />`
The easiest way to ensure this happens, is to establish a mock before the clients are setup, as `moto.core` is imported when the mock starts.


One way to avoid import issues is to make use of local Python imports -- i.e. import the module that creates boto3-clients inside of the unit test you want to run.

Example:

.. sourcecode:: python

    def test_something(aws):
        # aws is a fixture defined above that yields a boto3 s3 client.
        
        from some.package.that.does.something.with.s3 import some_func # <-- Local import for unit test
        # ^^ Importing here ensures that the mock has been established.

        some_func()  # The mock has been established from the "s3" pytest fixture, so this function that uses
                     # a package-level S3 client will properly use the mock and not reach out to AWS.

Patching the client or resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If it is not possible to rearrange imports, we can patch the boto3-client or resource after the mock has started. See the following code sample:

.. sourcecode:: python

    # The client can come from an import, an __init__-file, wherever..
    outside_client = boto3.client("s3")
    s3 = boto3.resource("s3")

    @mock_aws
    def test_mock_works_with_client_or_resource_created_outside():
        from moto.core import patch_client, patch_resource
        patch_client(outside_client)
        patch_resource(s3)

        assert outside_client.list_buckets()["Buckets"] == []

        assert list(s3.buckets.all()) == []

This will ensure that the boto3 requests are still mocked.

Other caveats
~~~~~~~~~~~~~
For Tox, Travis CI, Github Actions, and other build systems, you might need to also create fake AWS credentials. The following command will create the required file with some bogus-credentials:

.. sourcecode:: bash

    mkdir ~/.aws && touch ~/.aws/credentials && echo -e "[default]\naws_access_key_id = test\naws_secret_access_key = test" > ~/.aws/credentials

.. _unittest: https://docs.python.org/3/library/unittest.html
.. _pytest: https://pytest.org/en/latest/
.. _pytest fixtures: https://pytest.org/en/latest/fixture.html#fixture
