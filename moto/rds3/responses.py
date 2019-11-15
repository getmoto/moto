from __future__ import unicode_literals

import json

import boto3
import xmltodict

from moto.core.responses import BaseResponse
from moto.core.utils import get_random_message_id
from .models import rds3_backends
from . import utils
from .exceptions import InvalidParameterValue
from .models import RDS3Backend
from .utils import DictSerializer, camelcase_to_underscores


MAX_RECORDS = 100


def result_key(result, method):
    # TODO: Fix this abomination
    # Try to do sensible stuff, like try plural and then list
    # If [] just look for list in top level output structure?
    # Or could still do hacky method[9:] for *some* describe methods...
    key = ''
    item = result
    plural = False
    if isinstance(result, list):
        if result:
            item = result[0]
            plural = True
        else:
            if 'tags' in method:
                key = 'TagList'
            else:
                key = method[9:]
            plural = False
            item = None
    if item:
        key = item.__class__.__name__
    if key == 'OptionGroup' and plural:
        key = 'OptionGroupsList'
        plural = False
    elif key == 'Tag' and plural:
        key = 'TagList'
        plural = False
    elif key == 'DBLogFile' and plural:
        key = 'DescribeDBLogFiles'
        plural = False
    return '{}{}'.format(key, 's' if plural else '')


@utils.add_backend_methods(RDS3Backend)
class RDSResponse(BaseResponse):

    @property
    def backend(self):
        return rds3_backends[self.region]

    @property
    def parameters(self):
        return utils.parse_query_parameters(self._get_action(), self.querystring)

    def call_action(self):
        # TODO: Should be able to get rid of this by trapping errors when
        # calling method and properly serializing before returning...
        status, headers, body = super(RDSResponse, self).call_action()
        if status >= 400:
            body = self.get_response(body)
        return status, headers, body

    def handle_action(self):
        client = boto3.client('rds', region_name='us-east-1')
        action = self._get_action()
        action_method = camelcase_to_underscores(action)
        # TODO: Wrap this in a try and catch exceptions and convert to dict
        # try:
        result = getattr(self.backend, action_method)(**self.parameters)

        if client.can_paginate(action_method) or action_method in ['describe_db_clusters',
                                                                   'describe_db_cluster_parameter_groups']:
            result, marker = self._paginate_response(result)
        else:
            marker = None
        # This is needed for empty arrays passed back from describe... could make better...
        # TODO: If empty array passed back from describe, this fails... Need to fix...
        result_dict = {}
        if result is not None:
            if isinstance(result, dict):
                result_dict = result
            else:
                key = camelcase_to_underscores(result_key(result, action_method))
                result_dict[key] = result
        if marker:
            result_dict['marker'] = marker
        serializer = DictSerializer()
        serialized = serializer.serialize_object(result_dict, client.meta.service_model.operation_model(action))
        response = self.package_result(serialized)
        # except HTTPException as http_error:

        return self.get_response(response)

    def _paginate_response(self, resources):
        marker = self.parameters.get('marker')
        page_size = self.parameters.get('max_records', MAX_RECORDS)
        if page_size < 20 or page_size > 100:
            msg = 'Invalid value {} for MaxRecords. Must be between 20 and 100'.format(page_size)
            raise InvalidParameterValue(msg)
        all_resources = list(resources)
        all_ids = [resource.resource_id for resource in all_resources]
        if marker:
            start = all_ids.index(marker) + 1
        else:
            start = 0
        paginated_resources = all_resources[start:start + page_size]
        next_marker = None
        if len(all_resources) > start + page_size:
            next_marker = paginated_resources[-1].resource_id
        return paginated_resources, next_marker

    def package_result(self, result):
        api_method = self._get_action()
        response_key = '{}Response'.format(api_method)
        response = {
            response_key: {
                'ResponseMetadata': {
                    'RequestId': get_random_message_id()
                }
            }
        }
        response[response_key].update(result)
        return response

    def get_response(self, response):
        # TODO: I don't think json is ever used for RDS.  I think redshift switched between boto and boto3.
        if self.request_json:
            return json.dumps(response)
        else:
            # TODO: Get rid of this once serialization is in place.
            # response = utils.fix_bool_values(response)
            xml = xmltodict.unparse(response, full_document=False)
            if hasattr(xml, 'decode'):
                xml = xml.decode('utf-8')
            return xml
