.. _state transition:

.. role:: raw-html(raw)
    :format: html

=============================
State Transitions
=============================

When developing against AWS, many API calls are asynchronous. Many resources will take some time to complete, and you'll need to write business logic to ensure the application can deal with all possible states. What is the desired behaviour when the status is `initializing`? What should happen when the status is finally `ready`? What should happen when the resource is still not `ready` after an hour?

Let's look at an example. Say you want to create a DAX cluster, and wait until it's available - or throw an error if this takes too long.

.. sourcecode:: python

    def create_and_wait_for_cluster(name):
        client.create_cluster(ClusterName=name, ...)

        cluster_status = get_cluster_status(name)
        while cluster_status != "available":
            sleep()

            if five_minutes_have_passed():
                error()

            cluster_status = get_cluster_status(name)

Because Moto handles everything in-memory, and no actual servers are created, there is no need to wait until the cluster is ready - it could be ready immediately.  :raw-html:`<br />`
Not having to wait for a resource to be ready is of course the major benefit of using Moto, but it also means that the entire example above is impossible to test.

Moto exposes an API that can artificially delay these state transitions, allowing you to let Moto resemble the asynchronous nature of AWS as closely as you need.

Sticking with the example above, you may want to test what happens if the cluster takes 5 seconds to create:

.. sourcecode:: python

    from moto.moto_api import state_manager

    state_manager.set_transition(model_name="dax::cluster", transition={"progression": "time", "duration": 5})

    create_and_wait_for_cluster("my_new_cluster")

In order to test what happens in the event of a timeout, we can order the cluster to only be ready after 10 minutes:

.. sourcecode:: python

    from moto.moto_api import state_manager

    state_manager.set_transition(model_name="dax::cluster", transition={"progression": "time", "duration": 600})

    try:
        create_and_wait_for_cluster("my_new_cluster")
    except:
        verify_the_correct_error_was_thrown()

In other tests, you may simply want the cluster to be ready as quickly as possible:

.. sourcecode:: python

    from moto.moto_api import state_manager

    state_manager.set_transition(model_name="dax::cluster", transition={"progression": "immediate"})


So far we've seen two possible transitions:
 - The state progresses immediately
 - The state progresses after x seconds

There is a third possibility, where the state progresses after calling `describe_object` a specific number of times.  :raw-html:`<br />`
This can be useful if you want to verify that the state does change, but you don't want your unit test to take too long.

.. note::
    We will use the `boto3.client(..).describe_object` method as an example throughout this page.  :raw-html:`<br />`
    This should be seen as a agnostic version of service-specific methods to verify the status of a resource, such as `boto.client("dax").describe_clusters()` or `boto.client("support").describe_cases()`.

Changing the state after a certain number of invocations can be done like this:

.. sourcecode:: python

    state_manager.set_transition(model_name="dax::cluster", transition={"progression": "manual", "times": 3})

The transition is called `manual` because it requires you to manually invoke the `describe_object`-method before the status is progressed.  :raw-html:`<br />`
To show how this would work in practice, let's look at an example test:

.. sourcecode:: python

    client.create_cluster(ClusterName=name, ...)
    # The first time we retrieve the status
    status = client.describe_clusters(ClusterNames=[name])["Clusters"][0]["Status"]
    assert status == "creating"
    # Second time we retrieve the status
    status = client.describe_clusters(ClusterNames=[name])["Clusters"][0]["Status"]
    assert status == "creating"
    # This is the third time that we're retrieving the status - this time it will advance to the next status
    status = client.describe_clusters(ClusterNames=[name])["Clusters"][0]["Status"]
    assert status == "available"

This should be done cleanly in a while-loop of-course, similar to the `create_and_wait_for_cluster` defined above - but this is a good way to showcase the behaviour.


Registered models
########################

:doc:`A list of all supported models can be found here. <models>`

Older versions of Moto may not support all models that are listed here.  :raw-html:`<br />`
To see a list of supported models for your Moto-version, call the `get_registered_models`-method:

.. sourcecode:: python

    with mock_all():
        print(state_manager.get_registered_models())

Note the `mock_all`-decorator! Models are registered when the mock for that resource is started. If you call this method outside of a mock, you may see an empty list.

If you'd like to see state transition support for a resource that's not yet supported, feel free to open an issue or PR.


State Transitions in ServerMode
########################################

Configuration state transitions can be done in ServerMode as well, by making a HTTP request to the MotoAPI.
This is an example request for `dax::cluster` to wait 5 seconds before the cluster becomes ready:

.. sourcecode:: python

    post_body = dict(model_name="dax::cluster", transition={"progression": "time", "duration": 5})
    resp = requests.post("http://localhost:5000/moto-api/state-manager/set-transition", data=json.dumps(post_body))

An example request to see the currently configured transition for a specific model:

.. sourcecode:: python

    requests.get("http://localhost:5000/moto-api/state-manager/get-transition?model_name=dax::cluster")


We will not list all configuration options here again, but all models and transitions types (as specified above) follow the same format.

Reset
########

It is possible to reset the state manager, and undo any custom transitions that were set.  :raw-html:`<br />`
Using Python:

.. sourcecode:: python

    from moto.moto_api import state_manager

    state_manager.unset_transition(model_name="dax::cluster")

Or if you're using Moto in ServerMode:

.. sourcecode:: python

    post_body = dict(model_name="dax::cluster")
    resp = requests.post("http://localhost:5000/moto-api/state-manager/unset-transition", data=json.dumps(post_body))
