import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


class S3NotificationEvent(str, Enum):
    REDUCED_REDUNDANCY_LOST_OBJECT_EVENT = "s3:ReducedRedundancyLostObject"
    OBJECT_CREATED_EVENT = "s3:ObjectCreated:*"
    OBJECT_CREATED_PUT_EVENT = "s3:ObjectCreated:Put"
    OBJECT_CREATED_POST_EVENT = "s3:ObjectCreated:Post"
    OBJECT_CREATED_COPY_EVENT = "s3:ObjectCreated:Copy"
    OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD_EVENT = (
        "s3:ObjectCreated:CompleteMultipartUpload"
    )
    OBJECT_REMOVED_EVENT = "s3:ObjectRemoved:*"
    OBJECT_REMOVED_DELETE_EVENT = "s3:ObjectRemoved:Delete"
    OBJECT_REMOVED_DELETE_MARKER_CREATED_EVENT = "s3:ObjectRemoved:DeleteMarkerCreated"
    OBJECT_RESTORE_EVENT = "s3:ObjectRestore:*"
    OBJECT_RESTORE_POST_EVENT = "s3:ObjectRestore:Post"
    OBJECT_RESTORE_COMPLETED_EVENT = "s3:ObjectRestore:Completed"
    REPLICATION_EVENT = "s3:Replication:*"
    REPLICATION_OPERATION_FAILED_REPLICATION_EVENT = (
        "s3:Replication:OperationFailedReplication"
    )
    REPLICATION_OPERATION_NOT_TRACKED_EVENT = "s3:Replication:OperationNotTracked"
    REPLICATION_OPERATION_MISSED_THRESHOLD_EVENT = (
        "s3:Replication:OperationMissedThreshold"
    )
    REPLICATION_OPERATION_REPLICATED_AFTER_THRESHOLD_EVENT = (
        "s3:Replication:OperationReplicatedAfterThreshold"
    )
    OBJECT_RESTORE_DELETE_EVENT = "s3:ObjectRestore:Delete"
    LIFECYCLE_TRANSITION_EVENT = "s3:LifecycleTransition"
    INTELLIGENT_TIERING_EVENT = "s3:IntelligentTiering"
    OBJECT_ACL_EVENT = "s3:ObjectAcl:Put"
    LIFECYCLE_EXPIRATION_EVENT = "s3:LifecycleExpiration:*"
    LIFECYCLEEXPIRATION_DELETE_EVENT = "s3:LifecycleExpiration:Delete"
    LIFECYCLE_EXPIRATION_DELETE_MARKER_CREATED_EVENT = (
        "s3:LifecycleExpiration:DeleteMarkerCreated"
    )
    OBJECT_TAGGING_EVENT = "s3:ObjectTagging:*"
    OBJECT_TAGGING_PUT_EVENT = "s3:ObjectTagging:Put"
    OBJECT_TAGGING_DELETE_EVENT = "s3:ObjectTagging:Delete"

    @classmethod
    def events(self) -> List[str]:
        return sorted([item.value for item in S3NotificationEvent])

    @classmethod
    def is_event_valid(self, event_name: str) -> bool:
        # Ex) s3:ObjectCreated:Put
        if event_name in self.events():
            return True
        # Ex) event name without `s3:` like ObjectCreated:Put
        if event_name in [e[:3] for e in self.events()]:
            return True
        return False


def _get_s3_event(
    event_name: str, bucket: Any, key: Any, notification_id: str
) -> Dict[str, List[Dict[str, Any]]]:
    etag = key.etag.replace('"', "")
    # s3:ObjectCreated:Put --> ObjectCreated:Put
    event_name = event_name[3:]
    event_time = datetime.now().strftime(_EVENT_TIME_FORMAT)
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": bucket.region_name,
                "eventTime": event_time,
                "eventName": event_name,
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": notification_id,
                    "bucket": {
                        "name": bucket.name,
                        "arn": f"arn:aws:s3:::{bucket.name}",
                    },
                    "object": {"key": key.name, "size": key.size, "eTag": etag},
                },
            }
        ]
    }


