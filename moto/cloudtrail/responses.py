"""Handles incoming cloudtrail requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import cloudtrail_backends
from .exceptions import InvalidParameterCombinationException


class CloudTrailResponse(BaseResponse):
    """Handler for CloudTrail requests and responses."""

    @property
    def cloudtrail_backend(self):
        """Return backend instance specific for this region."""
        return cloudtrail_backends[self.region]

    def create_trail(self):
        name = self._get_param("Name")
        bucket_name = self._get_param("S3BucketName")
        is_global = self._get_bool_param("IncludeGlobalServiceEvents")
        is_multi_region = self._get_bool_param("IsMultiRegionTrail", False)
        if not is_global and is_multi_region:
            raise InvalidParameterCombinationException(
                "Multi-Region trail must include global service events."
            )
        s3_key_prefix = self._get_param("S3KeyPrefix")
        sns_topic_name = self._get_param("SnsTopicName")
        log_validation = self._get_bool_param("EnableLogFileValidation", False)
        is_org_trail = self._get_bool_param("IsOrganizationTrail", False)
        trail = self.cloudtrail_backend.create_trail(
            name,
            bucket_name,
            s3_key_prefix,
            sns_topic_name,
            is_multi_region,
            log_validation,
            is_org_trail,
        )
        return json.dumps(trail.description())

    def get_trail(self):
        name = self._get_param("Name")
        trail = self.cloudtrail_backend.get_trail(name)
        return json.dumps({"Trail": trail.description()})

    def get_trail_status(self):
        name = self._get_param("Name")
        status = self.cloudtrail_backend.get_trail_status(name)
        return json.dumps(status.description())

    def describe_trails(self):
        include_shadow_trails = self._get_bool_param("includeShadowTrails", True)
        trails = self.cloudtrail_backend.describe_trails(include_shadow_trails)
        return json.dumps(
            {"trailList": [t.description(include_region=True) for t in trails]}
        )

    def list_trails(self):
        all_trails = self.cloudtrail_backend.list_trails()
        return json.dumps({"Trails": [t.short() for t in all_trails]})

    def start_logging(self):
        name = self._get_param("Name")
        self.cloudtrail_backend.start_logging(name)
        return json.dumps({})

    def stop_logging(self):
        name = self._get_param("Name")
        self.cloudtrail_backend.stop_logging(name)
        return json.dumps({})

    def delete_trail(self):
        name = self._get_param("Name")
        self.cloudtrail_backend.delete_trail(name)
        return json.dumps({})
