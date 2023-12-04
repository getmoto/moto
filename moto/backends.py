import importlib
import sys
from typing import TYPE_CHECKING, Iterable, Tuple, Union, overload

import moto

if TYPE_CHECKING:
    from typing_extensions import Literal

    from moto.acm.models import AWSCertificateManagerBackend
    from moto.acmpca.models import ACMPCABackend
    from moto.amp.models import PrometheusServiceBackend
    from moto.apigateway.models import APIGatewayBackend
    from moto.apigatewaymanagementapi.models import ApiGatewayManagementApiBackend
    from moto.apigatewayv2.models import ApiGatewayV2Backend
    from moto.appconfig.models import AppConfigBackend
    from moto.applicationautoscaling.models import ApplicationAutoscalingBackend
    from moto.appsync.models import AppSyncBackend
    from moto.athena.models import AthenaBackend
    from moto.autoscaling.models import AutoScalingBackend
    from moto.awslambda.models import LambdaBackend
    from moto.batch.models import BatchBackend
    from moto.budgets.models import BudgetsBackend
    from moto.ce.models import CostExplorerBackend
    from moto.cloudformation.models import CloudFormationBackend
    from moto.cloudfront.models import CloudFrontBackend
    from moto.cloudtrail.models import CloudTrailBackend
    from moto.cloudwatch.models import CloudWatchBackend
    from moto.codebuild.models import CodeBuildBackend
    from moto.codecommit.models import CodeCommitBackend
    from moto.codepipeline.models import CodePipelineBackend
    from moto.cognitoidentity.models import CognitoIdentityBackend
    from moto.cognitoidp.models import CognitoIdpBackend
    from moto.comprehend.models import ComprehendBackend
    from moto.config.models import ConfigBackend
    from moto.core import SERVICE_BACKEND, BackendDict, BaseBackend
    from moto.databrew.models import DataBrewBackend
    from moto.datapipeline.models import DataPipelineBackend
    from moto.datasync.models import DataSyncBackend
    from moto.dax.models import DAXBackend
    from moto.dms.models import DatabaseMigrationServiceBackend
    from moto.ds.models import DirectoryServiceBackend
    from moto.dynamodb.models import DynamoDBBackend
    from moto.dynamodb_v20111205.models import (
        DynamoDBBackend as DynamoDBBackend_v20111205,
    )
    from moto.dynamodbstreams.models import DynamoDBStreamsBackend
    from moto.ebs.models import EBSBackend
    from moto.ec2.models import EC2Backend
    from moto.ec2instanceconnect.models import Ec2InstanceConnectBackend
    from moto.ecr.models import ECRBackend
    from moto.ecs.models import EC2ContainerServiceBackend
    from moto.efs.models import EFSBackend
    from moto.eks.models import EKSBackend
    from moto.elasticache.models import ElastiCacheBackend
    from moto.elasticbeanstalk.models import EBBackend
    from moto.elastictranscoder.models import ElasticTranscoderBackend
    from moto.elb.models import ELBBackend
    from moto.elbv2.models import ELBv2Backend
    from moto.emr.models import ElasticMapReduceBackend
    from moto.emrcontainers.models import EMRContainersBackend
    from moto.emrserverless.models import EMRServerlessBackend
    from moto.es.models import ElasticsearchServiceBackend
    from moto.events.models import EventsBackend
    from moto.firehose.models import FirehoseBackend
    from moto.forecast.models import ForecastBackend
    from moto.glacier.models import GlacierBackend
    from moto.glue.models import GlueBackend
    from moto.greengrass.models import GreengrassBackend
    from moto.guardduty.models import GuardDutyBackend
    from moto.iam.models import IAMBackend
    from moto.identitystore.models import IdentityStoreBackend
    from moto.inspector2.models import Inspector2Backend
    from moto.instance_metadata.models import InstanceMetadataBackend
    from moto.iot.models import IoTBackend
    from moto.iotdata.models import IoTDataPlaneBackend
    from moto.ivs.models import IVSBackend
    from moto.kinesis.models import KinesisBackend
    from moto.kinesisvideo.models import KinesisVideoBackend
    from moto.kinesisvideoarchivedmedia.models import KinesisVideoArchivedMediaBackend
    from moto.kms.models import KmsBackend
    from moto.lakeformation.models import LakeFormationBackend
    from moto.logs.models import LogsBackend
    from moto.managedblockchain.models import ManagedBlockchainBackend
    from moto.mediaconnect.models import MediaConnectBackend
    from moto.medialive.models import MediaLiveBackend
    from moto.mediapackage.models import MediaPackageBackend
    from moto.mediastore.models import MediaStoreBackend
    from moto.mediastoredata.models import MediaStoreDataBackend
    from moto.meteringmarketplace.models import MeteringMarketplaceBackend
    from moto.moto_api._internal.models import MotoAPIBackend
    from moto.mq.models import MQBackend
    from moto.neptune.models import NeptuneBackend
    from moto.opensearch.models import OpenSearchServiceBackend
    from moto.opsworks.models import OpsWorksBackend
    from moto.organizations.models import OrganizationsBackend
    from moto.personalize.models import PersonalizeBackend
    from moto.pinpoint.models import PinpointBackend
    from moto.polly.models import PollyBackend
    from moto.quicksight.models import QuickSightBackend
    from moto.ram.models import ResourceAccessManagerBackend
    from moto.rds.models import RDSBackend
    from moto.rdsdata.models import RDSDataServiceBackend
    from moto.redshift.models import RedshiftBackend
    from moto.redshiftdata.models import RedshiftDataAPIServiceBackend
    from moto.rekognition.models import RekognitionBackend
    from moto.resourcegroups.models import ResourceGroupsBackend
    from moto.resourcegroupstaggingapi.models import ResourceGroupsTaggingAPIBackend
    from moto.robomaker.models import RoboMakerBackend
    from moto.route53.models import Route53Backend
    from moto.route53resolver.models import Route53ResolverBackend
    from moto.s3.models import S3Backend
    from moto.s3control.models import S3ControlBackend
    from moto.sagemaker.models import SageMakerModelBackend
    from moto.sagemakerruntime.models import SageMakerRuntimeBackend
    from moto.scheduler.models import EventBridgeSchedulerBackend
    from moto.sdb.models import SimpleDBBackend
    from moto.secretsmanager.models import SecretsManagerBackend
    from moto.servicediscovery.models import ServiceDiscoveryBackend
    from moto.servicequotas.models import ServiceQuotasBackend
    from moto.ses.models import SESBackend
    from moto.sesv2.models import SESV2Backend
    from moto.signer.models import SignerBackend
    from moto.sns.models import SNSBackend
    from moto.sqs.models import SQSBackend
    from moto.ssm.models import SimpleSystemManagerBackend
    from moto.ssoadmin.models import SSOAdminBackend
    from moto.stepfunctions.models import StepFunctionBackend
    from moto.sts.models import STSBackend
    from moto.support.models import SupportBackend
    from moto.swf.models import SWFBackend
    from moto.textract.models import TextractBackend
    from moto.timestreamwrite.models import TimestreamWriteBackend
    from moto.transcribe.models import TranscribeBackend
    from moto.wafv2.models import WAFV2Backend
    from moto.xray.models import XRayBackend


