.. _getting_started:

=========================
Getting Started with Moto
=========================

Installing Moto
---------------

You can use ``pip`` to install the latest released version of ``moto`` and specify which service(s) you will use::

    pip install 'moto[ec2,s3,..]'

This command will install Moto along with the dependencies required for the specified services.

If you want to mock many AWS services without worrying about the number of dependencies, you can use::

    pip install 'moto[all]'

To install ``moto`` from source, you can clone the repository and install it as follows::

    git clone git://github.com/getmoto/moto.git
    cd moto
    pip install '.[all]'

Moto Usage
----------

Suppose you have the following code that you want to test:

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

Using a simple decorator, all calls to AWS are automatically mocked.

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

Context Manager
~~~~~~~~~~~~~~~

The context manager works similarly to the decorator, with all calls inside the ``with`` statement being mocked.

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

You can also manually start and stop the mocking process.

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

Unittest Usage
~~~~~~~~~~~~~~

If you are using `unittest`_ to run tests and want to use `moto` inside `setUp`, you can do so with `.start()` and `.stop()`:

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

            s3 = boto3.resource("s3")
            bucket = s3.Bucket(self.bucket_name)
            bucket.create()

        def tearDown(self):
            self.mock_aws.stop()

        def test(self):
            content = b"abc"
            key = "/path/to/obj"

            # Run the file which uploads to S3
            func_to_test(self.bucket_name, key, content)

            # Check the file was uploaded as expected
            s3 = boto3.resource("s3")
            object = s3.Object(self.bucket_name, key)
            actual = object.get()["Body"].read()
            self.assertEqual(actual, content)

Class Decorator
~~~~~~~~~~~~~~~~~

You can also use decorators at the class level. This decorator will apply to every test method within the class, ensuring that state is not shared across test methods.

.. sourcecode:: python

    @mock_aws
    class TestMockClassLevel(unittest.TestCase):
        def setUp(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="mybucket")

        def test_creating_a_bucket(self):
            # 'mybucket', created in setUp, is accessible in this test
            # Other clients can be created as needed
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucket_inside")

        def test_accessing_a_bucket(self):
            # The state has been reset before this method starts
            # 'mybucket' is recreated in the setUp method
            # 'bucket_inside', however, created in another test, no longer exists
            pass

    .. note:: A tearDown method can be used to destroy any buckets/state, but this is not strictly necessary as the state is automatically reset before each test method starts.

Stand-Alone Server Mode
~~~~~~~~~~~~~~~~~~~~~~~

Moto also includes a stand-alone server that allows you to mock out the AWS HTTP endpoints. This can be useful if you are using a programming language other than Python.

To start the server, use the following command::

    $ moto_server -p 3000
    * Running on http://127.0.0.1:3000/

See :doc:`server_mode` for more information.

Recommended Usage
-----------------

There are several important caveats to consider when using Moto:

How do I avoid tests from mutating my real infrastructure?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that your mocks are properly in place, follow these guidelines:

1. Ensure that your tests have dummy environment variables set up:

   .. sourcecode:: bash

       export AWS_ACCESS_KEY_ID='testing'
       export AWS_SECRET_ACCESS_KEY='testing'
       export AWS_SECURITY_TOKEN='testing'
       export AWS_SESSION_TOKEN='testing'
       export AWS_DEFAULT_REGION='us-east-1'

2. Do not embed credentials directly in your code. This practice is always discouraged, regardless of whether you use Moto. It also makes it impossible to configure fake credentials for testing purposes.

3. **VERY IMPORTANT**: Ensure that you have your mocks set up *BEFORE* your `boto3` client is instantiated. This can often happen if you import a module that creates a `boto3` client outside of a function. Refer to :ref:`pesky_imports_section` below for strategies on how to work around this issue.

.. note:: By default, the region must be one supported by AWS. See :ref:`Can I mock the default AWS region?` for instructions on changing this.

Pytest Fixtures Example Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are a user of `pytest`_, you can leverage `pytest fixtures`_ to help set up your mocks and other AWS resources that you might need.

Here’s an example:

.. sourcecode:: python

    @pytest.fixture(scope="function")
    def aws_credentials():
        """Mocked AWS Credentials for Moto."""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture(scope="function")
    def s3(aws_credentials):
        """Return a mocked S3 client."""
        with mock_aws():
            yield boto3.client("s3", region_name="us-east-1")

    @pytest.fixture(scope="function")
    def mocked_aws(aws_credentials):
        """Mock all AWS interactions. Requires you to create your own boto3 clients."""
        with mock_aws():
            yield

    @pytest.fixture
    def create_bucket1(s3):
        s3.create_bucket(Bucket="bb1")

    @pytest.fixture
    def create_bucket2(s3):
        s3.create_bucket(Bucket="bb2")

    def test_s3_bucket_creation(s3):
        s3.create_bucket(Bucket="somebucket")
        result = s3.list_buckets()
        assert len(result["Buckets"]) == 1

    def test_s3_bucket_creation_through_fixtures(create_bucket1, create_bucket2):
        result = boto3.client("s3").list_buckets()
        assert len(result["Buckets"]) == 2

    def test_generic_aws_fixture(mocked_aws):
        s3_client = boto3.client("s3")
        s3_client.create_bucket(Bucket="somebucket")

In the example above, all of the mocked AWS fixtures (indirectly) use `aws_credentials`, which sets the proper fake environment variables. This setup is recommended to ensure that `
