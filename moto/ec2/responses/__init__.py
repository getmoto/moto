from urlparse import parse_qs

from moto.ec2.utils import camelcase_to_underscores, method_namess_from_class

from .instances import InstanceResponse
from .tags import TagResponse


class EC2Response(object):

    sub_responses = [InstanceResponse, TagResponse]

    def dispatch(self, uri, body, headers):
        if body:
            querystring = parse_qs(body)
        else:
            querystring = parse_qs(headers)

        action = querystring['Action'][0]
        action = camelcase_to_underscores(action)

        for sub_response in self.sub_responses:
            method_names = method_namess_from_class(sub_response)
            if action in method_names:
                response = sub_response(querystring)
                method = getattr(response, action)
                return method()
        import pdb;pdb.set_trace()
