import re
import time

from datetime import datetime
from moto.core import get_account_id, BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds, BackendDict
from moto.utilities.tagging_service import TaggingService
from .exceptions import (
    S3BucketDoesNotExistException,
    InsufficientSnsTopicPolicyException,
    TrailNameTooLong,
    TrailNameTooShort,
    TrailNameNotStartingCorrectly,
    TrailNameNotEndingCorrectly,
    TrailNameInvalidChars,
    TrailNotFoundException,
)


def datetime2int(date):
    return int(time.mktime(date.timetuple()))


class TrailStatus(object):
    def __init__(self):
        self.is_logging = False
        self.latest_delivery_time = ""
        self.latest_delivery_attempt = ""
        self.start_logging_time = None
        self.started = None
        self.stopped = None

    def start_logging(self):
        self.is_logging = True
        self.started = datetime.utcnow()
        self.latest_delivery_time = datetime2int(datetime.utcnow())
        self.latest_delivery_attempt = iso_8601_datetime_without_milliseconds(
            datetime.utcnow()
        )

    def stop_logging(self):
        self.is_logging = False
        self.stopped = datetime.utcnow()

    def description(self):
        if self.is_logging:
            self.latest_delivery_time = datetime2int(datetime.utcnow())
            self.latest_delivery_attempt = iso_8601_datetime_without_milliseconds(
                datetime.utcnow()
            )
        desc = {
            "IsLogging": self.is_logging,
            "LatestDeliveryAttemptTime": self.latest_delivery_attempt,
            "LatestNotificationAttemptTime": "",
            "LatestNotificationAttemptSucceeded": "",
            "LatestDeliveryAttemptSucceeded": "",
            "TimeLoggingStarted": "",
            "TimeLoggingStopped": "",
        }
        if self.started:
            desc["StartLoggingTime"] = datetime2int(self.started)
            desc["TimeLoggingStarted"] = iso_8601_datetime_without_milliseconds(
                self.started
            )
            desc["LatestDeliveryTime"] = self.latest_delivery_time
        if self.stopped:
            desc["StopLoggingTime"] = datetime2int(self.stopped)
            desc["TimeLoggingStopped"] = iso_8601_datetime_without_milliseconds(
                self.stopped
            )
        return desc


