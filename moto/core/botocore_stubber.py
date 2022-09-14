from collections import defaultdict
from io import BytesIO
from botocore.awsrequest import AWSResponse
from moto.core.exceptions import HTTPException


class MockRawResponse(BytesIO):
    def __init__(self, response_input):
        if isinstance(response_input, str):
            response_input = response_input.encode("utf-8")
        super().__init__(response_input)

    def stream(self, **kwargs):  # pylint: disable=unused-argument
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class BotocoreStubber:
    def __init__(self):
        self.enabled = False
        self.methods = defaultdict(list)

    def reset(self):
        self.methods.clear()

    def register_response(self, method, pattern, response):
        matchers = self.methods[method]
        matchers.append((pattern, response))

    def __call__(self, event_name, request, **kwargs):
        if not self.enabled:
            return None

        from moto.moto_api import recorder

        response = None
        response_callback = None
        found_index = None
        matchers = self.methods.get(request.method)

        base_url = request.url.split("?", 1)[0]
        for i, (pattern, callback) in enumerate(matchers):
            if pattern.match(base_url):
                if found_index is None:
                    found_index = i
                    response_callback = callback
                else:
                    matchers.pop(found_index)
                    break

        if response_callback is not None:
            for header, value in request.headers.items():
                if isinstance(value, bytes):
                    request.headers[header] = value.decode("utf-8")
            try:
                status, headers, body = response_callback(
                    request, request.url, request.headers
                )

                # TODO:
                # [x] record manual HTTP requests
                # [x] test boto requests with body
                # [x] test manual requests with body
                # technical approach: Unified pre-process method that we call before calling `response_callback` or the werkzeug equivalent?
                # maybe send all incoming requests to the same place, so that the response_callback is only computed in one place
                # [x] test with treadedmotoserver
                # docs
                # [x] replay_recording(target_host) should replace all urls (with a note explaining that it should only work in ServerMode)
                recorder.record_request(request)
            except HTTPException as e:
                status = e.code
                headers = e.get_headers()
                body = e.get_body()
            body = MockRawResponse(body)
            response = AWSResponse(request.url, status, headers, body)

        return response
