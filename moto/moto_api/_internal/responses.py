import json

from moto import settings
from moto.core.responses import ActionAuthenticatorMixin, BaseResponse


class MotoAPIResponse(BaseResponse):
    def reset_response(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        if request.method == "POST":
            from .models import moto_api_backend

            moto_api_backend.reset()
            return 200, {}, json.dumps({"status": "ok"})
        return 400, {}, json.dumps({"Error": "Need to POST to reset Moto"})

    def reset_auth_response(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        if request.method == "POST":
            previous_initial_no_auth_action_count = (
                settings.INITIAL_NO_AUTH_ACTION_COUNT
            )
            settings.INITIAL_NO_AUTH_ACTION_COUNT = float(request.data.decode())
            ActionAuthenticatorMixin.request_count = 0
            return (
                200,
                {},
                json.dumps(
                    {
                        "status": "ok",
                        "PREVIOUS_INITIAL_NO_AUTH_ACTION_COUNT": str(
                            previous_initial_no_auth_action_count
                        ),
                    }
                ),
            )
        return 400, {}, json.dumps({"Error": "Need to POST to reset Moto Auth"})

    def model_data(self, request, full_url, headers):  # pylint: disable=unused-argument
        from moto.core.base_backend import model_data

        results = {}
        for service in sorted(model_data):
            models = model_data[service]
            results[service] = {}
            for name in sorted(models):
                model = models[name]
                results[service][name] = []
                for instance in model.instances:
                    inst_result = {}
                    for attr in dir(instance):
                        if not attr.startswith("_"):
                            try:
                                json.dumps(getattr(instance, attr))
                            except (TypeError, AttributeError):
                                pass
                            else:
                                inst_result[attr] = getattr(instance, attr)
                    results[service][name].append(inst_result)
        return 200, {"Content-Type": "application/javascript"}, json.dumps(results)

    def dashboard(self, request, full_url, headers):  # pylint: disable=unused-argument
        from flask import render_template

        return render_template("dashboard.html")

    def get_transition(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        from .models import moto_api_backend

        qs_dict = dict(
            x.split("=") for x in request.query_string.decode("utf-8").split("&")
        )
        model_name = qs_dict["model_name"]

        resp = moto_api_backend.get_transition(model_name=model_name)

        return 200, {}, json.dumps(resp)

    def set_transition(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        from .models import moto_api_backend

        request_body_size = int(headers["Content-Length"])
        body = request.environ["wsgi.input"].read(request_body_size).decode("utf-8")
        body = json.loads(body)
        model_name = body["model_name"]
        transition = body["transition"]

        moto_api_backend.set_transition(model_name, transition)
        return 201, {}, ""

    def unset_transition(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        from .models import moto_api_backend

        request_body_size = int(headers["Content-Length"])
        body = request.environ["wsgi.input"].read(request_body_size).decode("utf-8")
        body = json.loads(body)
        model_name = body["model_name"]

        moto_api_backend.unset_transition(model_name)
        return 201, {}, ""

    def seed(self, req, full_url, headers):
        self.setup_class(req, full_url, headers)
        from . import mock_random

        a = self._get_param("a")
        mock_random.seed(int(a))
        return 200, {}, ""
