.. _contributing tips:

=============================
Development Tips
=============================

Below you can find some tips that might help during development.

****************************
Naming Conventions
****************************
Let's say you want to implement the `import_certificate` feature for the ACM service.

Implementing the feature itself can be done by creating a method called `import_certificate` in `moto/acm/responses.py`.
| It's considered good practice to deal with input/output formatting and validation in `responses.py`, and create a method `import_certificate` in `moto/acm/models.py` that handles the actual import logic.

When writing tests, you'll want to add a new method called `def test_import_certificate` to `tests/test_acm/test_acm.py`.
| Additional tests should also have names indicate of what's happening, i.e. `def test_import_certificate_fails_without_name`, `def test_import_existing_certificate`, etc.


****************************************
Determining which URLs to intercept
****************************************
In order for Moto to know which requests to intercept, Moto needs to know which URLs to intercept.
| But how do we know which URL's should be intercepted? There are a few ways of doing it:

 - For an existing service, copy/paste the url-path for an existing feature and cross your fingers and toes
 - Use the service model that is used by botocore: https://github.com/boto/botocore/tree/develop/botocore/data
   Look for the `requestUri`-field in the `services.json` file.
 - Make a call to AWS itself, and intercept the request using a proxy.
   This gives you all information you could need, including the URL, parameters, request and response format.


******************************
Intercepting AWS requests
******************************
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


******************************
Tagging Service
******************************

A dedicated TaggingService exists in `moto.utilities`, to help with storing/retrieving tags for resources.

Not all services use it yet, but contributors are encouraged to  use the TaggingService for all new features.

***************************
CI
***************************

Our CI runs all tests twice - one normal run, and one run in ServerMode. In ServerMode, Moto is started as a stand-alone Flask server, and all tests are run against this Flask-instance.

To verify whether your tests pass in ServerMode, you can run the following commands:

.. sourcecode:: bash

  moto_server
  TEST_SERVER_MODE=true pytest -sv tests/test_service/..


*****************************
Partial Implementations
*****************************

If a service is only partially implemented, a warning can be used to inform the user:

.. sourcecode:: python

  import warnings
  warnings.warn("The Filters-parameter is not yet implemented for client.method()")


****************
Writing tests
****************

One test should only verify a single feature/method. I.e., one test for `create_resource()`, another for `update_resource()`, etc.

Negative tests
^^^^^^^^^^^^^^^^^

When writing negative tests, try to use the following format:

.. sourcecode:: python

  with pytest.raises(botocore.exceptions.ClientError) as exc:
      client.failing_call(..)
  err = exc.value.response["Error"]
  # These assertions use the 'sure' library, but any assertion style is accepted
  err["Code"].should.equal(..)
  err["Message"].should.equal(..)

This is the best way to ensure that exceptions are dealt with correctly by Moto.


Parallel tests
^^^^^^^^^^^^^^^^^^^^^

To speed up our CI, the ServerMode tests for the `awslambda`, `batch`, `ec2` and `sqs` services will run in parallel.
This means the following:

 - Make sure you use unique names for functions/queues/etc
 - Calls to `describe_reservations()`/`list_queues()`/etc might return resources from other tests
