.. _contributing urls:

.. role:: raw-html(raw)
    :format: html

***********************
Intercepting URLs
***********************


Determining which URLs to intercept
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for Moto to know which requests to intercept, Moto needs to know which URLs to intercept. :raw-html:`<br />` But how do we know which URL's should be intercepted? There are a few ways of doing it:

 - For an existing service, copy/paste the url-path for an existing feature and cross your fingers and toes
 - Use the service model that is used by botocore: https://github.com/boto/botocore/tree/develop/botocore/data
   Look for the `requestUri`-field in the `services.json` file.
 - Make a call to AWS itself, and intercept the request using a proxy.
   This gives you all information you could need, including the URL, parameters, request and response format.


Intercepting AWS requests
***************************

Download and install a proxy such `MITMProxy <https://mitmproxy.org/>`_.

With the proxy running, the easiest way of proxying requests to AWS is probably via the CLI.

.. sourcecode:: bash

  export HTTP_PROXY=http://localhost:8080
  export HTTPS_PROXY=http://localhost:8080
  aws ses describe-rule-set --no-verify-ssl

.. sourcecode:: python

  from botocore.config import Config
  proxy_config = Config(proxies={'http': 'localhost:8080', 'https': 'localhost:8080'})
  boto3.client("ses", config=proxy_config, use_ssl=False, verify=False)

