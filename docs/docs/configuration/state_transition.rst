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

.. warning:: Not all services will support this immediately - how to tell? List them here maybe easiest/most foolproof

There are three possibilities:
 - Status progresses immediately
 - Status progresses after calling `describe` x number of times
 - Status progresses after x seconds

.. sourcecode:: python

    from moto.moto_api import state_manager

    state_manager.set_transition(feature="support::case", transition={"progression": "time", "duration": 3})
    state_manager.set_transition(feature="support::check", transition={"progression": "immediate"})
    state_manager.set_transition(feature="dax::cluster", transition={"progression": "manual", "times": 3})


Updating this configuration can be done in ServerMode as well.

.. sourcecode:: python

    post_body = dict(feature="dax::cluster", transition={"progression": "waiter", "wait_times": 3})
    resp = requests.post("http://localhost:5000/moto-api/state-manager/set-transition", data=json.dumps(post_body))

    requests.get("http://localhost:5000/moto-api/state-manager/get-transition?feature=dax::cluster")

