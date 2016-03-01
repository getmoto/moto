from __future__ import unicode_literals

import datetime
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_with_milliseconds
from .utils import create_rest_api_id


class RestAPI(object):
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description
        self.create_date = datetime.datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "createdDate": iso_8601_datetime_with_milliseconds(self.create_date),
        }


class APIGatewayBackend(BaseBackend):
    def __init__(self, region_name):
        super(APIGatewayBackend, self).__init__()
        self.apis = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_rest_api(self, name, description):
        api_id = create_rest_api_id()
        rest_api = RestAPI(api_id, name, description)
        self.apis[api_id] = rest_api
        return rest_api

    def get_rest_api(self, function_id):
        rest_api = self.apis[function_id]
        return rest_api

    def list_apis(self):
        return self.apis.values()

    def delete_rest_api(self, function_id):
        rest_api = self.apis.pop(function_id)
        return rest_api

apigateway_backends = {}
for region_name in ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']:  # Not available in boto yet
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
