DEFAULT_TRANSITION = {"progression": "immediate"}


class StateManager:
    def __init__(self):
        self._default_transitions = dict()
        self._transitions = dict()

    def set_default_transition(self, feature, transition):
        self._default_transitions[feature] = transition

    def set_transition(self, feature, transition):
        self._transitions[feature] = transition

    def get_transition(self, feature):
        if feature in self._transitions:
            return self._transitions[feature]
        if feature in self._default_transitions:
            return self._default_transitions[feature]
        return DEFAULT_TRANSITION
