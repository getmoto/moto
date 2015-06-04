from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlparse, parse_qs

from moto.core.responses import _TemplateEnvironmentMixin
from .models import glacier_backends
from .utils import region_from_glacier_url, vault_from_glacier_url


class GlacierResponse(_TemplateEnvironmentMixin):

    def __init__(self, backend):
        self.backend = backend

    @classmethod
    def all_vault_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._all_vault_response(request, full_url, headers)

    def _all_vault_response(self, request, full_url, headers):
        vaults = self.backend.list_vaules()
        response = json.dumps({
            "Marker": None,
            "VaultList": [
                vault.to_dict() for vault in vaults
            ]
        })

        headers['content-type'] = 'application/json'
        return 200, headers, response

    @classmethod
    def vault_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_response(request, full_url, headers)

    def _vault_response(self, request, full_url, headers):
        method = request.method
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        vault_name = vault_from_glacier_url(full_url)

        if method == 'GET':
            return self._vault_response_get(vault_name, querystring, headers)
        elif method == 'PUT':
            return self._vault_response_put(vault_name, querystring, headers)
        elif method == 'DELETE':
            return self._vault_response_delete(vault_name, querystring, headers)

    def _vault_response_get(self, vault_name, querystring, headers):
        vault = self.backend.get_vault(vault_name)
        headers['content-type'] = 'application/json'
        return 200, headers, json.dumps(vault.to_dict())

    def _vault_response_put(self, vault_name, querystring, headers):
        self.backend.create_vault(vault_name)
        return 201, headers, ""

    def _vault_response_delete(self, vault_name, querystring, headers):
        self.backend.delete_vault(vault_name)
        return 204, headers, ""
