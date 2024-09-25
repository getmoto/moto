import json

import boto3

client = boto3.client("osis")
kwargs = {
    "PipelineName": "test-attach",
    "MinUnits": 2,
    "MaxUnits": 4,
    "PipelineConfigurationBody": "version: \"2\"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: [\"https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.us-east-1.es.amazonaws.com\"]\n      indices:\n        exclude:\n          - index_name_regex: '\\..*'\n      aws:\n        region: \"us-east-1\"\n        sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n        serverless: false\n        serverless_options:\n           network_policy_name: \"test-policy\"\n  sink:\n    - opensearch:\n        hosts: [\"https://kbjahvxo2jgx8beq2vob.us-east-1.aoss.amazonaws.com\"]\n        aws:\n          sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n          region: \"us-east-1\"\n          serverless: true\n          serverless_options:\n            network_policy_name: \"another-test-policy\"\n        index: \"${getMetadata(\\\"opensearch-index\\\")}\"\n        document_id: \"${getMetadata(\\\"opensearch-document_id\\\")}\"\n",
    "VpcOptions": {
        "SubnetIds": ["subnet-914763e7"],
        "SecurityGroupIds": ["sg-6c7fa917"],
        "VpcEndpointManagement": "SERVICE",
        "VpcAttachmentOptions": {
            "AttachToVpc": True,
            "CidrBlock": "172.16.128.0/24",
        }
    },
}
# resp = client.create_pipeline(**kwargs)
# resp = client.delete_pipeline(PipelineName="test-serverless-sink")
resp = boto3.client('opensearch').describe_domains(DomainNames=["c7ntest"])
# resp = client.start_pipeline(PipelineName="c7n-test")
# resp = client.update_pipeline(PipelineName="test-buffer", PipelineConfigurationBody="version: \"2\"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: [\"https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.us-east-1.es.amazonaws.com\"]\n      indices:\n        exclude:\n          - index_name_regex: '\\..*'\n      aws:\n        region: \"us-east-1\"\n        sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n        serverless: false\n        serverless_options:\n           network_policy_name: \"test-policy\"\n  sink:\n    - opensearch:\n        hosts: [\"https://kbjahvxo2jgx8beq2vob.us-east-1.aoss.amazonaws.com\"]\n        aws:\n          sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n          region: \"us-east-1\"\n          serverless: true\n          serverless_options:\n            network_policy_name: \"another-test-policy\"\n        index: \"${getMetadata(\\\"opensearch-index\\\")}\"\n        document_id: \"${getMetadata(\\\"opensearch-document_id\\\")}\"\n")
# resp = client.get_pipeline(PipelineName="test-no-vpc")
# resp = client.list_tags_for_resource(Arn="arn:aws:osis:us-east-1:644160558196:pipeline/c7n-vpc-test-7")
# resp = client.list_pipelines()
print(json.dumps(resp, indent=2, default=str))

# CUSTOMER VPC ENDPOINT EXAMPLE
# EVEN AFTER ENDPOINT IS CONFIGURED NOT RETURNED IN GET RESPONSE
"""
{
  "Pipeline": {
    "PipelineName": "c7n-vpc-test-3",
    "PipelineArn": "arn:aws:osis:us-east-1:644160558196:pipeline/c7n-vpc-test-3",
    "MinUnits": 2,
    "MaxUnits": 4,
    "Status": "ACTIVE",
    "StatusReason": {
      "Description": "WARN: There is no \"available\" VPC endpoint associated with this pipeline. You must configure an interface vpc endpoint to ingest data."
    },
    "PipelineConfigurationBody": "version: \"2\"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: [ \"https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com\" ]\n      indices:\n        exclude:\n          - index_name_regex: '\\..*'\n      aws:\n        region: \"us-east-1\"\n        sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n        serverless: false\n  sink:\n    - opensearch:\n        hosts: [ \"https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com\" ]\n        aws:\n          sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n          region: \"us-east-1\"\n          serverless: false\n        index: \"${getMetadata(\\\"opensearch-index\\\")}\"\n        document_id: \"${getMetadata(\\\"opensearch-document_id\\\")}\"\n\n\n",
    "CreatedAt": "2024-09-17 16:05:33-04:00",
    "LastUpdatedAt": "2024-09-17 16:05:33-04:00",
    "IngestEndpointUrls": [
      "c7n-vpc-test-3-5q2trkc4vauce44povulnryfam.us-east-1.osis.amazonaws.com"
    ],
    "VpcEndpoints": [
      {
        "VpcId": "vpc-d2d616b5",
        "VpcOptions": {
          "SubnetIds": [
            "subnet-914763e7"
          ],
          "SecurityGroupIds": [
            "sg-6c7fa917"
          ],
          "VpcAttachmentOptions": {
            "AttachToVpc": true,
            "CidrBlock": "172.21.56.0/24"
          },
          "VpcEndpointManagement": "CUSTOMER"
        }
      }
    ],
    "VpcEndpointService": "com.amazonaws.osis.us-east-1.c7n-vpc-test-3-5q2trkc4vauce44povulnryfam",
    "Destinations": [
      {
        "ServiceName": "OpenSearch",
        "Endpoint": "https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com"
      }
    ],
    "Tags": []
  }
}
"""

# SERVICE VPCE EXAMPLE
"""
{
  "Pipeline": {
    "PipelineName": "c7n-vpc-test-2",
    "PipelineArn": "arn:aws:osis:us-east-1:644160558196:pipeline/c7n-vpc-test-2",
    "MinUnits": 2,
    "MaxUnits": 4,
    "Status": "ACTIVE",
    "StatusReason": {
      "Description": "The pipeline is ready to ingest data."
    },
    "PipelineConfigurationBody": "version: \"2\"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: [ \"https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com\" ]\n      indices:\n        exclude:\n          - index_name_regex: '\\..*'\n      aws:\n        region: \"us-east-1\"\n        sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n        serverless: false\n  sink:\n    - opensearch:\n        hosts: [ \"https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com\" ]\n        aws:\n          sts_role_arn: \"arn:aws:iam::644160558196:role/CloudCustodianRole\"\n          region: \"us-east-1\"\n          serverless: false\n        index: \"${getMetadata(\\\"opensearch-index\\\")}\"\n        document_id: \"${getMetadata(\\\"opensearch-document_id\\\")}\"\n\n\n",
    "CreatedAt": "2024-09-17 16:04:14-04:00",
    "LastUpdatedAt": "2024-09-17 16:04:14-04:00",
    "IngestEndpointUrls": [
      "c7n-vpc-test-2-uqc6fa32bpmz7iaffx7votqtla.us-east-1.osis.amazonaws.com"
    ],
    "VpcEndpoints": [
      {
        "VpcEndpointId": "vpce-0831ce4117f3282cf",
        "VpcId": "vpc-d2d616b5",
        "VpcOptions": {
          "SubnetIds": [
            "subnet-914763e7"
          ],
          "SecurityGroupIds": [
            "sg-6c7fa917"
          ],
          "VpcAttachmentOptions": {
            "AttachToVpc": true,
            "CidrBlock": "172.21.56.0/24"
          },
          "VpcEndpointManagement": "SERVICE"
        }
      }
    ],
    "Destinations": [
      {
        "ServiceName": "OpenSearch",
        "Endpoint": "https://search-c7ntest-1a2a3a4a5a6a7a8a9a0a9a8a7a.us-east-1.es.amazonaws.com"
      }
    ],
    "Tags": []
  }
}
"""
