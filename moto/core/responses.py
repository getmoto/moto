import datetime
import json

from urlparse import parse_qs

from moto.core.utils import headers_to_dict, camelcase_to_underscores, method_names_from_class


class BaseResponse(object):
    def dispatch2(self, uri, body, headers):
        return self.dispatch(uri, body, headers)

    def dispatch(self, uri, body, headers):
        if body:
            querystring = parse_qs(body)
        else:
            querystring = headers_to_dict(headers)

        self.path = uri.path
        self.querystring = querystring

        action = querystring.get('Action', [""])[0]
        action = camelcase_to_underscores(action)

        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            return method()
        raise NotImplementedError("The {} action has not been implemented".format(action))


def metadata_response(uri, body, headers):
    """
    Mock response for localhost metadata

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
    """

    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    path = uri.path.lstrip("/latest/meta-data/")
    if path == '':
        return "iam/"
    elif path == 'iam/':
        return 'security-credentials/'
    elif path == 'iam/security-credentials/':
        return 'default-role'
    elif path == 'iam/security-credentials/default-role':
        return json.dumps(dict(
            AccessKeyId="test-key",
            SecretAccessKey="test-secret-key",
            Token="test-session-token",
            Expiration=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")
        ))
