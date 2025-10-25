import aws_cdk as cdk
from aws_cdk import Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class S3EventbridgeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        s3_bucket = s3.Bucket(
            self,
            "bucket",
            access_control=s3.BucketAccessControl.PRIVATE,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        # allow s3 bucket to send notification to eventbridge
        s3_bucket.enable_event_bridge_notification()

        # Queue to send events to
        event_queue = sqs.Queue(self, id="sample_queue_id")

        # eventbridge rule to trigger when objects gets added or deleted in s3 bucket
        self.event_rule = events.Rule(
            self,
            "queueRule",
            description="Rule to trigger Queue Message",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail={"bucket": {"name": [s3_bucket.bucket_name]}},
            ),
        )
        self.event_rule.add_target(targets.SqsQueue(queue=event_queue))


app = cdk.App()
S3EventbridgeStack(app, "s3-eventbridge-queue")

app.synth()
