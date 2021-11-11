.. _contributing architecture:

=============================
Architecture
=============================

If you're interested in the inner workings of Moto, or are trying to hunt down some tricky bug, the below sections will help you learn more about how Moto works.

**************************
Decorator Architecture
**************************
When using decorators, Moto works by intercepting the HTTP request that is send out by boto3.
This has multiple benefits:

 - boto3 keeps the responsibility of any initial parameter validation
 - boto3 keeps the responsibility of any post-processing of the response
 - Other SDK's can also be used against Moto, as all SDK's  use the HTTP API to talk to AWS in the end.

Botocore utilizes an event-based architecture. Events such as `creating-client-class` and `before-send` are emitted for all boto3-requests.

When the decorator starts, Moto registers a hook into the `before-send`-event that allows us to intercept the HTTP-request that was about to be send.
For every intercepted request, Moto figures out which service/feature is called based on the HTTP request prepared by `boto3`, and calls our own stub instead.


***********************************************
Determining which service/feature is called
***********************************************
There are multiple ways for Moto to determine which request was called.
For each request we need to know two things:

 #. Which service is this request for?
 #. Which feature is called?

When using one ore more decorators, Moto will load all urls from `{service}/urls.py::url_bases`.
Incoming requests are matched against those to figure out which service the request has to go to.
After that, we try to find right feature by looking at:

 #. The `Action`-parameter in the querystring or body, or
 #. The `x-amz-target`-header, or
 #. The full URI. Boto3 has a model for each service that maps the HTTP method and URI to a feature.
    Note that this only works if the `Responses`-class has an attribute `SERVICE_NAME`, as Moto needs to know which boto3-client has this model.

When using Moto in ServerMode, all incoming requests will be made to `http://localhost`, or wherever the MotoServer is hosted, so we can no longer use the request URI to figure out which service to talk to.
In order to still know which service the request was intended for, Moto will check:

 #. The authorization header first (`HTTP_AUTHORIZATION`)
 #. The target header next (`HTTP_X_AMZ_TARGET`)
 #. Or the path header (`PATH_INFO`)
 #. If all else fails, we assume S3 as the default

Now that we have determined the service, we can rebuild the original host this request was send to.
With the combination of the restored host and path we can match against the `url_bases` and `url_paths` in `{service}/urls.py` to determine which Moto-method is responsible for handling the incoming request.


***********************************
File Architecture
***********************************
To keep a logical separation between services, each one is located into a separate folder.
Each service follows the same file structure.

The below table explains the purpose of each file:

+---------------+---------------------------------------------------------------------------------------------------------------+
| File          | Responsibility                                                                                                |
+===============+===============================================================================================================+
| __init__.py   | Initializes the decorator to be used by developers                                                            |
+---------------+---------------------------------------------------------------------------------------------------------------+
| urls.py       | List of the URL's that should be intercepted                                                                  |
+---------------+---------------------------------------------------------------------------------------------------------------+
| responses.py  | Requests are redirected here first. Responsible for extracting parameters and determining the response format |
+---------------+---------------------------------------------------------------------------------------------------------------+
| models.py     | Responsible for the data storage and logic required.                                                          |
+---------------+---------------------------------------------------------------------------------------------------------------+
| exceptions.py | Not required - this would contain any custom exceptions, if your code throws any                              |
+---------------+---------------------------------------------------------------------------------------------------------------+
