import datetime
import json

from urlparse import parse_qs, urlparse

from moto.core.utils import camelcase_to_underscores, method_names_from_class


class BaseResponse(object):

    def dispatch(self, request, full_url, headers):
        if hasattr(request, 'body'):
            # Boto
            self.body = request.body
        else:
            # Flask server
            self.body = request.data

        querystring = parse_qs(urlparse(full_url).query)
        if not querystring:
            querystring = parse_qs(self.body)
        if not querystring:
            querystring = headers

        self.uri = full_url
        self.path = urlparse(full_url).path
        self.querystring = querystring
        self.method = request.method

        self.headers = dict(request.headers)
        self.response_headers = headers
        return self.call_action()

    def call_action(self):
        headers = self.response_headers
        action = self.querystring.get('Action', [""])[0]
        action = camelcase_to_underscores(action)
        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            response = method()
            if isinstance(response, basestring):
                return 200, headers, response
            else:
                body, new_headers = response
                status = new_headers.pop('status', 200)
                headers.update(new_headers)
                return status, headers, body
        raise NotImplementedError("The {0} action has not been implemented".format(action))


def metadata_response(request, full_url, headers):
    """
    Mock response for localhost metadata

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
    """
    parsed_url = urlparse(full_url)
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    credentials = dict(
        AccessKeyId="test-key",
        SecretAccessKey="test-secret-key",
        Token="test-session-token",
        Expiration=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    path = parsed_url.path.lstrip("/latest/meta-data/")
    if path == '':
        result = 'iam'
    elif path == 'iam':
        result = json.dumps({
            'security-credentials': {
                'default-role': credentials
            }
        })
    elif path == 'iam/security-credentials/':
        result = 'default-role'
    elif path == 'iam/security-credentials/default-role':
        result = json.dumps(credentials)
    return 200, headers, result
