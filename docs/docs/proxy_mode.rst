.. _proxy_mode:

.. role:: bash(code)
   :language: bash

.. role:: raw-html(raw)
    :format: html

================================
Proxy Mode
================================

Moto can be run as a proxy, intercepting all requests to AWS and mocking them instead.  :raw-html:`<br />`
Some of the benefits:

 - Easy to configure for all SDK's
 - Can be reached by Lambda containers, allowing you to mock service-calls inside a Lambda-function


Installation
-------------

Install the required dependencies using:

.. code:: bash

    pip install moto[proxy]


You can then start the proxy like this:

.. code:: bash

    $ pip install moto[proxy]
    $ moto_proxy

Note that, if you want your Lambda functions to reach this proxy, you need to open up the moto_proxy:

.. code:: bash

    $ moto_proxy -H 0.0.0.0

.. warning:: Be careful not to use this on a public network - this allows all network users access to your server.


Quick usage
--------------
The help command shows a quick-guide on how to configure SDK's to  use the proxy.
.. code-block:: bash

    $ moto_proxy --help


Extended Configuration
------------------------

To use the MotoProxy while running your tests, the AWS SDK needs to know two things:

 - The proxy endpoint
 - How to deal with SSL

To set the proxy endpoint, use the `HTTPS_PROXY`-environment variable.

Because the proxy does not have an approved SSL certificate, the SDK will not trust the proxy by default. This means that the SDK has to be configured to either

1. Accept the proxy's custom certificate, by setting the `AWS_CA_BUNDLE`-environment variable
2. Allow unverified SSL certificates

The `AWS_CA_BUNDLE` needs to point to the location of the CA certificate that comes with Moto.  :raw-html:`<br />`
You can run `moto_proxy --help` to get the exact location of this certificate, depending on where Moto is installed.

Environment Variables Configuration:
-------------------------------------

.. code-block:: bash

    export HTTPS_PROXY=http://localhost:5005
    aws cloudformation list-stacks --no-verify-ssl

Or by configuring the AWS_CA_BUNDLE:

.. code-block:: bash

    export HTTPS_PROXY=http://localhost:5005
    export AWS_CA_BUNDLE=/location/of/moto/ca/cert.crt
    aws cloudformation list-stacks


Python Configuration
--------------------------

If you're already using Moto's `mock_service`-decorators, you can use a custom environment variable that configures everything automatically:

.. code-block:: bash

    TEST_PROXY_MODE=true pytest

To configure this manually:

.. code-block:: python

    from botocore.config import Config

    config = Config(proxies={"https": "http://localhost:5005"})
    client = boto3.client("s3", config=config, verify=False)


Terraform Configuration
------------------------------

.. code-block::

    provider "aws" {
        region                      = "us-east-1"
        http_proxy                  = "http://localhost:5005"
        custom_ca_bundle            = "/location/of/moto/ca/cert.crt"
        # OR
        insecure                    = true
    }


Drawbacks
------------

Configuring a proxy means that all requests are intercepted, but the MotoProxy can only handle requests to AWS.

If your test includes a call to `https://www.thirdpartyservice.com`, that will also be intercepted by `MotoProxy` - and subsequently throw an error because it doesn't know how to handle non-AWS requests.

You can exclude `www.thirdpartyservice.com` from being proxied by setting `NO_PROXY=www.thirdpartyservice.com` to work around. `NO_PROXY` accepts a comma separated list of domains, e.g. `NO_PROXY=.thirdpartyservice.com,api.anotherservice.com`.
