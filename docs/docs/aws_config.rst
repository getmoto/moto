.. _aws_config:


AWS Config Support
##################

An experimental feature for AWS Config has been developed to provide AWS Config capabilities in your unit tests.
This feature is experimental as there are many services that are not yet supported and will require the community to add them in
over time. This page details how the feature works and how you can use it.

What is this and why would I use this?
**************************************

AWS Config is an AWS service that describes your AWS resource types and can track their changes over time. At this time, moto does not
have support for handling the configuration history changes, but it does have a few methods mocked out that can be immensely useful
for unit testing.

If you are developing automation that needs to pull against AWS Config, then this will help you write tests that can simulate your
code in production.

How does this work?
*******************

The AWS Config capabilities in moto work by examining the state of resources that are created within moto, and then returning that data
in the way that AWS Config would return it (sans history). This will work by querying all of the moto backends (regions) for a given
resource type.

However, this will only work on resource types that have this enabled.

Current enabled resource types
===============================

#. S3 (all)
#. IAM (Role, Policy)

Developer Guide
***************

There are several pieces to this for adding new capabilities to moto:

#. Listing resources
#. Describing resources

For both, there are a number of pre-requisites:

Base Components
===============

In the `moto/core/models.py` file is a class named `ConfigQueryModel`. This is a base class that keeps track of all the
resource type backends.

At a minimum, resource types that have this enabled will have:

#. A `config.py` file that will import the resource type backends (from the `__init__.py`)
#. In the resource's `config.py`, an implementation of the `ConfigQueryModel` class with logic unique to the resource type
#. An instantiation of the `ConfigQueryModel`
#. In the `moto/config/models.py` file, import the `ConfigQueryModel` instantiation, and update `RESOURCE_MAP` to have a mapping of the AWS Config resource type to the instantiation on the previous step (just imported).

An example of the above is implemented for S3. You can see that by looking at:

#. `moto/s3/config.py`
#. `moto/config/models.py`

Testing
=======

For each resource type, you will need to test write tests for a few separate areas:

- Test the backend queries to ensure discovered resources come back (ie for `IAM::Policy`, write `tests.tests_iam.test_policy_list_config_discovered_resources`). For writing these tests, you must not make use of `boto` to create resources. You will need to use the backend model methods to provision the resources. This is to make tests compatible with the moto server. You must make tests for the resource type to test listing and object fetching.

- Test the config dict for all scenarios (ie for `IAM::Policy`, write `tests.tests_iam.test_policy_config_dict`). For writing this test, you'll need to create resources in the same way as the first test (without using `boto`), in every meaningful configuration that would produce a different config dict. Then, query the backend and ensure each of the dicts are as you expect.

- Test that everything works end to end with the `boto` clients. (ie for `IAM::Policy`, write `tests.tests_iam.test_policy_config_client`). The main two items to test will be the `boto.client('config').list_discovered_resources()`, `boto.client('config').list_aggregate_discovered_resources()`, `moto.client('config').batch_get_resource_config()`, and `moto.client('config').batch_aggregate_get_resource_config()`. This test doesn't have to be super thorough, but it basically tests that the front end and backend logic all works together and returns correct resources. Beware the aggregate methods all have capital first letters (ie `Limit`), while non-aggregate methods have lowercase first letters (ie `limit`)

Listing
=======

S3 is currently the model implementation, but it also odd in that S3 is a global resource type with regional resource residency.

But for most resource types the following is true:

#. There are regional backends with their own sets of data
#. Config aggregation can pull data from any backend region -- we assume that everything lives in the same account

Implementing the listing capability will be different for each resource type. At a minimum, you will need to return a `List` of `Dict` that look like this:

.. sourcecode:: python

 [
    {
        'type': 'AWS::The AWS Config data type',
        'name': 'The name of the resource',
        'id': 'The ID of the resource',
        'region': 'The region of the resource -- if global, then you may want to have the calling logic pass in the
                   aggregator region in for the resource region -- or just us-east-1 :P'
    }
    , ...
 ]


It's recommended to read the comment for the `ConfigQueryModel`'s `list_config_service_resources` function in [base class here](moto/core/models.py).

^^ The AWS Config code will see this and format it correct for both aggregated and non-aggregated calls.

General implementation tips
===========================
The aggregation and non-aggregation querying can and should just use the same overall logic. The differences are:

1. Non-aggregated listing will specify the region-name of the resource backend `backend_region`
1. Aggregated listing will need to be able to list resource types across ALL backends and filter optionally by passing in `resource_region`.

An example of a working implementation of this is `S3 <https://github.com/spulec/moto/blob/master/moto/s3/config.py>`_.

Pagination should generally be able to pull out the resource across any region so should be sharded by `region-item-name` -- not done for S3
because S3 has a globally unique name space.

Describing Resources
====================

Fetching a resource's configuration has some similarities to listing resources, but it requires more work (to implement). Due to the
various ways that a resource can be configured, some work will need to be done to ensure that the Config dict returned is correct.

For most resource types the following is true:

1. There are regional backends with their own sets of data
1. Config aggregation can pull data from any backend region -- we assume that everything lives in the same account

The current implementation is for S3. S3 is very complex and depending on how the bucket is configured will depend on what Config will
return for it.

When implementing resource config fetching, you will need to return at a minimum `None` if the resource is not found, or a `dict` that looks
like what AWS Config would return.

It's recommended to read the comment for the `ConfigQueryModel` 's `get_config_resource` function in `the base class <https://github.com/spulec/moto/blob/master/moto/core/models.py>`_.