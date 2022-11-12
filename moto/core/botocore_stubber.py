from collections import defaultdict
from io import BytesIO
from botocore.awsrequest import AWSResponse
from moto.core.exceptions import HTTPException
from typing import Any, Dict, Callable, List, Tuple, Union, Pattern
from .responses import TYPE_RESPONSE


class MockRawResponse(BytesIO):
    def __init__(self, response_input: Union[str, bytes]):
        if isinstance(response_input, str):
            response_input = response_input.encode("utf-8")
        super().__init__(response_input)

    def stream(self, **kwargs: Any) -> Any:  # pylint: disable=unused-argument
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class BotocoreStubber:
    def __init__(self) -> None:
        self.enabled = False
        self.methods: Dict[
            str, List[Tuple[Pattern[str], Callable[..., TYPE_RESPONSE]]]
        ] = defaultdict(list)

    def reset(self) -> None:
        self.methods.clear()

    def register_response(
        self, method: str, pattern: Pattern[str], response: Callable[..., TYPE_RESPONSE]
    ) -> None:
        matchers = self.methods[method]
        matchers.append((pattern, response))

    def __call__(self, event_name: str, request: Any, **kwargs: Any) -> AWSResponse:
        if not self.enabled:
            return None

        from moto.moto_api import recorder

        response = None
        response_callback = None
        found_index = None
        matchers = self.methods.get(request.method)

        base_url = request.url.split("?", 1)[0]
        for i, (pattern, callback) in enumerate(matchers):  # type: ignore[arg-type]
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
                recorder._record_request(request)

                status, headers, body = response_callback(
                    request, request.url, request.headers
                )

            except HTTPException as e:
                status = e.code  # type: ignore[assignment]
                headers = e.get_headers()  # type: ignore[assignment]
                body = e.get_body()
            raw_response = MockRawResponse(body)
            response = AWSResponse(request.url, status, headers, raw_response)

        return response
