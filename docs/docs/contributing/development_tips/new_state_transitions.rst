.. _new state transitions:

===============================
State Transition Management
===============================

When developing a model where the resource is not available immediately, such as EC2 instances, a configuration option is available to specify whether you want mocked resources to be available immediately (to speed up unit testing), or whether you want an artificial delay to more closely mimick AWS' behaviour where resources are only available/ready after some time.

See the user-documentation here: :ref:`state transition`

In order for a new model to support this behaviour out of the box, it needs to be configured and registered with the State Manager.
The following steps need to be taken for this to be effective:

 - Extend the new model with the ManagedState-class
 - Call the ManagedState-constructor with information on which state transitions are supported
 - Decide when to advance the status
 - Register the model with the StateManager

An example model could look like this:

.. sourcecode:: python

    from moto.moto_api._internal.managed_state_model import ManagedState

    class NewModel(ManagedState):
        def __init__(self):
            ManagedState.__init__(self,
                                  # A unique name should be chosen to uniquely identify this model
                                  # Any name is acceptable - a typical format would be 'API:type'
                                  # Examples: 'S3::bucket', 'APIGateway::Method', 'DynamoDB::Table'
                                  model_name="new::model",
                                  # List all the possible status-transitions here
                                  transitions=[("initializing", "starting"),
                                               ("starting", "ready")])

        def to_json(self):
            # ManagedState gives us a 'status'-attribute out of the box
            # On the first iteration, this will be set to the first status of the first transition
            return {
                "name": ...,
                "status": self.status,
                ...
            }

    from moto.moto_api import state_manager

    class Backend():
        def __init__():
            # This is how we register the model, and specify the default transition-behaviour
            # Typically this is done when constructing the Backend-class
            state_manager.register_default_transition(
                # This name should be the same as the name used in NewModel
                model_name="new::model",
                # Any transition-config is possible - this is a good default option though
                transition={"progression": "immediate"},
            )

        def list_resources():
            for ec2_instance in all_resources:
                # For users who configured models of this type to transition manually, this is where we advance the status
                # Say the transition is registered like so: {"progression": "manual", "times": 3}
                #
                # The user calls 'list_resources' 3 times, the advance-method is called 3 times, and the state manager advances the state after the 3rd time.
                # This all happens out of the box - just make sure that the `advance()`-method is invoked when appropriate
                #
                # If the transition is set to progress immediately, this method does exactly nothing.
                #
                # If the user decides to change the progression to be time-based, where the status changed every y seconds, this method does exactly nothing.
                # It will has to be called though, for people who do have the manual progression configured
                model.advance()
            return all_models

        def describe_resource():
            resource = ...
            # Depending on the API, there may be different ways for the user to retrieve the same information
            # Make sure that each way (describe, list, get_, ) calls the advance()-method, and the resource can actually progress to the next state
            resource.advance()
            return resource
