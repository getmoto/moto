from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlparse, parse_qs

from moto.core.responses import _TemplateEnvironmentMixin
from .models import glacier_backends
from .utils import region_from_glacier_url, vault_from_glacier_url


class GlacierResponse(_TemplateEnvironmentMixin):
    def __init__(self, backend):
        super(GlacierResponse, self).__init__()
        self.backend = backend

    @classmethod
    def all_vault_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._all_vault_response(request, full_url, headers)

    def _all_vault_response(self, request, full_url, headers):
        vaults = self.backend.list_vaules()
        response = json.dumps(
            {"Marker": None, "VaultList": [vault.to_dict() for vault in vaults]}
        )

        headers["content-type"] = "application/json"
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

        if method == "GET":
            return self._vault_response_get(vault_name, querystring, headers)
        elif method == "PUT":
            return self._vault_response_put(vault_name, querystring, headers)
        elif method == "DELETE":
            return self._vault_response_delete(vault_name, querystring, headers)

    def _vault_response_get(self, vault_name, querystring, headers):
        vault = self.backend.get_vault(vault_name)
        headers["content-type"] = "application/json"
        return 200, headers, json.dumps(vault.to_dict())

    def _vault_response_put(self, vault_name, querystring, headers):
        self.backend.create_vault(vault_name)
        return 201, headers, ""

    def _vault_response_delete(self, vault_name, querystring, headers):
        self.backend.delete_vault(vault_name)
        return 204, headers, ""

    @classmethod
    def vault_archive_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_archive_response(request, full_url, headers)

    def _vault_archive_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        description = ""
        if "x-amz-archive-description" in request.headers:
            description = request.headers["x-amz-archive-description"]
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        vault_name = full_url.split("/")[-2]

        if method == "POST":
            return self._vault_archive_response_post(
                vault_name, body, description, querystring, headers
            )
        else:
            return 400, headers, "400 Bad Request"

    def _vault_archive_response_post(
        self, vault_name, body, description, querystring, headers
    ):
        vault = self.backend.get_vault(vault_name)
        vault_id = vault.create_archive(body, description)
        headers["x-amz-archive-id"] = vault_id
        return 201, headers, ""

    @classmethod
    def vault_archive_individual_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_archive_individual_response(
            request, full_url, headers
        )

    def _vault_archive_individual_response(self, request, full_url, headers):
        method = request.method
        vault_name = full_url.split("/")[-3]
        archive_id = full_url.split("/")[-1]

        if method == "DELETE":
            vault = self.backend.get_vault(vault_name)
            vault.delete_archive(archive_id)
            return 204, headers, ""

    @classmethod
    def vault_jobs_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_jobs_response(request, full_url, headers)

    def _vault_jobs_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        account_id = full_url.split("/")[1]
        vault_name = full_url.split("/")[-2]

        if method == "GET":
            jobs = self.backend.list_jobs(vault_name)
            headers["content-type"] = "application/json"
            return (
                200,
                headers,
                json.dumps(
                    {"JobList": [job.to_dict() for job in jobs], "Marker": None}
                ),
            )
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            job_type = json_body["Type"]
            archive_id = None
            if "ArchiveId" in json_body:
                archive_id = json_body["ArchiveId"]
            if "Tier" in json_body:
                tier = json_body["Tier"]
            else:
                tier = "Standard"
            job_id = self.backend.initiate_job(vault_name, job_type, tier, archive_id)
            headers["x-amz-job-id"] = job_id
            headers["Location"] = "/{0}/vaults/{1}/jobs/{2}".format(
                account_id, vault_name, job_id
            )
            return 202, headers, ""

    @classmethod
    def vault_jobs_individual_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_jobs_individual_response(
            request, full_url, headers
        )

    def _vault_jobs_individual_response(self, request, full_url, headers):
        vault_name = full_url.split("/")[-3]
        archive_id = full_url.split("/")[-1]

        vault = self.backend.get_vault(vault_name)
        job = vault.describe_job(archive_id)
        return 200, headers, json.dumps(job.to_dict())

    @classmethod
    def vault_jobs_output_response(clazz, request, full_url, headers):
        region_name = region_from_glacier_url(full_url)
        response_instance = GlacierResponse(glacier_backends[region_name])
        return response_instance._vault_jobs_output_response(request, full_url, headers)

    def _vault_jobs_output_response(self, request, full_url, headers):
        vault_name = full_url.split("/")[-4]
        job_id = full_url.split("/")[-2]
        vault = self.backend.get_vault(vault_name)
        if vault.job_ready(job_id):
            output = vault.get_job_output(job_id)
            if isinstance(output, dict):
                headers["content-type"] = "application/json"
                return 200, headers, json.dumps(output)
            else:
                headers["content-type"] = "application/octet-stream"
                return 200, headers, output
        else:
            return 404, headers, "404 Not Found"
