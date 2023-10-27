from ..awslambda.models import (
    lambda_backends,
    BaseBackend,
    LambdaBackend,
)
from ..core import BackendDict
from moto import settings
import datetime
from os import getenv
from time import sleep
from typing import Any, Dict, List, Tuple, Optional


class LambdaSimpleBackend(BaseBackend):
    """
    Implements a Lambda-Backend that does not use Docker containers. Submitted Jobs are marked as Success by default.

    Set the environment variable MOTO_SIMPLE_BATCH_FAIL_AFTER=0 to fail jobs immediately, or set this variable to a positive integer to control after how many seconds the job fails.

    Annotate your tests with `@mock_batch_simple`-decorator to use this Batch-implementation.
    """

    @property
    def backend(self) -> LambdaBackend:
        return lambda_backends[self.account_id][self.region_name]

    def __getattribute__(self, name: str) -> Any:
        """
        Magic part that makes this class behave like a wrapper around the regular batch_backend
        We intercept calls to `submit_job` and replace this with our own (non-Docker) implementation
        Every other method call is send through to batch_backend
        """
        if name in [
            "backend",
            "account_id",
            "region_name",
            "urls",
            "_url_module",
            "__class__",
            "url_bases",
        ]:
            return object.__getattribute__(self, name)
        if name in ["_invoke_lambda", ]:

            def newfunc(*args: Any, **kwargs: Any) -> Any:
                attr = object.__getattribute__(self, name)
                return attr(*args, **kwargs)

            return newfunc
        else:
            return object.__getattribute__(self.backend, name)

    def _invoke_lambda(self, event: Optional[str] = None) -> Tuple[str, bool, str]:
        # Create the LogGroup if necessary, to write the result to
        self.logs_backend.ensure_log_group(self.logs_group_name)
        # TODO: context not yet implemented
        if event is None:
            event = dict()  # type: ignore[assignment]
        output = None

            env_vars = {
                "_HANDLER": self.handler,
                "AWS_EXECUTION_ENV": f"AWS_Lambda_{self.run_time}",
                "AWS_LAMBDA_FUNCTION_TIMEOUT": self.timeout,
                "AWS_LAMBDA_FUNCTION_NAME": self.function_name,
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": self.memory_size,
                "AWS_LAMBDA_FUNCTION_VERSION": self.version,
                "AWS_REGION": self.region,
                "AWS_ACCESS_KEY_ID": "role-account-id",
                "AWS_SECRET_ACCESS_KEY": "role-secret-key",
                "AWS_SESSION_TOKEN": "session-token",
            }

            env_vars.update(self.environment_vars)
            env_vars["MOTO_HOST"] = settings.moto_server_host()
            moto_port = settings.moto_server_port()
            env_vars["MOTO_PORT"] = moto_port
            env_vars["MOTO_HTTP_ENDPOINT"] = f'{env_vars["MOTO_HOST"]}:{moto_port}'

            if settings.test_proxy_mode():
                env_vars["HTTPS_PROXY"] = env_vars["MOTO_HTTP_ENDPOINT"]
                env_vars["AWS_CA_BUNDLE"] = "/var/task/ca.crt"

            invocation_error = False
            return "Happy lambda response", invocation_error, "Lambda logs say it's a-ok"
            # log_config = docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)

        #     with _DockerDataVolumeContext(
        #             self
        #     ) as data_vol, _DockerDataVolumeLayerContext(self) as layer_context:
        #         try:
        #             run_kwargs: Dict[str, Any] = dict()
        #             network_name = settings.moto_network_name()
        #             network_mode = settings.moto_network_mode()
        #             if network_name:
        #                 run_kwargs["network"] = network_name
        #             elif network_mode:
        #                 run_kwargs["network_mode"] = network_mode
        #             elif settings.TEST_SERVER_MODE:
        #                 # AWSLambda can make HTTP requests to a Docker container called 'motoserver'
        #                 # Only works if our Docker-container is named 'motoserver'
        #                 # TODO: should remove this and rely on 'network_mode' instead, as this is too tightly coupled with our own test setup
        #                 run_kwargs["links"] = {"motoserver": "motoserver"}
        #
        #             # add host.docker.internal host on linux to emulate Mac + Windows behavior
        #             #   for communication with other mock AWS services running on localhost
        #             if platform == "linux" or platform == "linux2":
        #                 run_kwargs["extra_hosts"] = {
        #                     "host.docker.internal": "host-gateway"
        #                 }
        #
        #             # The requested image can be found in one of a few repos:
        #             # - User-provided repo
        #             # - mlupin/docker-lambda (the repo with up-to-date AWSLambda images
        #             # - lambci/lambda (the repo with older/outdated AWSLambda images
        #             #
        #             # We'll cycle through all of them - when we find the repo that contains our image, we use it
        #             image_repos = set(
        #                 [
        #                     settings.moto_lambda_image(),
        #                     "mlupin/docker-lambda",
        #                     "lambci/lambda",
        #                 ]
        #             )
        #             for image_repo in image_repos:
        #                 image_ref = f"{image_repo}:{self.run_time}"
        #                 try:
        #                     self.ensure_image_exists(image_ref)
        #                     break
        #                 except docker.errors.NotFound:
        #                     pass
        #             volumes = {
        #                 data_vol.name: {"bind": "/var/task", "mode": "rw"},
        #                 layer_context.name: {"bind": "/opt", "mode": "rw"},
        #             }
        #             container = self.docker_client.containers.run(
        #                 image_ref,
        #                 [self.handler, json.dumps(event)],
        #                 remove=False,
        #                 mem_limit=f"{self.memory_size}m",
        #                 volumes=volumes,
        #                 environment=env_vars,
        #                 detach=True,
        #                 log_config=log_config,
        #                 **run_kwargs,
        #             )
        #         finally:
        #             if container:
        #                 try:
        #                     exit_code = container.wait(timeout=300)["StatusCode"]
        #                 except requests.exceptions.ReadTimeout:
        #                     exit_code = -1
        #                     container.stop()
        #                     container.kill()
        #
        #                 output = container.logs(stdout=False, stderr=True)
        #                 output += container.logs(stdout=True, stderr=False)
        #                 container.remove()
        #
        #     output = output.decode("utf-8")  # type: ignore[union-attr]
        #
        #     self.save_logs(output)
        #
        #     # We only care about the response from the lambda
        #     # Which is the last line of the output, according to https://github.com/lambci/docker-lambda/issues/25
        #     resp = output.splitlines()[-1]
        #     logs = os.linesep.join(
        #         [line for line in self.convert(output).splitlines()[:-1]]
        #     )
        #     invocation_error = exit_code != 0
        #     return resp, invocation_error, logs
        # except docker.errors.DockerException as e:
        #     # Docker itself is probably not running - there will be no Lambda-logs to handle
        #     msg = f"error running docker: {e}"
        #     logger.error(msg)
        #     self.save_logs(msg)
        #     return msg, True, ""


lambda_simple_backends = BackendDict(LambdaSimpleBackend, "lambda")
