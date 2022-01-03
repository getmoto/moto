.. _state transition:

.. role:: raw-html(raw)
    :format: html

=============================
State Transitions
=============================

When developing against AWS, many API calls are asynchronous. For example, an EC2 instance that was just spun up, will not be available immediately.  :raw-html:`<br />`
To account for this, a lot of business logic has to be written to ensure the application handles all possible states, like `initializing`, `starting`, `ready`, etc.

Because Moto handles all calls in-memory, and no actual servers are created, there is no need to wait until a server is 'ready' - it will be available immediately.
This is obviously the major benefit of using Moto, but it also means that the logic around state transitions cannot be tested.  :raw-html:`<br />`

Moto exposes an API that can artificially delay state transitions, to help you test this logic anyway.

.. warning:: Not all services will support this immediately - how to tell? List them here maybe easiest/most foolproof? Or expose an api that lists them all

There are three possibilities:
 - Status progresses immediately
 - Status progresses after calling `describe` x number of times
 - Status progresses after x seconds

.. sourcecode:: python

    from moto.moto_api import state_manager

    # The progression can be automatic, where the status progresses after a number of seconds
    state_manager.set_transition(feature="support::case", transition={"progression": "time", "duration": 3})
    # TODO: Do we need this? How would this work?
    state_manager.set_transition(feature="support::check", transition={"progression": "immediate"})
    # TODO: naming?
    # The state progresses after the appropriate `describe_` or `list_`-function for this feature has been called a number of times.
    state_manager.set_transition(feature="dax::cluster", transition={"progression": "manual", "times": 3})


Updating this configuration can be done in ServerMode as well.

.. sourcecode:: python

    post_body = dict(feature="dax::cluster", transition={"progression": "waiter", "wait_times": 3})
    resp = requests.post("http://localhost:5000/moto-api/state-manager/set-transition", data=json.dumps(post_body))

    requests.get("http://localhost:5000/moto-api/state-manager/get-transition?feature=dax::cluster")


Reset
########

It is possible to reset the transition to the default progression, how Moto behaves without any customization.

.. sourcecode:: python

    from moto.moto_api import state_manager

    # TODO: IMPLEMENT
    state_manager.unset_transition(feature="dax::cluster")

    # Or in ServerMode
    # TODO: IMPLEMENT
    post_body = dict(feature="dax::cluster")
    resp = requests.post("http://localhost:5000/moto-api/state-manager/unset-transition", data=json.dumps(post_body))