def _get_region_from_arn(arn: str) -> str:
    return arn.split(":")[3]


def send_event(
    account_id: str, event_name: S3NotificationEvent, bucket: Any, key: Any
) -> None:
    if bucket.notification_configuration is None:
        return

    for notification in bucket.notification_configuration.cloud_function:
        if notification.matches(event_name, key.name):
            event_body = _get_s3_event(event_name, bucket, key, notification.id)
            region_name = _get_region_from_arn(notification.arn)

            _invoke_awslambda(account_id, event_body, notification.arn, region_name)

    for notification in bucket.notification_configuration.queue:
        if notification.matches(event_name, key.name):
            event_body = _get_s3_event(event_name, bucket, key, notification.id)
            region_name = _get_region_from_arn(notification.arn)
            queue_name = notification.arn.split(":")[-1]

            _send_sqs_message(account_id, event_body, queue_name, region_name)

    for notification in bucket.notification_configuration.topic:
        if notification.matches(event_name, key.name):
            event_body = _get_s3_event(event_name, bucket, key, notification.id)
            region_name = _get_region_from_arn(notification.arn)
            topic_arn = notification.arn

            _send_sns_message(account_id, event_body, topic_arn, region_name)


def _send_sqs_message(
    account_id: str, event_body: Any, queue_name: str, region_name: str
) -> None:
    try:
        from moto.sqs.models import sqs_backends

        sqs_backend = sqs_backends[account_id][region_name]
        sqs_backend.send_message(
            queue_name=queue_name, message_body=json.dumps(event_body)
        )
    except:  # noqa
        # This is an async action in AWS.
        # Even if this part fails, the calling function should pass, so catch all errors
        # Possible exceptions that could be thrown:
        # - Queue does not exist
        pass


def _send_sns_message(
    account_id: str, event_body: Any, topic_arn: str, region_name: str
) -> None:
    try:
        from moto.sns.models import sns_backends

        sns_backend = sns_backends[account_id][region_name]
        sns_backend.publish(arn=topic_arn, message=json.dumps(event_body))
    except:  # noqa
        # This is an async action in AWS.
        # Even if this part fails, the calling function should pass, so catch all errors
        # Possible exceptions that could be thrown:
        # - Topic does not exist
        pass


def _invoke_awslambda(
    account_id: str, event_body: Any, fn_arn: str, region_name: str
) -> None:
    try:
        from moto.awslambda.utils import get_backend

        lambda_backend = get_backend(account_id, region_name)
        func = lambda_backend.get_function(fn_arn)
        func.invoke(json.dumps(event_body), dict(), dict())
    except:  # noqa
        # This is an async action in AWS.
        # Even if this part fails, the calling function should pass, so catch all errors
        # Possible exceptions that could be thrown:
        # - Function does not exist
        pass


def _get_test_event(bucket_name: str) -> Dict[str, Any]:
    event_time = datetime.now().strftime(_EVENT_TIME_FORMAT)
    return {
        "Service": "Amazon S3",
        "Event": "s3:TestEvent",
        "Time": event_time,
        "Bucket": bucket_name,
    }


def send_test_event(account_id: str, bucket: Any) -> None:
    arns = [n.arn for n in bucket.notification_configuration.queue]
    for arn in set(arns):
        region_name = _get_region_from_arn(arn)
        queue_name = arn.split(":")[-1]
        message_body = _get_test_event(bucket.name)
        _send_sqs_message(account_id, message_body, queue_name, region_name)

    arns = [n.arn for n in bucket.notification_configuration.topic]
    for arn in set(arns):
        region_name = _get_region_from_arn(arn)
        message_body = _get_test_event(bucket.name)
        _send_sns_message(account_id, message_body, arn, region_name)
