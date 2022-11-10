.. _server_mode:

.. role:: bash(code)
   :language: bash

.. role:: raw-html(raw)
    :format: html

================================
Non-Python SDK's / Server Mode
================================

Moto has a stand-alone server mode. This allows you to use Moto with any of the official AWS SDK's.

Installation
-------------

Install the required dependencies using:

.. code:: bash

    pip install moto[server]


You can then start it like this:

.. code:: bash

    $ moto_server

You can also pass the port:

.. code-block:: bash

    $ moto_server -p3000
     * Running on http://127.0.0.1:3000/

If you want to be able to use the server externally you can pass an IP
address to bind to as a hostname or allow any of your external
interfaces with 0.0.0.0:

.. code-block:: bash

    $ moto_server -H 0.0.0.0
     * Running on http://0.0.0.0:5000/

Please be aware this might allow other network users to access your
server.

Start within Python
--------------------
It is possible to start this server from within Python, in a separate thread.  :raw-html:`<br />`
By default, this server will start on port 5000, but this is configurable.

.. code-block:: python

    from moto.server import ThreadedMotoServer
    server = ThreadedMotoServer()
    server.start()
    # run tests
    client = boto3.client("service", endpoint_url="http://localhost:5000")
    ...
    server.stop()

Note that the ThreadedMotoServer and the decorators act on the same state, making it possible to combine the two approaches.  :raw-html:`<br />`
See the following example:

.. code-block:: python

    class TestThreadedMotoServer(unittest.TestCase):

        def setUp(self):
            self.server = ThreadedMotoServer()
            self.server.start()

        def tearDown(self):
            self.server.stop()

        @mock_s3
        def test_load_data_using_decorators(self):
            server_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
            server_client.create_bucket(Bucket="test")

            in_mem_client = boto3.client("s3")
            buckets = in_mem_client.list_buckets()["Buckets"]
            [b["Name"] for b in buckets].should.equal(["test"])

This example shows it is possible to create state using the TreadedMotoServer, and access that state using the usual decorators.  :raw-html:`<br />`
0Note that the decorators will destroy any resources on start, so make sure to not accidentally destroy any resources created by the ThreadedMotoServer that should be kept.

.. note:: The ThreadedMotoServer is considered in beta for now, and the exact interface and behaviour may still change.   :raw-html:`<br />` Please let us know if you'd like to see any changes.

Run using Docker
----------------------
You could also use the official Docker image from https://hub.docker.com/r/motoserver/moto/tags:

.. code-block:: bash

    docker run motoserver/moto:latest

Example Usage
--------------

To use Moto in your tests, pass the `endpoint_url`-parameter to the SDK of your choice.

In Python:

.. code-block:: python

    boto3.resource(
        service_name='s3',
        region_name='us-west-1',
        endpoint_url='http://localhost:5000'
    )

In Java:

.. code-block:: java

    AmazonSQS sqs = new AmazonSQSClient();
    sqs.setRegion(Region.getRegion(Regions.US_WEST_2));
    sqs.setEndpoint("http://localhost:5000");

In Scala:

.. code-block:: scala

    val region = Region.getRegion(Regions.US_WEST_2).getName
    val serviceEndpoint = "http://localhost:5000"
    val config = new AwsClientBuilder.EndpointConfiguration(serviceEndpoint, region)
    val amazonSqs =  AmazonSQSClientBuilder.standard().withEndpointConfiguration(config).build

In Terraform:

.. code-block::

    provider "aws" {
        region                      = "us-east-1"
        skip_credentials_validation = true
        skip_metadata_api_check     = true
        skip_requesting_account_id  = true
        s3_force_path_style         = true

        endpoints {
            lambda           = "http://localhost:5000"
        }
    }

See the `Terraform Docs`_ for more information.


Other languages:

* `Java`_
* `Ruby`_
* `Javascript`_


Use ServerMode using the decorators
-------------------------------------

It is possible to call the MotoServer for tests that were written using decorators.
The following environment variables can be set to achieve this:

.. code-block:: bash

    TEST_SERVER_MODE=true

Whenever a mock-decorator starts, Moto will:

 #. Send a reset-request to :bash:`http://localhost:5000`, removing all state that was kept
 #. Add the :bash:`endpoint_url` parameter to boto3, so that all requests will be made to :bash:`http://localhost:5000`.

Optionally, the `http://localhost:5000` endpoint can be overridden by:

.. code-block:: bash

    TEST_SERVER_MODE_ENDPOINT=http://moto-server:5000

This can be used for example in case of docker-compose configuration that runs Moto server
in a separate service container.

Calling the reset-API ensures the same behaviour as normal decorators, where the complete state is removed.
It is possible to keep the state in between tests, using this environment variable:

.. code-block:: bash

    MOTO_CALL_RESET_API=false


Dashboard
---------

Moto comes with a dashboard to view the current state of the system::

    http://localhost:5000/moto-api/


Reset API
---------

An internal API endpoint is provided to reset the state of all of the backends. This will remove all S3 buckets, EC2 servers, etc.::

   requests.post("http://motoapi.amazonaws.com/moto-api/reset")

Install with Homebrew
---------------------

Moto is also available to install using `Homebrew`_, which makes it much easier
to manage if you're not using Python as your primary development language.

Once Homebrew is installed, you can install Moto by running:

.. code-block:: bash

    brew install moto

To make the Moto server start up automatically when you log into your computer,
you can run:

.. code-block:: bash

    brew services start moto

Caveats
-------
The standalone server has some caveats with some services. The following services
require that you update your hosts file for your code to work properly:

#. `s3-control`

For the above services, this is required because the hostname is in the form of `AWS_ACCOUNT_ID.localhost`.
As a result, you need to add that entry to your host file for your tests to function properly.


.. _Java: https://github.com/spulec/moto/blob/master/other_langs/sqsSample.java
.. _Ruby: https://github.com/spulec/moto/blob/master/other_langs/test.rb
.. _Javascript: https://github.com/spulec/moto/blob/master/other_langs/test.js
.. _Homebrew: https://brew.sh
.. _Terraform Docs: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/guides/custom-service-endpoints
