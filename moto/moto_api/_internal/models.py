from moto.core.models import BaseBackend


class MotoAPIBackend(BaseBackend):
    def reset(self):
        import moto.backends as backends

        for name, backends_ in backends.loaded_backends():
            if name == "moto_api":
                continue
            for backend in backends_.values():
                backend.reset()
        self.__init__()

    def get_transition(self, feature):
        from moto.moto_api import state_manager

        return state_manager.get_transition(feature)

    def set_transition(self, feature, transition):
        from moto.moto_api import state_manager

        state_manager.set_transition(feature, transition)

moto_api_backend = MotoAPIBackend()
