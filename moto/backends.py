from __future__ import unicode_literals
import importlib


_backends = {
    'acm': 'moto.acm.acm_backends',
    'apigateway': 'moto.apigateway.apigateway_backends',
    'autoscaling': 'moto.autoscaling.autoscaling_backends',
    'batch': 'moto.batch.batch_backends',
    'cloudformation': 'moto.cloudformation.cloudformation_backends',
    'cloudwatch': 'moto.cloudwatch.cloudwatch_backends',
    'cognito-identity': 'moto.cognitoidentity.cognitoidentity_backends',
    'cognito-idp': 'moto.cognitoidp.cognitoidp_backends',
    'config': 'moto.config.config_backends',
    'datapipeline': 'moto.datapipeline.datapipeline_backends',
    'dynamodb': 'moto.dynamodb.dynamodb_backends',
    'dynamodb2': 'moto.dynamodb2.dynamodb_backends2',
    'dynamodbstreams': 'moto.dynamodbstreams.dynamodbstreams_backends',
    'ec2': 'moto.ec2.ec2_backends',
    'ecr': 'moto.ecr.ecr_backends',
    'ecs': 'moto.ecs.ecs_backends',
    'elb': 'moto.elb.elb_backends',
    'elbv2': 'moto.elbv2.elbv2_backends',
    'events': 'moto.events.events_backends',
    'emr': 'moto.emr.emr_backends',
    'glacier': 'moto.glacier.glacier_backends',
    'glue': 'moto.glue.glue_backends',
    'iam': 'moto.iam.iam_backends',
    'moto_api': 'moto.core.moto_api_backends',
    'instance_metadata': 'moto.instance_metadata.instance_metadata_backends',
    'logs': 'moto.logs.logs_backends',
    'kinesis': 'moto.kinesis.kinesis_backends',
    'kms': 'moto.kms.kms_backends',
    'opsworks': 'moto.opsworks.opsworks_backends',
    'organizations': 'moto.organizations.organizations_backends',
    'polly': 'moto.polly.polly_backends',
    'redshift': 'moto.redshift.redshift_backends',
    'resource-groups': 'moto.resourcegroups.resourcegroups_backends',
    'rds': 'moto.rds2.rds2_backends',
    's3': 'moto.s3.s3_backends',
    's3bucket_path': 'moto.s3.s3_backends',
    'ses': 'moto.ses.ses_backends',
    'secretsmanager': 'moto.secretsmanager.secretsmanager_backends',
    'sns': 'moto.sns.sns_backends',
    'sqs': 'moto.sqs.sqs_backends',
    'ssm': 'moto.ssm.ssm_backends',
    'sts': 'moto.sts.sts_backends',
    'swf': 'moto.swf.swf_backends',
    'route53': 'moto.route53.route53_backends',
    'lambda': 'moto.awslambda.lambda_backends',
    'xray': 'moto.xray.xray_backends',
    'resourcegroupstaggingapi': 'moto.resourcegroupstaggingapi.resourcegroupstaggingapi_backends',
    'iot': 'moto.iot.iot_backends',
    'iot-data': 'moto.iotdata.iotdata_backends',
}


def get_backend(backend_name):
    import_path = _backends.get(backend_name)
    if import_path is None:
        raise ValueError(
            "No such backend '%s'. Available backends are: %s" % (backend_name, ', '.join(_backends.keys()))
        )
    module_path, member_name = import_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, member_name)


def get_model(name, region_name):
    for backend_name in _backends.keys():
        backends = get_backend(backend_name)
        for region, backend in backends.items():
            if region == region_name:
                models = getattr(backend.__class__, '__models__', {})
                if name in models:
                    return list(getattr(backend, models[name])())
