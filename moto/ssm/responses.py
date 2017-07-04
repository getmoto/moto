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