decorators = [d for d in dir(moto) if d.startswith("mock_") and not d == "mock_all"]
decorator_functions = [getattr(moto, f) for f in decorators]
BACKENDS = {f.boto3_name: (f.name, f.backend) for f in decorator_functions}
BACKENDS["dynamodb_v20111205"] = ("dynamodb_v20111205", "dynamodb_backends")
BACKENDS["moto_api"] = ("moto_api._internal", "moto_api_backends")
BACKENDS["instance_metadata"] = ("instance_metadata", "instance_metadata_backends")
BACKENDS["s3bucket_path"] = ("s3", "s3_backends")

# There's a similar Union that we could import from boto3-stubs, but it wouldn't have
# moto's custom service backends
SERVICE_NAMES = Union[
    "Literal['acm']",
    "Literal['acm-pca']",
    "Literal['amp']",
    "Literal['apigateway']",
    "Literal['apigatewaymanagementapi']",
    "Literal['apigatewayv2']",
    "Literal['appconfig']",
    "Literal['applicationautoscaling']",
    "Literal['appsync']",
    "Literal['athena']",
    "Literal['autoscaling']",
    "Literal['batch']",
    "Literal['budgets']",
    "Literal['ce']",
    "Literal['cloudformation']",
    "Literal['cloudfront']",
    "Literal['cloudtrail']",
    "Literal['cloudwatch']",
    "Literal['codebuild']",
    "Literal['codecommit']",
    "Literal['codepipeline']",
    "Literal['cognito-identity']",
    "Literal['cognito-idp']",
    "Literal['comprehend']",
    "Literal['config']",
    "Literal['databrew']",
    "Literal['datapipeline']",
    "Literal['datasync']",
    "Literal['dax']",
    "Literal['dms']",
    "Literal['ds']",
    "Literal['dynamodb']",
    "Literal['dynamodb_v20111205']",
    "Literal['dynamodbstreams']",
    "Literal['ebs']",
    "Literal['ec2']",
    "Literal['ec2instanceconnect']",
    "Literal['ecr']",
    "Literal['ecs']",
    "Literal['efs']",
    "Literal['eks']",
    "Literal['elasticache']",
    "Literal['elasticbeanstalk']",
    "Literal['elastictranscoder']",
    "Literal['elb']",
    "Literal['elbv2']",
    "Literal['emr']",
    "Literal['emr-containers']",
    "Literal['emr-serverless']",
    "Literal['es']",
    "Literal['events']",
    "Literal['firehose']",
    "Literal['forecast']",
    "Literal['glacier']",
    "Literal['glue']",
    "Literal['greengrass']",
    "Literal['guardduty']",
    "Literal['iam']",
    "Literal['identitystore']",
    "Literal['inspector2']",
    "Literal['instance_metadata']",
    "Literal['iot']",
    "Literal['iot-data']",
    "Literal['ivs']",
    "Literal['kinesis']",
    "Literal['kinesisvideo']",
    "Literal['kinesis-video-archived-media']",
    "Literal['kms']",
    "Literal['lakeformation']",
    "Literal['lambda']",
    "Literal['logs']",
    "Literal['managedblockchain']",
    "Literal['mediaconnect']",
    "Literal['medialive']",
    "Literal['mediapackage']",
    "Literal['mediastore']",
    "Literal['mediastore-data']",
    "Literal['meteringmarketplace']",
    "Literal['moto_api']",
    "Literal['mq']",
    "Literal['neptune']",
    "Literal['opensearch']",
    "Literal['opsworks']",
    "Literal['organizations']",
    "Literal['personalize']",
    "Literal['pinpoint']",
    "Literal['polly']",
    "Literal['quicksight']",
    "Literal['ram']",
    "Literal['rds']",
    "Literal['rds-data']",
    "Literal['redshift']",
    "Literal['redshift-data']",
    "Literal['rekognition']",
    "Literal['resource-groups']",
    "Literal['resourcegroupstaggingapi']",
    "Literal['robomaker']",
    "Literal['route53']",
    "Literal['route53resolver']",
    "Literal['s3']",
    "Literal['s3bucket_path']",
    "Literal['s3control']",
    "Literal['sagemaker']",
    "Literal['sagemaker-runtime']",
    "Literal['scheduler']",
    "Literal['sdb']",
    "Literal['secretsmanager']",
    "Literal['servicediscovery']",
    "Literal['service-quotas']",
    "Literal['ses']",
    "Literal['sesv2']",
    "Literal['signer']",
    "Literal['sns']",
    "Literal['sqs']",
    "Literal['ssm']",
    "Literal['sso-admin']",
    "Literal['stepfunctions']",
    "Literal['sts']",
    "Literal['support']",
    "Literal['swf']",
    "Literal['textract']",
    "Literal['timestream-write']",
    "Literal['transcribe']",
    "Literal['wafv2']",
    "Literal['xray']",
]


