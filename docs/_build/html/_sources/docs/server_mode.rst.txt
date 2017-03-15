.. _server_mode:

===========
Server mode
===========

Moto has a stand-alone server mode. This allows you to utilize
the backend structure of Moto even if you don't use Python.

It uses flask, which isn't a default dependency. You can install the
server 'extra' package with:

.. code:: bash

    pip install moto[server]


You can then start it running a service:

.. code:: bash

    $ moto_server ec2

You can also pass the port:

.. code-block:: bash

    $ moto_server ec2 -p3000
     * Running on http://127.0.0.1:3000/

If you want to be able to use the server externally you can pass an IP
address to bind to as a hostname or allow any of your external
interfaces with 0.0.0.0:

.. code-block:: bash

    $ moto_server ec2 -H 0.0.0.0
     * Running on http://0.0.0.0:5000/

Please be aware this might allow other network users to access your
server.

Then go to localhost_ to see a list of running instances (it will be empty since you haven't added any yet).

If you want to use boto3 with this, you can pass an `endpoint_url` to the resource

.. code-block:: python

    boto3.resource(
        service_name='s3',
        region_name='us-west-1',
        endpoint_url='http://localhost:5000',
    )

Other languages
---------------

You don't need to use Python to use Moto; it can be used with any language. Here are some examples to run it with other languages:

* `Java`_
* `Ruby`_
* `Javascript`_

.. _Java: https://github.com/spulec/moto/blob/master/other_langs/sqsSample.java
.. _Ruby: https://github.com/spulec/moto/blob/master/other_langs/test.rb
.. _Javascript: https://github.com/spulec/moto/blob/master/other_langs/test.js
.. _localhost: http://localhost:5000/?Action=DescribeInstances
