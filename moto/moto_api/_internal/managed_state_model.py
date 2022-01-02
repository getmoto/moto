from moto.moto_api import state_manager


class ManagedState:
    """
    Subclass this class to configure state-transitions
    """

    def __init__(self, model_name, transitions):
        # Indicate the possible transitions for this model
        # Example: [(initializing,queued), (queued, starting), (starting, ready)]
        self._transitions = transitions
        # Current status of this model. Implementations should call `status`
        # The initial status is assumed to be the first transition
        self._status, _ = transitions[0]
        # Internal counter that keeps track of how often this model has been described
        # Used for transition-type=manual
        self._tick = 0
        # Name of this model. This will be used in the API
        self.model_name = model_name

    def advance(self):
        self._tick += 1

    @property
    def status(self):
        """
        Transitions the status as appropriate before returning
        """
        transition_config = state_manager.get_transition(self.model_name)
        target_status = self._get_next_status(previous=self._status)
        if transition_config["progression"] == "manual":
            if self._tick >= transition_config["times"]:
                self._status = target_status
                self._tick = 0

        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def _get_next_status(self, previous):
        return next((nxt for prev, nxt in self._transitions if previous == prev), previous)
