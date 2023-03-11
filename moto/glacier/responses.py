import json
from typing import Any, Dict
from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from .models import glacier_backends, GlacierBackend
from .utils import vault_from_glacier_url


class GlacierResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="glacier")

    @property
    def glacier_backend(self) -> GlacierBackend:
        return glacier_backends[self.current_account][self.region]

    def all_vault_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._all_vault_response(headers)

    def _all_vault_response(self, headers: Any) -> TYPE_RESPONSE:
        vaults = self.glacier_backend.list_vaults()
        response = json.dumps(
            {"Marker": None, "VaultList": [vault.to_dict() for vault in vaults]}
        )

        headers["content-type"] = "application/json"
        return 200, headers, response

    def vault_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._vault_response(request, full_url, headers)

    def _vault_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        method = request.method
        vault_name = vault_from_glacier_url(full_url)

        if method == "GET":
            return self._vault_response_get(vault_name, headers)
        elif method == "PUT":
            return self._vault_response_put(vault_name, headers)
        elif method == "DELETE":
            return self._vault_response_delete(vault_name, headers)

    def _vault_response_get(self, vault_name: str, headers: Any) -> TYPE_RESPONSE:
        vault = self.glacier_backend.get_vault(vault_name)
        headers["content-type"] = "application/json"
        return 200, headers, json.dumps(vault.to_dict())

    def _vault_response_put(self, vault_name: str, headers: Any) -> TYPE_RESPONSE:
        self.glacier_backend.create_vault(vault_name)
        return 201, headers, ""

    def _vault_response_delete(self, vault_name: str, headers: Any) -> TYPE_RESPONSE:
        self.glacier_backend.delete_vault(vault_name)
        return 204, headers, ""

    def vault_archive_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        return self._vault_archive_response(request, full_url, headers)

    def _vault_archive_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        description = ""
        if "x-amz-archive-description" in request.headers:
            description = request.headers["x-amz-archive-description"]
        vault_name = full_url.split("/")[-2]

        if method == "POST":
            return self._vault_archive_response_post(
                vault_name, body, description, headers
            )
        else:
            return 400, headers, "400 Bad Request"

    def _vault_archive_response_post(
        self, vault_name: str, body: bytes, description: str, headers: Dict[str, Any]
    ) -> TYPE_RESPONSE:
        vault = self.glacier_backend.upload_archive(vault_name, body, description)
        headers["x-amz-archive-id"] = vault["archive_id"]
        headers["x-amz-sha256-tree-hash"] = vault["sha256"]
        return 201, headers, ""

    def vault_archive_individual_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._vault_archive_individual_response(request, full_url, headers)

    def _vault_archive_individual_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        method = request.method
        vault_name = full_url.split("/")[-3]
        archive_id = full_url.split("/")[-1]

        if method == "DELETE":
            vault = self.glacier_backend.get_vault(vault_name)
            vault.delete_archive(archive_id)
            return 204, headers, ""

    def vault_jobs_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._vault_jobs_response(request, full_url, headers)

    def _vault_jobs_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        account_id = full_url.split("/")[1]
        vault_name = full_url.split("/")[-2]

        if method == "GET":
            jobs = self.glacier_backend.list_jobs(vault_name)
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
            job_id = self.glacier_backend.initiate_job(
                vault_name, job_type, tier, archive_id
            )
            headers["x-amz-job-id"] = job_id
            headers["Location"] = f"/{account_id}/vaults/{vault_name}/jobs/{job_id}"
            return 202, headers, ""

    def vault_jobs_individual_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._vault_jobs_individual_response(full_url, headers)

    def _vault_jobs_individual_response(
        self, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        vault_name = full_url.split("/")[-3]
        archive_id = full_url.split("/")[-1]

        job = self.glacier_backend.describe_job(vault_name, archive_id)
        return 200, headers, json.dumps(job.to_dict())  # type: ignore

    def vault_jobs_output_response(
        self, request: Any, full_url: str, headers: Any
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        return self._vault_jobs_output_response(full_url, headers)

    def _vault_jobs_output_response(self, full_url: str, headers: Any) -> TYPE_RESPONSE:
        vault_name = full_url.split("/")[-4]
        job_id = full_url.split("/")[-2]
        output = self.glacier_backend.get_job_output(vault_name, job_id)
        if output is None:
            return 404, headers, "404 Not Found"
        if isinstance(output, dict):
            headers["content-type"] = "application/json"
            return 200, headers, json.dumps(output)
        else:
            headers["content-type"] = "application/octet-stream"
            return 200, headers, output