def _import_backend(
    module_name: str,
    backends_name: str,
) -> "BackendDict[SERVICE_BACKEND]":
    module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


def backends() -> "Iterable[BackendDict[BaseBackend]]":
    for module_name, backends_name in BACKENDS.values():
        yield _import_backend(module_name, backends_name)


def service_backends() -> "Iterable[BackendDict[BaseBackend]]":
    services = [(f.name, f.backend) for f in decorator_functions]
    for module_name, backends_name in sorted(set(services)):
        yield _import_backend(module_name, backends_name)


def loaded_backends() -> "Iterable[Tuple[str, BackendDict[BaseBackend]]]":
    loaded_modules = sys.modules.keys()
    moto_modules = [m for m in loaded_modules if m.startswith("moto.")]
    imported_backends = [
        name
        for name, (module_name, _) in BACKENDS.items()
        if f"moto.{module_name}" in moto_modules
    ]
    for name in imported_backends:
        module_name, backends_name = BACKENDS[name]
        yield name, _import_backend(module_name, backends_name)


# fmt: off
# This is more or less the dummy-implementation style that's currently in black's preview
# style. It should be live in black v24.0+, at which point we should remove the # fmt: off
# directive.
@overload
def get_backend(name: "Literal['acm']") -> "BackendDict[AWSCertificateManagerBackend]": ...
@overload
def get_backend(name: "Literal['acm-pca']") -> "BackendDict[ACMPCABackend]": ...
@overload
def get_backend(name: "Literal['amp']") -> "BackendDict[PrometheusServiceBackend]": ...
@overload
def get_backend(name: "Literal['apigateway']") -> "BackendDict[APIGatewayBackend]": ...
@overload
def get_backend(name: "Literal['apigatewaymanagementapi']") -> "BackendDict[ApiGatewayManagementApiBackend]": ...
@overload
def get_backend(name: "Literal['apigatewayv2']") -> "BackendDict[ApiGatewayV2Backend]": ...
@overload
def get_backend(name: "Literal['appconfig']") -> "BackendDict[AppConfigBackend]": ...
@overload
def get_backend(name: "Literal['applicationautoscaling']") -> "BackendDict[ApplicationAutoscalingBackend]": ...
@overload
def get_backend(name: "Literal['appsync']") -> "BackendDict[AppSyncBackend]": ...
@overload
def get_backend(name: "Literal['athena']") -> "BackendDict[AthenaBackend]": ...
@overload
def get_backend(name: "Literal['autoscaling']") -> "BackendDict[AutoScalingBackend]": ...
@overload
def get_backend(name: "Literal['batch']") -> "BackendDict[BatchBackend]": ...
@overload
def get_backend(name: "Literal['budgets']") -> "BackendDict[BudgetsBackend]": ...
@overload
def get_backend(name: "Literal['ce']") -> "BackendDict[CostExplorerBackend]": ...
@overload
def get_backend(name: "Literal['cloudformation']") -> "BackendDict[CloudFormationBackend]": ...
@overload
def get_backend(name: "Literal['cloudfront']") -> "BackendDict[CloudFrontBackend]": ...
@overload
def get_backend(name: "Literal['cloudtrail']") -> "BackendDict[CloudTrailBackend]": ...
@overload
def get_backend(name: "Literal['cloudwatch']") -> "BackendDict[CloudWatchBackend]": ...
@overload
def get_backend(name: "Literal['codebuild']") -> "BackendDict[CodeBuildBackend]": ...
@overload
def get_backend(name: "Literal['codecommit']") -> "BackendDict[CodeCommitBackend]": ...
@overload
def get_backend(name: "Literal['codepipeline']") -> "BackendDict[CodePipelineBackend]": ...
@overload
def get_backend(name: "Literal['cognito-identity']") -> "BackendDict[CognitoIdentityBackend]": ...
@overload
def get_backend(name: "Literal['cognito-idp']") -> "BackendDict[CognitoIdpBackend]": ...
@overload
def get_backend(name: "Literal['comprehend']") -> "BackendDict[ComprehendBackend]": ...
@overload
def get_backend(name: "Literal['config']") -> "BackendDict[ConfigBackend]": ...
@overload
def get_backend(name: "Literal['databrew']") -> "BackendDict[DataBrewBackend]": ...
@overload
def get_backend(name: "Literal['datapipeline']") -> "BackendDict[DataPipelineBackend]": ...
@overload
def get_backend(name: "Literal['datasync']") -> "BackendDict[DataSyncBackend]": ...
@overload
def get_backend(name: "Literal['dax']") -> "BackendDict[DAXBackend]": ...
@overload
def get_backend(name: "Literal['dms']") -> "BackendDict[DatabaseMigrationServiceBackend]": ...
@overload
def get_backend(name: "Literal['ds']") -> "BackendDict[DirectoryServiceBackend]": ...
@overload
def get_backend(name: "Literal['dynamodb']") -> "BackendDict[DynamoDBBackend]": ...
@overload
def get_backend(name: "Literal['dynamodb_v20111205']") -> "BackendDict[DynamoDBBackend_v20111205]": ...
@overload
def get_backend(name: "Literal['dynamodbstreams']") -> "BackendDict[DynamoDBStreamsBackend]": ...
@overload
def get_backend(name: "Literal['ebs']") -> "BackendDict[EBSBackend]": ...
@overload
def get_backend(name: "Literal['ec2']") -> "BackendDict[EC2Backend]": ...
@overload
def get_backend(name: "Literal['ec2instanceconnect']") -> "BackendDict[Ec2InstanceConnectBackend]": ...
@overload
def get_backend(name: "Literal['ecr']") -> "BackendDict[ECRBackend]": ...
@overload
def get_backend(name: "Literal['ecs']") -> "BackendDict[EC2ContainerServiceBackend]": ...
@overload
def get_backend(name: "Literal['efs']") -> "BackendDict[EFSBackend]": ...
@overload
def get_backend(name: "Literal['eks']") -> "BackendDict[EKSBackend]": ...
@overload
def get_backend(name: "Literal['elasticache']") -> "BackendDict[ElastiCacheBackend]": ...
@overload
def get_backend(name: "Literal['elasticbeanstalk']") -> "BackendDict[EBBackend]": ...
@overload
def get_backend(name: "Literal['elastictranscoder']") -> "BackendDict[ElasticTranscoderBackend]": ...
@overload
def get_backend(name: "Literal['elb']") -> "BackendDict[ELBBackend]": ...
@overload
def get_backend(name: "Literal['elbv2']") -> "BackendDict[ELBv2Backend]": ...
@overload
def get_backend(name: "Literal['emr']") -> "BackendDict[ElasticMapReduceBackend]": ...
@overload
def get_backend(name: "Literal['emr-containers']") -> "BackendDict[EMRContainersBackend]": ...
@overload
def get_backend(name: "Literal['emr-serverless']") -> "BackendDict[EMRServerlessBackend]": ...
@overload
def get_backend(name: "Literal['es']") -> "BackendDict[ElasticsearchServiceBackend]": ...
@overload
def get_backend(name: "Literal['events']") -> "BackendDict[EventsBackend]": ...
@overload
def get_backend(name: "Literal['firehose']") -> "BackendDict[FirehoseBackend]": ...
@overload
def get_backend(name: "Literal['forecast']") -> "BackendDict[ForecastBackend]": ...
@overload
def get_backend(name: "Literal['glacier']") -> "BackendDict[GlacierBackend]": ...
@overload
def get_backend(name: "Literal['glue']") -> "BackendDict[GlueBackend]": ...
@overload
def get_backend(name: "Literal['greengrass']") -> "BackendDict[GreengrassBackend]": ...
@overload
def get_backend(name: "Literal['guardduty']") -> "BackendDict[GuardDutyBackend]": ...
@overload
def get_backend(name: "Literal['iam']") -> "BackendDict[IAMBackend]": ...
@overload
def get_backend(name: "Literal['identitystore']") -> "BackendDict[IdentityStoreBackend]": ...
@overload
def get_backend(name: "Literal['inspector2']") -> "BackendDict[Inspector2Backend]": ...
@overload
def get_backend(name: "Literal['instance_metadata']") -> "BackendDict[InstanceMetadataBackend]": ...
@overload
def get_backend(name: "Literal['iot']") -> "BackendDict[IoTBackend]": ...
@overload
def get_backend(name: "Literal['iot-data']") -> "BackendDict[IoTDataPlaneBackend]": ...
@overload
def get_backend(name: "Literal['ivs']") -> "BackendDict[IVSBackend]": ...
@overload
def get_backend(name: "Literal['kinesis']") -> "BackendDict[KinesisBackend]": ...
@overload
def get_backend(name: "Literal['kinesisvideo']") -> "BackendDict[KinesisVideoBackend]": ...
@overload
def get_backend(name: "Literal['kinesis-video-archived-media']") -> "BackendDict[KinesisVideoArchivedMediaBackend]": ...
@overload
def get_backend(name: "Literal['kms']") -> "BackendDict[KmsBackend]": ...
@overload
def get_backend(name: "Literal['lakeformation']") -> "BackendDict[LakeFormationBackend]": ...
@overload
def get_backend(name: "Literal['lambda']") -> "BackendDict[LambdaBackend]": ...
@overload
def get_backend(name: "Literal['logs']") -> "BackendDict[LogsBackend]": ...
@overload
def get_backend(name: "Literal['managedblockchain']") -> "BackendDict[ManagedBlockchainBackend]": ...
@overload
def get_backend(name: "Literal['mediaconnect']") -> "BackendDict[MediaConnectBackend]": ...
@overload
def get_backend(name: "Literal['medialive']") -> "BackendDict[MediaLiveBackend]": ...
@overload
def get_backend(name: "Literal['mediapackage']") -> "BackendDict[MediaPackageBackend]": ...
@overload
def get_backend(name: "Literal['mediastore']") -> "BackendDict[MediaStoreBackend]": ...
@overload
def get_backend(name: "Literal['mediastore-data']") -> "BackendDict[MediaStoreDataBackend]": ...
@overload
def get_backend(name: "Literal['meteringmarketplace']") -> "BackendDict[MeteringMarketplaceBackend]": ...
@overload
def get_backend(name: "Literal['moto_api']") -> "BackendDict[MotoAPIBackend]": ...
@overload
def get_backend(name: "Literal['mq']") -> "BackendDict[MQBackend]": ...
@overload
def get_backend(name: "Literal['neptune']") -> "BackendDict[NeptuneBackend]": ...
@overload
def get_backend(name: "Literal['opensearch']") -> "BackendDict[OpenSearchServiceBackend]": ...
@overload
def get_backend(name: "Literal['opsworks']") -> "BackendDict[OpsWorksBackend]": ...
@overload
def get_backend(name: "Literal['organizations']") -> "BackendDict[OrganizationsBackend]": ...
@overload
def get_backend(name: "Literal['personalize']") -> "BackendDict[PersonalizeBackend]": ...
@overload
def get_backend(name: "Literal['pinpoint']") -> "BackendDict[PinpointBackend]": ...
@overload
def get_backend(name: "Literal['polly']") -> "BackendDict[PollyBackend]": ...
@overload
def get_backend(name: "Literal['quicksight']") -> "BackendDict[QuickSightBackend]": ...
@overload
def get_backend(name: "Literal['ram']") -> "BackendDict[ResourceAccessManagerBackend]": ...
@overload
def get_backend(name: "Literal['rds']") -> "BackendDict[RDSBackend]": ...
@overload
def get_backend(name: "Literal['rds-data']") -> "BackendDict[RDSDataServiceBackend]": ...
@overload
def get_backend(name: "Literal['redshift']") -> "BackendDict[RedshiftBackend]": ...
@overload
def get_backend(name: "Literal['redshift-data']") -> "BackendDict[RedshiftDataAPIServiceBackend]": ...
@overload
def get_backend(name: "Literal['rekognition']") -> "BackendDict[RekognitionBackend]": ...
@overload
def get_backend(name: "Literal['resource-groups']") -> "BackendDict[ResourceGroupsBackend]": ...
@overload
def get_backend(name: "Literal['resourcegroupstaggingapi']") -> "BackendDict[ResourceGroupsTaggingAPIBackend]": ...
@overload
def get_backend(name: "Literal['robomaker']") -> "BackendDict[RoboMakerBackend]": ...
@overload
def get_backend(name: "Literal['route53']") -> "BackendDict[Route53Backend]": ...
@overload
def get_backend(name: "Literal['route53resolver']") -> "BackendDict[Route53ResolverBackend]": ...
@overload
def get_backend(name: "Literal['s3']") -> "BackendDict[S3Backend]": ...
@overload
def get_backend(name: "Literal['s3bucket_path']") -> "BackendDict[S3Backend]": ...
@overload
def get_backend(name: "Literal['s3control']") -> "BackendDict[S3ControlBackend]": ...
@overload
def get_backend(name: "Literal['sagemaker']") -> "BackendDict[SageMakerModelBackend]": ...
@overload
def get_backend(name: "Literal['sagemaker-runtime']") -> "BackendDict[SageMakerRuntimeBackend]": ...
@overload
def get_backend(name: "Literal['scheduler']") -> "BackendDict[EventBridgeSchedulerBackend]": ...
@overload
def get_backend(name: "Literal['sdb']") -> "BackendDict[SimpleDBBackend]": ...
@overload
def get_backend(name: "Literal['secretsmanager']") -> "BackendDict[SecretsManagerBackend]": ...
@overload
def get_backend(name: "Literal['servicediscovery']") -> "BackendDict[ServiceDiscoveryBackend]": ...
@overload
def get_backend(name: "Literal['service-quotas']") -> "BackendDict[ServiceQuotasBackend]": ...
@overload
def get_backend(name: "Literal['ses']") -> "BackendDict[SESBackend]": ...
@overload
def get_backend(name: "Literal['sesv2']") -> "BackendDict[SESV2Backend]": ...
@overload
def get_backend(name: "Literal['signer']") -> "BackendDict[SignerBackend]": ...
@overload
def get_backend(name: "Literal['sns']") -> "BackendDict[SNSBackend]": ...
@overload
def get_backend(name: "Literal['sqs']") -> "BackendDict[SQSBackend]": ...
@overload
def get_backend(name: "Literal['ssm']") -> "BackendDict[SimpleSystemManagerBackend]": ...
@overload
def get_backend(name: "Literal['sso-admin']") -> "BackendDict[SSOAdminBackend]": ...
@overload
def get_backend(name: "Literal['stepfunctions']") -> "BackendDict[StepFunctionBackend]": ...
@overload
def get_backend(name: "Literal['sts']") -> "BackendDict[STSBackend]": ...
@overload
def get_backend(name: "Literal['support']") -> "BackendDict[SupportBackend]": ...
@overload
def get_backend(name: "Literal['swf']") -> "BackendDict[SWFBackend]": ...
@overload
def get_backend(name: "Literal['textract']") -> "BackendDict[TextractBackend]": ...
@overload
def get_backend(name: "Literal['timestream-write']") -> "BackendDict[TimestreamWriteBackend]": ...
@overload
def get_backend(name: "Literal['transcribe']") -> "BackendDict[TranscribeBackend]": ...
@overload
def get_backend(name: "Literal['wafv2']") -> "BackendDict[WAFV2Backend]": ...
@overload
def get_backend(name: "Literal['xray']") -> "BackendDict[XRayBackend]": ...
# fmt: on


def get_backend(name: SERVICE_NAMES) -> "BackendDict[SERVICE_BACKEND]":
    module_name, backends_name = BACKENDS[name]
    return _import_backend(module_name, backends_name)
