from moto.core import BaseBackend


class MotoAPIBackend(BaseBackend):
    def reset(self):
        import moto.backends as backends

        for name, backends_ in backends.loaded_backends():
            if name == "moto_api":
                continue
            for backend in backends_.values():
                backend.reset()
        self.__init__()

    def get_transition(self, model_name):
        from moto.moto_api import state_manager

        return state_manager.get_transition(model_name)

    def set_transition(self, model_name, transition):
        from moto.moto_api import state_manager

        state_manager.set_transition(model_name, transition)

    def unset_transition(self, model_name):
        from moto.moto_api import state_manager

        state_manager.unset_transition(model_name)


moto_api_backend = MotoAPIBackend()