class Trail(BaseModel):
    def __init__(
        self,
        region_name,
        trail_name,
        bucket_name,
        s3_key_prefix,
        sns_topic_name,
        is_global,
        is_multi_region,
        log_validation,
        is_org_trail,
        cw_log_group_arn,
        cw_role_arn,
        kms_key_id,
    ):
        self.region_name = region_name
        self.trail_name = trail_name
        self.bucket_name = bucket_name
        self.s3_key_prefix = s3_key_prefix
        self.sns_topic_name = sns_topic_name
        self.is_multi_region = is_multi_region
        self.log_validation = log_validation
        self.is_org_trail = is_org_trail
        self.include_global_service_events = is_global
        self.cw_log_group_arn = cw_log_group_arn
        self.cw_role_arn = cw_role_arn
        self.kms_key_id = kms_key_id
        self.check_name()
        self.check_bucket_exists()
        self.check_topic_exists()
        self.status = TrailStatus()
        self.event_selectors = list()
        self.advanced_event_selectors = list()
        self.insight_selectors = list()

    @property
    def arn(self):
        return f"arn:aws:cloudtrail:{self.region_name}:{get_account_id()}:trail/{self.trail_name}"

    @property
    def topic_arn(self):
        if self.sns_topic_name:
            return f"arn:aws:sns:{self.region_name}:{get_account_id()}:{self.sns_topic_name}"
        return None

    def check_name(self):
        if len(self.trail_name) < 3:
            raise TrailNameTooShort(actual_length=len(self.trail_name))
        if len(self.trail_name) > 128:
            raise TrailNameTooLong(actual_length=len(self.trail_name))
        if not re.match("^[0-9a-zA-Z]{1}.+$", self.trail_name):
            raise TrailNameNotStartingCorrectly()
        if not re.match(r".+[0-9a-zA-Z]{1}$", self.trail_name):
            raise TrailNameNotEndingCorrectly()
        if not re.match(r"^[.\-_0-9a-zA-Z]+$", self.trail_name):
            raise TrailNameInvalidChars()

    def check_bucket_exists(self):
        from moto.s3 import s3_backend

        try:
            s3_backend.get_bucket(self.bucket_name)
        except Exception:
            raise S3BucketDoesNotExistException(
                f"S3 bucket {self.bucket_name} does not exist!"
            )

    def check_topic_exists(self):
        if self.sns_topic_name:
            from moto.sns import sns_backends

            sns_backend = sns_backends[self.region_name]
            try:
                sns_backend.get_topic(self.topic_arn)
            except Exception:
                raise InsufficientSnsTopicPolicyException(
                    "SNS Topic does not exist or the topic policy is incorrect!"
                )

    def start_logging(self):
        self.status.start_logging()

    def stop_logging(self):
        self.status.stop_logging()

    def put_event_selectors(self, event_selectors, advanced_event_selectors):
        if event_selectors:
            self.event_selectors = event_selectors
        elif advanced_event_selectors:
            self.event_selectors = []
            self.advanced_event_selectors = advanced_event_selectors

    def get_event_selectors(self):
        return self.event_selectors, self.advanced_event_selectors

    def put_insight_selectors(self, insight_selectors):
        self.insight_selectors.extend(insight_selectors)

    def get_insight_selectors(self):
        return self.insight_selectors

    def update(
        self,
        s3_bucket_name,
        s3_key_prefix,
        sns_topic_name,
        include_global_service_events,
        is_multi_region_trail,
        enable_log_file_validation,
        is_organization_trail,
        cw_log_group_arn,
        cw_role_arn,
        kms_key_id,
    ):
        if s3_bucket_name is not None:
            self.bucket_name = s3_bucket_name
        if s3_key_prefix is not None:
            self.s3_key_prefix = s3_key_prefix
        if sns_topic_name is not None:
            self.sns_topic_name = sns_topic_name
        if include_global_service_events is not None:
            self.include_global_service_events = include_global_service_events
        if is_multi_region_trail is not None:
            self.is_multi_region = is_multi_region_trail
        if enable_log_file_validation is not None:
            self.log_validation = enable_log_file_validation
        if is_organization_trail is not None:
            self.is_org_trail = is_organization_trail
        if cw_log_group_arn is not None:
            self.cw_log_group_arn = cw_log_group_arn
        if cw_role_arn is not None:
            self.cw_role_arn = cw_role_arn
        if kms_key_id is not None:
            self.kms_key_id = kms_key_id

    def short(self):
        return {
            "Name": self.trail_name,
            "TrailARN": self.arn,
            "HomeRegion": self.region_name,
        }

    def description(self, include_region=False):
        desc = {
            "Name": self.trail_name,
            "S3BucketName": self.bucket_name,
            "IncludeGlobalServiceEvents": self.include_global_service_events,
            "IsMultiRegionTrail": self.is_multi_region,
            "TrailARN": self.arn,
            "LogFileValidationEnabled": self.log_validation,
            "IsOrganizationTrail": self.is_org_trail,
            "HasCustomEventSelectors": False,
            "HasInsightSelectors": False,
            "CloudWatchLogsLogGroupArn": self.cw_log_group_arn,
            "CloudWatchLogsRoleArn": self.cw_role_arn,
            "KmsKeyId": self.kms_key_id,
        }
        if self.s3_key_prefix is not None:
            desc["S3KeyPrefix"] = self.s3_key_prefix
        if self.sns_topic_name is not None:
            desc["SnsTopicName"] = self.sns_topic_name
            desc["SnsTopicARN"] = self.topic_arn
        if include_region:
            desc["HomeRegion"] = self.region_name
        return desc


