from __future__ import unicode_literals

import importlib

BACKENDS = {
    "acm": ("acm", "acm_backends"),
    "apigateway": ("apigateway", "apigateway_backends"),
    "athena": ("athena", "athena_backends"),
    "autoscaling": ("autoscaling", "autoscaling_backends"),
    "batch": ("batch", "batch_backends"),
    "cloudformation": ("cloudformation", "cloudformation_backends"),
    "cloudwatch": ("cloudwatch", "cloudwatch_backends"),
    "codecommit": ("codecommit", "codecommit_backends"),
    "codepipeline": ("codepipeline", "codepipeline_backends"),
    "cognito-identity": ("cognitoidentity", "cognitoidentity_backends"),
    "cognito-idp": ("cognitoidp", "cognitoidp_backends"),
    "config": ("config", "config_backends"),
    "datapipeline": ("datapipeline", "datapipeline_backends"),
    "datasync": ("datasync", "datasync_backends"),
    "dynamodb": ("dynamodb", "dynamodb_backends"),
    "dynamodb2": ("dynamodb2", "dynamodb_backends2"),
    "dynamodbstreams": ("dynamodbstreams", "dynamodbstreams_backends"),
    "ec2": ("ec2", "ec2_backends"),
    "ec2instanceconnect": ("ec2instanceconnect", "ec2instanceconnect_backends"),
    "ecr": ("ecr", "ecr_backends"),
    "ecs": ("ecs", "ecs_backends"),
    "elasticbeanstalk": ("elasticbeanstalk", "eb_backends"),
    "elb": ("elb", "elb_backends"),
    "elbv2": ("elbv2", "elbv2_backends"),
    "emr": ("emr", "emr_backends"),
    "events": ("events", "events_backends"),
    "glacier": ("glacier", "glacier_backends"),
    "glue": ("glue", "glue_backends"),
    "iam": ("iam", "iam_backends"),
    "instance_metadata": ("instance_metadata", "instance_metadata_backends"),
    "iot": ("iot", "iot_backends"),
    "iot-data": ("iotdata", "iotdata_backends"),
    "kinesis": ("kinesis", "kinesis_backends"),
    "kms": ("kms", "kms_backends"),
    "lambda": ("awslambda", "lambda_backends"),
    "logs": ("logs", "logs_backends"),
    "managedblockchain": ("managedblockchain", "managedblockchain_backends"),
    "moto_api": ("core", "moto_api_backends"),
    "opsworks": ("opsworks", "opsworks_backends"),
    "organizations": ("organizations", "organizations_backends"),
    "polly": ("polly", "polly_backends"),
    "rds": ("rds2", "rds2_backends"),
    "redshift": ("redshift", "redshift_backends"),
    "resource-groups": ("resourcegroups", "resourcegroups_backends"),
    "resourcegroupstaggingapi": (
        "resourcegroupstaggingapi",
        "resourcegroupstaggingapi_backends",
    ),
    "route53": ("route53", "route53_backends"),
    "s3": ("s3", "s3_backends"),
    "s3bucket_path": ("s3", "s3_backends"),
    "secretsmanager": ("secretsmanager", "secretsmanager_backends"),
    "ses": ("ses", "ses_backends"),
    "sns": ("sns", "sns_backends"),
    "sqs": ("sqs", "sqs_backends"),
    "ssm": ("ssm", "ssm_backends"),
    "stepfunctions": ("stepfunctions", "stepfunction_backends"),
    "sts": ("sts", "sts_backends"),
    "swf": ("swf", "swf_backends"),
    "xray": ("xray", "xray_backends"),
}


def _import_backend(module_name, backends_name):
    module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


def backends():
    for module_name, backends_name in BACKENDS.values():
        yield _import_backend(module_name, backends_name)


def named_backends():
    for name, (module_name, backends_name) in BACKENDS.items():
        yield name, _import_backend(module_name, backends_name)


def get_backend(name):
    module_name, backends_name = BACKENDS[name]
    return _import_backend(module_name, backends_name)


def search_backend(predicate):
    for name, backend in named_backends():
        if predicate(backend):
            return name


def get_model(name, region_name):
    for backends_ in backends():
        for region, backend in backends_.items():
            if region == region_name:
                models = getattr(backend.__class__, "__models__", {})
                if name in models:
                    return list(getattr(backend, models[name])())
