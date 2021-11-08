.. _server_mode:

================
Non-Python SDK's
================

Moto has a stand-alone server mode. This allows you to use Moto with any of the official AWS SDK's.

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

To use Moto in your tests, you can pass an `endpoint_url` to the SDK of your choice.

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

Examples
--------

Here are some more examples:

* `Java`_
* `Ruby`_
* `Javascript`_


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
