import responses
import types
from io import BytesIO
from http.client import responses as http_responses
from urllib.parse import urlparse
from werkzeug.wrappers import Request

from moto.utilities.distutils_version import LooseVersion

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version


RESPONSES_VERSION = version("responses")


class CallbackResponse(responses.CallbackResponse):
    """
    Need to subclass so we can change a couple things
    """

    def get_response(self, request):
        """
        Need to override this so we can pass decode_content=False
        """
        if not isinstance(request, Request):
            url = urlparse(request.url)
            if request.body is None:
                body = None
            elif isinstance(request.body, str):
                body = BytesIO(request.body.encode("UTF-8"))
            elif hasattr(request.body, "read"):
                body = BytesIO(request.body.read())
            else:
                body = BytesIO(request.body)
            req = Request.from_values(
                path="?".join([url.path, url.query]),
                input_stream=body,
                content_length=request.headers.get("Content-Length"),
                content_type=request.headers.get("Content-Type"),
                method=request.method,
                base_url="{scheme}://{netloc}".format(
                    scheme=url.scheme, netloc=url.netloc
                ),
                headers=[(k, v) for k, v in request.headers.items()],
            )
            request = req
        headers = self.get_headers()

        result = self.callback(request)
        if isinstance(result, Exception):
            raise result

        status, r_headers, body = result
        body = responses._handle_body(body)
        headers.update(r_headers)

        return responses.HTTPResponse(
            status=status,
            reason=http_responses.get(status),
            body=body,
            headers=headers,
            preload_content=False,
            # Need to not decode_content to mimic requests
            decode_content=False,
        )

    def _url_matches(self, url, other, match_querystring=False):
        """
        Need to override this so we can fix querystrings breaking regex matching
        """
        if not match_querystring:
            other = other.split("?", 1)[0]

        if isinstance(url, str):
            if responses._has_unicode(url):
                url = responses._clean_unicode(url)
                if not isinstance(other, str):
                    other = other.encode("ascii").decode("utf8")
            return self._url_matches_strict(url, other)
        elif isinstance(url, responses.Pattern) and url.match(other):
            return True
        else:
            return False


def not_implemented_callback(request):  # pylint: disable=unused-argument
    status = 400
    headers = {}
    response = "The method is not implemented"

    return status, headers, response


# Modify behaviour of the matcher to only/always return the first match
# Default behaviour is to return subsequent matches for subsequent requests, which leads to https://github.com/spulec/moto/issues/2567
#  - First request matches on the appropriate S3 URL
#  - Same request, executed again, will be matched on the subsequent match, which happens to be the catch-all, not-yet-implemented, callback
# Fix: Always return the first match
#
# Note that, due to an outdated API we no longer support Responses <= 0.12.1
# This method should be used for Responses 0.12.1 < .. < 0.17.0
def _find_first_match(self, request):
    matches = []
    match_failed_reasons = []
    all_possibles = self._matches + responses._default_mock._matches
    for match in all_possibles:
        match_result, reason = match.matches(request)
        if match_result:
            matches.append(match)
        else:
            match_failed_reasons.append(reason)

    # Look for implemented callbacks first
    implemented_matches = [
        m
        for m in matches
        if type(m) is not CallbackResponse or m.callback != not_implemented_callback
    ]
    if implemented_matches:
        return implemented_matches[0], []
    elif matches:
        # We had matches, but all were of type not_implemented_callback
        return matches[0], match_failed_reasons

    return None, match_failed_reasons


def get_response_mock():
    """
    The responses-library is crucial in ensuring that requests to AWS are intercepted, and routed to the right backend.
    However, as our usecase is different from a 'typical' responses-user, Moto always needs some custom logic to ensure responses behaves in a way that works for us.

    For older versions, that meant changing the internal logic
    For later versions, > 0.17.0, we can use a custom registry, and extend the logic instead of overriding it

    For all versions, we need to add passthrough to allow non-AWS requests to work
    """
    responses_mock = None

    if LooseVersion(RESPONSES_VERSION) >= LooseVersion("0.17.0"):
        from .responses_custom_registry import CustomRegistry

        responses_mock = responses.RequestsMock(
            assert_all_requests_are_fired=False, registry=CustomRegistry
        )
    else:
        responses_mock = responses.RequestsMock(assert_all_requests_are_fired=False)
        responses_mock._find_match = types.MethodType(_find_first_match, responses_mock)

    responses_mock.add_passthru("http")
    return responses_mock


def reset_responses_mock(responses_mock):
    if LooseVersion(RESPONSES_VERSION) >= LooseVersion("0.17.0"):
        from .responses_custom_registry import CustomRegistry

        responses_mock.reset()
        # No way to set the registry directly (yet..)
        responses_mock._set_registry(CustomRegistry)
        responses_mock.add_passthru("http")
    else:
        responses_mock.reset()
