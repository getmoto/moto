# autogenerated by moto/scripts/update_backend_index.py
import re

backend_url_patterns = [
    ("acm", re.compile("https?://acm\\.(.+)\\.amazonaws\\.com")),
    ("acmpca", re.compile("https?://acm-pca\\.(.+)\\.amazonaws\\.com")),
    ("amp", re.compile("https?://aps\\.(.+)\\.amazonaws\\.com")),
    ("apigateway", re.compile("https?://apigateway\\.(.+)\\.amazonaws.com")),
    (
        "apigatewaymanagementapi",
        re.compile("https?://execute-api\\.(.+)\\.amazonaws\\.com"),
    ),
    ("appconfig", re.compile("https?://appconfig\\.(.+)\\.amazonaws\\.com")),
    (
        "applicationautoscaling",
        re.compile("https?://application-autoscaling\\.(.+)\\.amazonaws.com"),
    ),
    ("appsync", re.compile("https?://appsync\\.(.+)\\.amazonaws\\.com")),
    ("athena", re.compile("https?://athena\\.(.+)\\.amazonaws\\.com")),
    ("autoscaling", re.compile("https?://autoscaling\\.(.+)\\.amazonaws\\.com")),
    ("awslambda", re.compile("https?://lambda\\.(.+)\\.amazonaws\\.com")),
    ("backup", re.compile("https?://backup\\.(.+)\\.amazonaws\\.com")),
    ("batch", re.compile("https?://batch\\.(.+)\\.amazonaws.com")),
    ("bedrock", re.compile("https?://bedrock\\.(.+)\\.amazonaws\\.com")),
    ("bedrockagent", re.compile("https?://bedrock-agent\\.(.+)\\.amazonaws\\.com")),
    ("budgets", re.compile("https?://budgets\\.amazonaws\\.com")),
    ("ce", re.compile("https?://ce\\.(.+)\\.amazonaws\\.com")),
    ("cloudformation", re.compile("https?://cloudformation\\.(.+)\\.amazonaws\\.com")),
    ("cloudfront", re.compile("https?://cloudfront\\.amazonaws\\.com")),
    ("cloudfront", re.compile("https?://cloudfront\\.(.+)\\.amazonaws\\.com")),
    ("cloudtrail", re.compile("https?://cloudtrail\\.(.+)\\.amazonaws\\.com")),
    ("cloudwatch", re.compile("https?://monitoring\\.(.+)\\.amazonaws.com")),
    ("codebuild", re.compile("https?://codebuild\\.(.+)\\.amazonaws\\.com")),
    ("codecommit", re.compile("https?://codecommit\\.(.+)\\.amazonaws\\.com")),
    ("codepipeline", re.compile("https?://codepipeline\\.(.+)\\.amazonaws\\.com")),
    ("cognitoidentity", re.compile("https?://cognito-identity\\.(.+)\\.amazonaws.com")),
    ("cognitoidp", re.compile("https?://cognito-idp\\.(.+)\\.amazonaws.com")),
    ("comprehend", re.compile("https?://comprehend\\.(.+)\\.amazonaws\\.com")),
    ("config", re.compile("https?://config\\.(.+)\\.amazonaws\\.com")),
    ("databrew", re.compile("https?://databrew\\.(.+)\\.amazonaws.com")),
    ("datapipeline", re.compile("https?://datapipeline\\.(.+)\\.amazonaws\\.com")),
    ("datasync", re.compile("https?://(.*\\.)?(datasync)\\.(.+)\\.amazonaws.com")),
    ("dax", re.compile("https?://dax\\.(.+)\\.amazonaws\\.com")),
    ("dms", re.compile("https?://dms\\.(.+)\\.amazonaws\\.com")),
    ("ds", re.compile("https?://ds\\.(.+)\\.amazonaws\\.com")),
    ("dynamodb", re.compile("https?://dynamodb\\.(.+)\\.amazonaws\\.com")),
    (
        "dynamodbstreams",
        re.compile("https?://streams\\.dynamodb\\.(.+)\\.amazonaws.com"),
    ),
    ("ebs", re.compile("https?://ebs\\.(.+)\\.amazonaws\\.com")),
    ("ec2", re.compile("https?://ec2\\.(.+)\\.amazonaws\\.com(|\\.cn)")),
    (
        "ec2instanceconnect",
        re.compile("https?://ec2-instance-connect\\.(.+)\\.amazonaws\\.com"),
    ),
    ("ecr", re.compile("https?://ecr\\.(.+)\\.amazonaws\\.com")),
    ("ecr", re.compile("https?://api\\.ecr\\.(.+)\\.amazonaws\\.com")),
    ("ecs", re.compile("https?://ecs\\.(.+)\\.amazonaws\\.com")),
    ("efs", re.compile("https?://elasticfilesystem\\.(.+)\\.amazonaws.com")),
    ("efs", re.compile("https?://elasticfilesystem\\.amazonaws.com")),
    ("eks", re.compile("https?://eks\\.(.+)\\.amazonaws.com")),
    ("elasticache", re.compile("https?://elasticache\\.(.+)\\.amazonaws\\.com")),
    (
        "elasticbeanstalk",
        re.compile(
            "https?://elasticbeanstalk\\.(?P<region>[a-zA-Z0-9\\-_]+)\\.amazonaws.com"
        ),
    ),
    (
        "elastictranscoder",
        re.compile("https?://elastictranscoder\\.(.+)\\.amazonaws.com"),
    ),
    ("elb", re.compile("https?://elasticloadbalancing\\.(.+)\\.amazonaws.com")),
    ("elbv2", re.compile("https?://elasticloadbalancing\\.(.+)\\.amazonaws.com")),
    ("emr", re.compile("https?://(.+)\\.elasticmapreduce\\.amazonaws.com")),
    ("emr", re.compile("https?://elasticmapreduce\\.(.+)\\.amazonaws.com")),
    ("emrcontainers", re.compile("https?://emr-containers\\.(.+)\\.amazonaws\\.com")),
    ("emrserverless", re.compile("https?://emr-serverless\\.(.+)\\.amazonaws\\.com")),
    ("es", re.compile("https?://es\\.(.+)\\.amazonaws\\.com")),
    ("events", re.compile("https?://events\\.(.+)\\.amazonaws\\.com")),
    ("firehose", re.compile("https?://firehose\\.(.+)\\.amazonaws\\.com")),
    ("forecast", re.compile("https?://forecast\\.(.+)\\.amazonaws\\.com")),
    ("glacier", re.compile("https?://glacier\\.(.+)\\.amazonaws.com")),
    ("glue", re.compile("https?://glue\\.(.+)\\.amazonaws\\.com")),
    ("greengrass", re.compile("https?://greengrass\\.(.+)\\.amazonaws.com")),
    ("guardduty", re.compile("https?://guardduty\\.(.+)\\.amazonaws\\.com")),
    ("iam", re.compile("https?://iam\\.(.*\\.)?amazonaws\\.com")),
    ("identitystore", re.compile("https?://identitystore\\.(.+)\\.amazonaws\\.com")),
    ("inspector2", re.compile("https?://inspector2\\.(.+)\\.amazonaws\\.com")),
    ("instance_metadata", re.compile("http://169.254.169.254")),
    ("iot", re.compile("https?://iot\\.(.+)\\.amazonaws\\.com")),
    ("iotdata", re.compile("https?://data\\.iot\\.(.+)\\.amazonaws.com")),
    ("iotdata", re.compile("https?://data-ats\\.iot\\.(.+)\\.amazonaws.com")),
    ("ivs", re.compile("https?://ivs\\.(.+)\\.amazonaws\\.com")),
    ("kinesis", re.compile("https?://kinesis\\.(.+)\\.amazonaws\\.com")),
    ("kinesis", re.compile("https?://(.+)\\.control-kinesis\\.(.+)\\.amazonaws\\.com")),
    ("kinesis", re.compile("https?://(.+)\\.data-kinesis\\.(.+)\\.amazonaws\\.com")),
    ("kinesisvideo", re.compile("https?://kinesisvideo\\.(.+)\\.amazonaws.com")),
    (
        "kinesisvideoarchivedmedia",
        re.compile("https?://.*\\.kinesisvideo\\.(.+)\\.amazonaws.com"),
    ),
    ("kms", re.compile("https?://kms\\.(.+)\\.amazonaws\\.com")),
    ("lakeformation", re.compile("https?://lakeformation\\.(.+)\\.amazonaws\\.com")),
    ("logs", re.compile("https?://logs\\.(.+)\\.amazonaws\\.com")),
    (
        "managedblockchain",
        re.compile("https?://managedblockchain\\.(.+)\\.amazonaws.com"),
    ),
    ("mediaconnect", re.compile("https?://mediaconnect\\.(.+)\\.amazonaws.com")),
    ("medialive", re.compile("https?://medialive\\.(.+)\\.amazonaws.com")),
    ("mediapackage", re.compile("https?://mediapackage\\.(.+)\\.amazonaws.com")),
    ("mediastore", re.compile("https?://mediastore\\.(.+)\\.amazonaws\\.com")),
    ("mediastoredata", re.compile("https?://data\\.mediastore\\.(.+)\\.amazonaws.com")),
    (
        "meteringmarketplace",
        re.compile("https?://metering.marketplace.(.+).amazonaws.com"),
    ),
    ("meteringmarketplace", re.compile("https?://aws-marketplace.(.+).amazonaws.com")),
    ("moto_api._internal", re.compile("https?://motoapi.amazonaws.com")),
    ("mq", re.compile("https?://mq\\.(.+)\\.amazonaws\\.com")),
    ("networkmanager", re.compile("https?://networkmanager\\.(.+)\\.amazonaws\\.com")),
    ("opsworks", re.compile("https?://opsworks\\.us-east-1\\.amazonaws.com")),
    ("organizations", re.compile("https?://organizations\\.(.+)\\.amazonaws\\.com")),
    ("panorama", re.compile("https?://panorama\\.(.+)\\.amazonaws.com")),
    ("personalize", re.compile("https?://personalize\\.(.+)\\.amazonaws\\.com")),
    ("pinpoint", re.compile("https?://pinpoint\\.(.+)\\.amazonaws\\.com")),
    ("polly", re.compile("https?://polly\\.(.+)\\.amazonaws.com")),
    ("quicksight", re.compile("https?://quicksight\\.(.+)\\.amazonaws\\.com")),
    ("ram", re.compile("https?://ram\\.(.+)\\.amazonaws.com")),
    ("rds", re.compile("https?://rds\\.(.+)\\.amazonaws\\.com")),
    ("rds", re.compile("https?://rds\\.amazonaws\\.com")),
    ("rdsdata", re.compile("https?://rds-data\\.(.+)\\.amazonaws\\.com")),
    ("redshift", re.compile("https?://redshift\\.(.+)\\.amazonaws\\.com")),
    ("redshiftdata", re.compile("https?://redshift-data\\.(.+)\\.amazonaws\\.com")),
    ("rekognition", re.compile("https?://rekognition\\.(.+)\\.amazonaws\\.com")),
    ("resiliencehub", re.compile("https?://resiliencehub\\.(.+)\\.amazonaws\\.com")),
    (
        "resourcegroups",
        re.compile("https?://resource-groups(-fips)?\\.(.+)\\.amazonaws.com"),
    ),
    ("resourcegroupstaggingapi", re.compile("https?://tagging\\.(.+)\\.amazonaws.com")),
    ("robomaker", re.compile("https?://robomaker\\.(.+)\\.amazonaws\\.com")),
    ("route53", re.compile("https?://route53(\\..+)?\\.amazonaws.com")),
    ("route53domains", re.compile("https?://route53domains\\.(.+)\\.amazonaws\\.com")),
    (
        "route53resolver",
        re.compile("https?://route53resolver\\.(.+)\\.amazonaws\\.com"),
    ),
    ("s3", re.compile("https?://s3(?!-control)(.*)\\.amazonaws.com")),
    (
        "s3",
        re.compile(
            "https?://(?P<bucket_name>[a-zA-Z0-9\\-_.]*)\\.?s3(?!-control)(.*)\\.amazonaws.com"
        ),
    ),
    (
        "s3control",
        re.compile("https?://([0-9]+)\\.s3-control\\.(.+)\\.amazonaws\\.com"),
    ),
    ("sagemaker", re.compile("https?://api\\.sagemaker\\.(.+)\\.amazonaws.com")),
    (
        "sagemakermetrics",
        re.compile("https?://metrics.sagemaker\\.(.+)\\.amazonaws\\.com"),
    ),
    (
        "sagemakerruntime",
        re.compile("https?://runtime\\.sagemaker\\.(.+)\\.amazonaws\\.com"),
    ),
    ("scheduler", re.compile("https?://scheduler\\.(.+)\\.amazonaws\\.com")),
    ("sdb", re.compile("https?://sdb\\.(.+)\\.amazonaws\\.com")),
    ("secretsmanager", re.compile("https?://secretsmanager\\.(.+)\\.amazonaws\\.com")),
    (
        "servicediscovery",
        re.compile("https?://servicediscovery\\.(.+)\\.amazonaws\\.com"),
    ),
    ("servicequotas", re.compile("https?://servicequotas\\.(.+)\\.amazonaws\\.com")),
    ("ses", re.compile("https?://email\\.(.+)\\.amazonaws\\.com")),
    ("ses", re.compile("https?://ses\\.(.+)\\.amazonaws\\.com")),
    ("sesv2", re.compile("https?://email\\.(.+)\\.amazonaws\\.com")),
    ("signer", re.compile("https?://signer\\.(.+)\\.amazonaws\\.com")),
    ("sns", re.compile("https?://sns\\.(.+)\\.amazonaws\\.com")),
    ("sqs", re.compile("https?://(.*\\.)?(queue|sqs)\\.(.*\\.)?amazonaws\\.com")),
    ("ssm", re.compile("https?://ssm\\.(.+)\\.amazonaws\\.com")),
    ("ssm", re.compile("https?://ssm\\.(.+)\\.amazonaws\\.com\\.cn")),
    ("ssoadmin", re.compile("https?://sso\\.(.+)\\.amazonaws\\.com")),
    ("stepfunctions", re.compile("https?://states\\.(.+)\\.amazonaws.com")),
    ("sts", re.compile("https?://sts\\.(.*\\.)?amazonaws\\.com")),
    ("support", re.compile("https?://support\\.(.+)\\.amazonaws\\.com")),
    ("swf", re.compile("https?://swf\\.(.+)\\.amazonaws\\.com")),
    ("textract", re.compile("https?://textract\\.(.+)\\.amazonaws\\.com")),
    (
        "timestreamwrite",
        re.compile("https?://ingest\\.timestream\\.(.+)\\.amazonaws\\.com"),
    ),
    (
        "timestreamwrite",
        re.compile("https?://ingest\\.timestream\\.(.+)\\.amazonaws\\.com/"),
    ),
    ("transcribe", re.compile("https?://transcribe\\.(.+)\\.amazonaws\\.com")),
    ("wafv2", re.compile("https?://wafv2\\.(.+)\\.amazonaws.com")),
    ("workspaces", re.compile("https?://workspaces\\.(.+)\\.amazonaws\\.com")),
    ("xray", re.compile("https?://xray\\.(.+)\\.amazonaws.com")),
]