class CloudTrailBackend(BaseBackend):
    """Implementation of CloudTrail APIs."""

    def __init__(self, region_name):
        self.region_name = region_name
        self.trails = dict()
        self.tagging_service = TaggingService(tag_name="TagsList")

    def create_trail(
        self,
        name,
        bucket_name,
        s3_key_prefix,
        sns_topic_name,
        is_global,
        is_multi_region,
        log_validation,
        is_org_trail,
        cw_log_group_arn,
        cw_role_arn,
        kms_key_id,
        tags_list,
    ):
        trail = Trail(
            self.region_name,
            name,
            bucket_name,
            s3_key_prefix,
            sns_topic_name,
            is_global,
            is_multi_region,
            log_validation,
            is_org_trail,
            cw_log_group_arn,
            cw_role_arn,
            kms_key_id,
        )
        self.trails[name] = trail
        self.tagging_service.tag_resource(trail.arn, tags_list)
        return trail

    def get_trail(self, name_or_arn):
        if len(name_or_arn) < 3:
            raise TrailNameTooShort(actual_length=len(name_or_arn))
        if name_or_arn in self.trails:
            return self.trails[name_or_arn]
        for trail in self.trails.values():
            if trail.arn == name_or_arn:
                return trail
        raise TrailNotFoundException(name_or_arn)

    def get_trail_status(self, name):
        if len(name) < 3:
            raise TrailNameTooShort(actual_length=len(name))
        trail_name = next(
            (
                trail.trail_name
                for trail in self.trails.values()
                if trail.trail_name == name or trail.arn == name
            ),
            None,
        )
        if not trail_name:
            # This particular method returns the ARN as part of the error message
            arn = (
                f"arn:aws:cloudtrail:{self.region_name}:{get_account_id()}:trail/{name}"
            )
            raise TrailNotFoundException(name=arn)
        trail = self.trails[trail_name]
        return trail.status

    def describe_trails(self, include_shadow_trails):
        all_trails = []
        if include_shadow_trails:
            for backend in cloudtrail_backends.values():
                all_trails.extend(backend.trails.values())
        else:
            all_trails.extend(self.trails.values())
        return all_trails

    def list_trails(self):
        return self.describe_trails(include_shadow_trails=True)

    def start_logging(self, name):
        trail = self.trails[name]
        trail.start_logging()

    def stop_logging(self, name):
        trail = self.trails[name]
        trail.stop_logging()

    def delete_trail(self, name):
        if name in self.trails:
            del self.trails[name]

    def update_trail(
        self,
        name,
        s3_bucket_name,
        s3_key_prefix,
        sns_topic_name,
        include_global_service_events,
        is_multi_region_trail,
        enable_log_file_validation,
        is_organization_trail,
        cw_log_group_arn,
        cw_role_arn,
        kms_key_id,
    ):
        trail = self.get_trail(name_or_arn=name)
        trail.update(
            s3_bucket_name=s3_bucket_name,
            s3_key_prefix=s3_key_prefix,
            sns_topic_name=sns_topic_name,
            include_global_service_events=include_global_service_events,
            is_multi_region_trail=is_multi_region_trail,
            enable_log_file_validation=enable_log_file_validation,
            is_organization_trail=is_organization_trail,
            cw_log_group_arn=cw_log_group_arn,
            cw_role_arn=cw_role_arn,
            kms_key_id=kms_key_id,
        )
        return trail

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def put_event_selectors(
        self, trail_name, event_selectors, advanced_event_selectors
    ):
        trail = self.get_trail(trail_name)
        trail.put_event_selectors(event_selectors, advanced_event_selectors)
        trail_arn = trail.arn
        return trail_arn, event_selectors, advanced_event_selectors

    def get_event_selectors(self, trail_name):
        trail = self.get_trail(trail_name)
        event_selectors, advanced_event_selectors = trail.get_event_selectors()
        return trail.arn, event_selectors, advanced_event_selectors

    def add_tags(self, resource_id, tags_list):
        self.tagging_service.tag_resource(resource_id, tags_list)

    def remove_tags(self, resource_id, tags_list):
        self.tagging_service.untag_resource_using_tags(resource_id, tags_list)

    def list_tags(self, resource_id_list):
        """
        Pagination is not yet implemented
        """
        resp = [{"ResourceId": r_id} for r_id in resource_id_list]
        for item in resp:
            item["TagsList"] = self.tagging_service.list_tags_for_resource(
                item["ResourceId"]
            )["TagsList"]
        return resp

    def put_insight_selectors(self, trail_name, insight_selectors):
        trail = self.get_trail(trail_name)
        trail.put_insight_selectors(insight_selectors)
        return trail.arn, insight_selectors

    def get_insight_selectors(self, trail_name):
        trail = self.get_trail(trail_name)
        return trail.arn, trail.get_insight_selectors()


cloudtrail_backends = BackendDict(CloudTrailBackend, "cloudtrail")
