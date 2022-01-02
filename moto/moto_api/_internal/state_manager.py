DEFAULT_TRANSITION = {"progression": "immediate"}


class StateManager:

    def __init__(self):
        self._transitions = dict()

    def set_transition(self, feature, transition):
        self._transitions[feature] = transition

    def get_transition(self, feature):
        try:
            return self._transitions[feature]
        except KeyError:
            return DEFAULT_TRANSITION
