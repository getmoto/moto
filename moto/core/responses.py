from urlparse import parse_qs

from moto.core.utils import headers_to_dict, camelcase_to_underscores, method_names_from_class


class BaseResponse(object):
    def dispatch(self, uri, body, headers):
        if body:
            querystring = parse_qs(body)
        else:
            querystring = headers_to_dict(headers)

        self.path = uri.path
        self.querystring = querystring

        action = querystring['Action'][0]
        action = camelcase_to_underscores(action)

        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            return method()
        raise NotImplementedError("The {} action has not been implemented".format(action))
