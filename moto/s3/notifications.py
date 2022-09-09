import json
from datetime import datetime

_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

S3_OBJECT_CREATE_COPY = "s3:ObjectCreated:Copy"
S3_OBJECT_CREATE_PUT = "s3:ObjectCreated:Put"


def _get_s3_event(event_name, bucket, key, notification_id):
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


def _get_region_from_arn(arn):
    return arn.split(":")[3]


def send_event(event_name, bucket, key):
    if bucket.notification_configuration is None:
        return

    for notification in bucket.notification_configuration.cloud_function:
        if notification.matches(event_name, key.name):
            event_body = _get_s3_event(event_name, bucket, key, notification.id)
            region_name = _get_region_from_arn(notification.arn)

            _invoke_awslambda(event_body, notification.arn, region_name)

    for notification in bucket.notification_configuration.queue:
        if notification.matches(event_name, key.name):
            event_body = _get_s3_event(event_name, bucket, key, notification.id)
            region_name = _get_region_from_arn(notification.arn)
            queue_name = notification.arn.split(":")[-1]

            _send_sqs_message(event_body, queue_name, region_name)


def _send_sqs_message(event_body, queue_name, region_name):
    try:
        from moto.sqs.models import sqs_backends

        sqs_backend = sqs_backends[region_name]
        sqs_backend.send_message(
            queue_name=queue_name, message_body=json.dumps(event_body)
        )
    except:  # noqa
        # This is an async action in AWS.
        # Even if this part fails, the calling function should pass, so catch all errors
        # Possible exceptions that could be thrown:
        # - Queue does not exist
        pass


def _invoke_awslambda(event_body, fn_arn, region_name):
    try:
        from moto.awslambda.models import lambda_backends

        lambda_backend = lambda_backends[region_name]
        func = lambda_backend.get_function(fn_arn)
        func.invoke(json.dumps(event_body), dict(), dict())
    except:  # noqa
        # This is an async action in AWS.
        # Even if this part fails, the calling function should pass, so catch all errors
        # Possible exceptions that could be thrown:
        # - Function does not exist
        pass


def _get_test_event(bucket_name):
    event_time = datetime.now().strftime(_EVENT_TIME_FORMAT)
    return {
        "Service": "Amazon S3",
        "Event": "s3:TestEvent",
        "Time": event_time,
        "Bucket": bucket_name,
    }


def send_test_event(bucket):
    arns = [n.arn for n in bucket.notification_configuration.queue]
    for arn in set(arns):
        region_name = _get_region_from_arn(arn)
        queue_name = arn.split(":")[-1]
        message_body = _get_test_event(bucket.name)
        _send_sqs_message(message_body, queue_name, region_name)
