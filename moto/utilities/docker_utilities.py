import docker
import functools
import requests.adapters


_orig_adapter_send = requests.adapters.HTTPAdapter.send


class DockerModel:
    def __init__(self):
        self.__docker_client = None

    @property
    def docker_client(self):
        if self.__docker_client is None:
            # We should only initiate the Docker Client at runtime.
            # The docker.from_env() call will fall if Docker is not running
            self.__docker_client = docker.from_env()

            # Unfortunately mocking replaces this method w/o fallback enabled, so we
            # need to replace it if we detect it's been mocked
            if requests.adapters.HTTPAdapter.send != _orig_adapter_send:
                _orig_get_adapter = self.docker_client.api.get_adapter

                def replace_adapter_send(*args, **kwargs):
                    adapter = _orig_get_adapter(*args, **kwargs)

                    if isinstance(adapter, requests.adapters.HTTPAdapter):
                        adapter.send = functools.partial(_orig_adapter_send, adapter)
                    return adapter

                self.docker_client.api.get_adapter = replace_adapter_send
        return self.__docker_client
