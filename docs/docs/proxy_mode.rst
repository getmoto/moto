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


URL Passthroughs
----------------

If some URL's should not be intercepted, you can configure the MotoProxy to pass them through.

To do so, make the following HTTP request:

.. code-block::

    config_url = "http://motoapi.amazonaws.com/moto-api/proxy/passthrough"
    proxies = {"http": "http://localhost:5005", "https": "http://localhost:5005"}

    http_url = "http://some_website.com/path"
    https_host = "google.com"
    config = {"http_urls": [http_url], "https_hosts": [https_host]}

    requests.post(config_url, json=config, proxies=proxies)

Note the difference between `http_url` and `https_hosts`. You can configure a full URL to intercept **if and only if** it is a HTTP (unsecured) url.

If you want to passthrough a request to a HTTPS endpoint, you have to specify the HTTPS host. Say you want to make a request to `https://companywebsite.com/mydata`, the `https_host` would have to be set to `companywebsite.com`.

All HTTPS requests to this domain will be intercepted.

Alternative Passthrough
-----------------------

If your test setup supports the `NO_PROXY` environment variable, you could exclude `www.thirdpartyservice.com` from being proxied by setting `NO_PROXY=www.thirdpartyservice.com`. `NO_PROXY` accepts a comma separated list of domains, e.g. `NO_PROXY=.thirdpartyservice.com,api.anotherservice.com`.
