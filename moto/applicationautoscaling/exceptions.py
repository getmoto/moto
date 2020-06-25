from __future__ import unicode_literals
import json


class AWSError(Exception):
    TYPE = None
    STATUS = 400

    def __init__(self, message):
        self.message = message

    def response(self):
        resp = {"__type": self.TYPE, "message": self.message}
        return json.dumps(resp), dict(status=self.STATUS)


class AWSValidationException(AWSError):
    TYPE = "ValidationException"


"""
{
  "Error": {
    "Message": "2 validation errors detected: Value 'bar' at 'scalableDimension' failed to satisfy constraint: Member must satisfy enum value set: [cassandra:table:ReadCapacityUnits, dynamodb:table:ReadCapacityUnits, dynamodb:index:ReadCapacityUnits, rds:cluster:ReadReplicaCount, comprehend:document-classifier-endpoint:DesiredInferenceUnits, elasticmapreduce:instancefleet:SpotCapacity, lambda:function:ProvisionedConcurrency, appstream:fleet:DesiredCapacity, dynamodb:index:WriteCapacityUnits, elasticmapreduce:instancefleet:OnDemandCapacity, rds:cluster:Capacity, cassandra:table:WriteCapacityUnits, dynamodb:table:WriteCapacityUnits, custom-resource:ResourceType:Property, sagemaker:variant:DesiredInstanceCount, ec2:spot-fleet-request:TargetCapacity, elasticmapreduce:instancegroup:InstanceCount, ecs:service:DesiredCount]; Value '' at 'serviceNamespace' failed to satisfy constraint: Member must satisfy enum value set: [appstream, rds, lambda, cassandra, dynamodb, custom-resource, elasticmapreduce, ec2, comprehend, ecs, sagemaker]",
    "Code": "ValidationException"
  },
  "ResponseMetadata": {
    "RequestId": "824468b7-c1d9-417e-b0d4-13539ecae0a0",
    "HTTPStatusCode": 400,
    "HTTPHeaders": {
      "x-amzn-requestid": "824468b7-c1d9-417e-b0d4-13539ecae0a0",
      "content-type": "application/x-amz-json-1.1",
      "content-length": "1069",
      "date": "Wed, 24 Jun 2020 19:32:19 GMT",
      "connection": "close"
    },
    "RetryAttempts": 0
  }
}
"""