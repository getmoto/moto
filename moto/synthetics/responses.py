"""
Response handlers for AWS CloudWatch Synthetics API emulation in Moto.
"""

from typing import Any

from moto.core.responses import BaseResponse
from moto.synthetics.models import SyntheticsBackend, synthetics_backends


class SyntheticsResponse(BaseResponse):
    """
    Handles API responses for AWS CloudWatch Synthetics operations.
    """

    def __init__(self) -> None:
        """
        Initialize the SyntheticsResponse with the synthetics service name.
        """
        super().__init__(service_name="synthetics")

    @property
    def synthetics_backend(self) -> SyntheticsBackend:
        """
        Returns the backend instance for the current region.
        """
        return synthetics_backends[self.region]  # type: ignore

    def create_canary(self) -> dict[str, Any]:
        """
        Create a new canary using the provided parameters.
        """
        params: dict[str, Any] = (
            self.request_json if isinstance(self.request_json, dict) else {}
        )
        canary = self.synthetics_backend.create_canary(
            name=params["Name"],
            code=params.get("Code", {}),
            artifact_s3_location=params.get("ArtifactS3Location", "s3://dummy"),
            execution_role_arn=params.get(
                "ExecutionRoleArn", "arn:aws:iam::123:role/service-role"
            ),
            schedule=params.get("Schedule", {"Expression": "rate(5 minutes)"}),
            run_config=params.get("RunConfig", {"TimeoutInSeconds": 60}),
            success_retention_period_in_days=params.get(
                "SuccessRetentionPeriodInDays", 31
            ),
            failure_retention_period_in_days=params.get(
                "FailureRetentionPeriodInDays", 31
            ),
            runtime_version=params.get("RuntimeVersion", "syn-nodejs-puppeteer-3.8"),
            vpc_config=params.get("VpcConfig"),
            resources_to_replicate_tags=params.get("ResourcesToReplicateTags"),
            provisioned_resource_cleanup=params.get("ProvisionedResourceCleanup"),
            browser_configs=params.get("BrowserConfigs"),
            tags=params.get("Tags", {}),
            artifact_config=params.get("ArtifactConfig"),
        )
        return {"Canary": canary.to_dict()}

    def get_canary(self) -> dict[str, object]:
        """
        Retrieve details for a specific canary by name.
        """
        params = self._get_params()  # from URL path regex
        name = params["name"]
        canary = self.synthetics_backend.get_canary(name)
        return {"Canary": canary.to_dict()}

    def describe_canaries(self) -> dict[str, object]:
        """
        List all canaries in the backend.
        """
        canaries, _ = self.synthetics_backend.describe_canaries(None, None, None)
        return {"Canaries": [c.to_dict() for c in canaries]}

    def list_tags_for_resource(self) -> dict[str, object]:
        """
        List tags for a given resource ARN.
        """
        params = self._get_params()  # from URL path regex
        arn = params["resourceArn"]
        tags = self.synthetics_backend.list_tags_for_resource(arn)
        return {"Tags": tags}
