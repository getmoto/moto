from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ssm_backends


class SimpleSystemManagerResponse(BaseResponse):

    @property
    def ssm_backend(self):
        return ssm_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, default=None):
        return self.request_params.get(param, default)

    def delete_parameter(self):
        name = self._get_param('Name')
        self.ssm_backend.delete_parameter(name)
        return json.dumps({})

    def delete_parameters(self):
        names = self._get_param('Names')
        result = self.ssm_backend.delete_parameters(names)

        response = {
            'DeletedParameters': [],
            'InvalidParameters': []
        }

        for name in names:
            if name in result:
                response['DeletedParameters'].append(name)
            else:
                response['InvalidParameters'].append(name)
        return json.dumps(response)

    def get_parameters(self):
        names = self._get_param('Names')
        with_decryption = self._get_param('WithDecryption')

        result = self.ssm_backend.get_parameters(names, with_decryption)

        response = {
            'Parameters': [],
            'InvalidParameters': [],
        }

        for parameter in result:
            param_data = parameter.response_object(with_decryption)
            response['Parameters'].append(param_data)

        param_names = [param.name for param in result]
        for name in names:
            if name not in param_names:
                response['InvalidParameters'].append(name)
        return json.dumps(response)

    def describe_parameters(self):
        page_size = 10
        filters = self._get_param('Filters')
        token = self._get_param('NextToken')
        if hasattr(token, 'strip'):
            token = token.strip()
        if not token:
            token = '0'
        token = int(token)

        result = self.ssm_backend.get_all_parameters()
        response = {
            'Parameters': [],
        }

        end = token + page_size
        for parameter in result[token:]:
            param_data = parameter.response_object(False)
            add = False

            if filters:
                for filter in filters:
                    if filter['Key'] == 'Name':
                        k = param_data['Name']
                        for v in filter['Values']:
                            if k.startswith(v):
                                add = True
                                break
                    elif filter['Key'] == 'Type':
                        k = param_data['Type']
                        for v in filter['Values']:
                            if k == v:
                                add = True
                                break
                    elif filter['Key'] == 'KeyId':
                        k = param_data.get('KeyId')
                        if k:
                            for v in filter['Values']:
                                if k == v:
                                    add = True
                                    break
            else:
                add = True

            if add:
                response['Parameters'].append(param_data)

            token = token + 1
            if len(response['Parameters']) == page_size:
                response['NextToken'] = str(end)
                break

        return json.dumps(response)

    def put_parameter(self):
        name = self._get_param('Name')
        description = self._get_param('Description')
        value = self._get_param('Value')
        type_ = self._get_param('Type')
        keyid = self._get_param('KeyId')
        overwrite = self._get_param('Overwrite', False)

        self.ssm_backend.put_parameter(
            name, description, value, type_, keyid, overwrite)
        return json.dumps({})

    def add_tags_to_resource(self):
        resource_id = self._get_param('ResourceId')
        resource_type = self._get_param('ResourceType')
        tags = {t['Key']: t['Value'] for t in self._get_param('Tags')}
        self.ssm_backend.add_tags_to_resource(
            resource_id, resource_type, tags)
        return json.dumps({})

    def remove_tags_from_resource(self):
        resource_id = self._get_param('ResourceId')
        resource_type = self._get_param('ResourceType')
        keys = self._get_param('TagKeys')
        self.ssm_backend.remove_tags_from_resource(
            resource_id, resource_type, keys)
        return json.dumps({})

    def list_tags_for_resource(self):
        resource_id = self._get_param('ResourceId')
        resource_type = self._get_param('ResourceType')
        tags = self.ssm_backend.list_tags_for_resource(
            resource_id, resource_type)
        tag_list = [{'Key': k, 'Value': v} for (k, v) in tags.items()]
        response = {'TagList': tag_list}
        return json.dumps(response)
