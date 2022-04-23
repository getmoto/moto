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


moto_api_backend = MotoAPIBackend()
