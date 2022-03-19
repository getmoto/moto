"""Implementation of the AWS Config Service APIs."""
import json
import re
import time
import random
import string

from datetime import datetime

from moto.config.exceptions import (
    InvalidResourceTypeException,
    InvalidDeliveryFrequency,
    InvalidConfigurationRecorderNameException,
    NameTooLongException,
    MaxNumberOfConfigurationRecordersExceededException,
    InvalidRecordingGroupException,
    NoSuchConfigurationRecorderException,
    NoAvailableConfigurationRecorderException,
    InvalidDeliveryChannelNameException,
    NoSuchBucketException,
    InvalidS3KeyPrefixException,
    InvalidSNSTopicARNException,
    MaxNumberOfDeliveryChannelsExceededException,
    NoAvailableDeliveryChannelException,
    NoSuchDeliveryChannelException,
    LastDeliveryChannelDeleteFailedException,
    TagKeyTooBig,
    TooManyTags,
    TagValueTooBig,
    TooManyAccountSources,
    InvalidParameterValueException,
    InvalidNextTokenException,
    NoSuchConfigurationAggregatorException,
    InvalidTagCharacters,
    DuplicateTags,
    InvalidLimitException,
    InvalidResourceParameters,
    TooManyResourceIds,
    ResourceNotDiscoveredException,
    ResourceNotFoundException,
    TooManyResourceKeys,
    InvalidResultTokenException,
    ValidationException,
    NoSuchOrganizationConformancePackException,
    MaxNumberOfConfigRulesExceededException,
    InsufficientPermissionsException,
    NoSuchConfigRuleException,
    ResourceInUseException,
    MissingRequiredConfigRuleParameterException,
)

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID
from moto.core.responses import AWSServiceSpec
from moto.core.utils import BackendDict
from moto.iam.config import role_config_query, policy_config_query
from moto.s3.config import s3_config_query
from moto.s3control.config import s3_account_public_access_block_query
from moto.utilities.utils import load_resource


POP_STRINGS = [
    "capitalizeStart",
    "CapitalizeStart",
    "capitalizeArn",
    "CapitalizeArn",
    "capitalizeARN",
    "CapitalizeARN",
]
DEFAULT_PAGE_SIZE = 100
CONFIG_RULE_PAGE_SIZE = 25

# Map the Config resource type to a backend:
RESOURCE_MAP = {
    "AWS::S3::Bucket": s3_config_query,
    "AWS::S3::AccountPublicAccessBlock": s3_account_public_access_block_query,
    "AWS::IAM::Role": role_config_query,
    "AWS::IAM::Policy": policy_config_query,
}

CAMEL_TO_SNAKE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")

MAX_TAGS_IN_ARG = 50

MANAGED_RULES = load_resource(__name__, "resources/aws_managed_rules.json")
MANAGED_RULES_CONSTRAINTS = MANAGED_RULES["ManagedRules"]


def datetime2int(date):
    return int(time.mktime(date.timetuple()))


def snake_to_camels(original, cap_start, cap_arn):
    parts = original.split("_")

    camel_cased = parts[0].lower() + "".join(p.title() for p in parts[1:])

    if cap_arn:
        camel_cased = camel_cased.replace(
            "Arn", "ARN"
        )  # Some config services use 'ARN' instead of 'Arn'

    if cap_start:
        camel_cased = camel_cased[0].upper() + camel_cased[1::]

    return camel_cased


def random_string():
    """Returns a random set of 8 lowercase letters for the Config Aggregator ARN"""
    chars = []
    for _ in range(0, 8):
        chars.append(random.choice(string.ascii_lowercase))

    return "".join(chars)


def validate_tag_key(tag_key, exception_param="tags.X.member.key"):
    """Validates the tag key.

    :param tag_key: The tag key to check against.
    :param exception_param: The exception parameter to send over to help
                            format the message. This is to reflect
                            the difference between the tag and untag APIs.
    :return:
    """
    # Validate that the key length is correct:
    if len(tag_key) > 128:
        raise TagKeyTooBig(tag_key, param=exception_param)

    # Validate that the tag key fits the proper Regex:
    # [\w\s_.:/=+\-@]+ SHOULD be the same as the Java regex on the AWS
    # documentation: [\p{L}\p{Z}\p{N}_.:/=+\-@]+
    match = re.findall(r"[\w\s_.:/=+\-@]+", tag_key)
    # Kudos if you can come up with a better way of doing a global search :)
    if not match or len(match[0]) < len(tag_key):
        raise InvalidTagCharacters(tag_key, param=exception_param)


def check_tag_duplicate(all_tags, tag_key):
    """Validates that a tag key is not a duplicate

    :param all_tags: Dict to check if there is a duplicate tag.
    :param tag_key: The tag key to check against.
    :return:
    """
    if all_tags.get(tag_key):
        raise DuplicateTags()


def validate_tags(tags):
    proper_tags = {}

    if len(tags) > MAX_TAGS_IN_ARG:
        raise TooManyTags(tags)

    for tag in tags:
        # Validate the Key:
        validate_tag_key(tag["Key"])
        check_tag_duplicate(proper_tags, tag["Key"])

        # Validate the Value:
        if len(tag["Value"]) > 256:
            raise TagValueTooBig(tag["Value"])

        proper_tags[tag["Key"]] = tag["Value"]

    return proper_tags


def convert_to_class_args(dict_arg):
    """Return dict that can be used to instantiate it's representative class.

    Given a dictionary in the incoming API request, convert the keys to
    snake case to use as arguments when instatiating the representative
    class's __init__().
    """
    class_args = {}
    for key, value in dict_arg.items():
        class_args[CAMEL_TO_SNAKE_REGEX.sub("_", key).lower()] = value

    # boto detects if extra/unknown arguments are provided, so it's not
    # necessary to do so here.
    return class_args


class ConfigEmptyDictable(BaseModel):
    """Base class to make serialization easy.

    This assumes that the sub-class will NOT return 'None's in the JSON.
    """

    def __init__(self, capitalize_start=False, capitalize_arn=True):
        """Assists with the serialization of the config object
        :param capitalize_start: For some Config services, the first letter
                                 is lowercase -- for others it's capital
        :param capitalize_arn: For some Config services, the API expects
                                 'ARN' and for others, it expects 'Arn'
        """
        self.capitalize_start = capitalize_start
        self.capitalize_arn = capitalize_arn

    def to_dict(self):
        data = {}
        for item, value in self.__dict__.items():
            # ignore private attributes
            if not item.startswith("_") and value is not None:
                if isinstance(value, ConfigEmptyDictable):
                    data[
                        snake_to_camels(
                            item, self.capitalize_start, self.capitalize_arn
                        )
                    ] = value.to_dict()
                else:
                    data[
                        snake_to_camels(
                            item, self.capitalize_start, self.capitalize_arn
                        )
                    ] = value

        # Cleanse the extra properties:
        for prop in POP_STRINGS:
            data.pop(prop, None)

        return data


class ConfigRecorderStatus(ConfigEmptyDictable):
    def __init__(self, name):
        super().__init__()

        self.name = name
        self.recording = False
        self.last_start_time = None
        self.last_stop_time = None
        self.last_status = None
        self.last_error_code = None
        self.last_error_message = None
        self.last_status_change_time = None

    def start(self):
        self.recording = True
        self.last_status = "PENDING"
        self.last_start_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())

    def stop(self):
        self.recording = False
        self.last_stop_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())


class ConfigDeliverySnapshotProperties(ConfigEmptyDictable):
    def __init__(self, delivery_frequency):
        super().__init__()

        self.delivery_frequency = delivery_frequency


class ConfigDeliveryChannel(ConfigEmptyDictable):
    def __init__(
        self, name, s3_bucket_name, prefix=None, sns_arn=None, snapshot_properties=None
    ):
        super().__init__()

        self.name = name
        self.s3_bucket_name = s3_bucket_name
        self.s3_key_prefix = prefix
        self.sns_topic_arn = sns_arn
        self.config_snapshot_delivery_properties = snapshot_properties


class RecordingGroup(ConfigEmptyDictable):
    def __init__(
        self,
        all_supported=True,
        include_global_resource_types=False,
        resource_types=None,
    ):
        super().__init__()

        self.all_supported = all_supported
        self.include_global_resource_types = include_global_resource_types
        self.resource_types = resource_types


class ConfigRecorder(ConfigEmptyDictable):
    def __init__(self, role_arn, recording_group, name="default", status=None):
        super().__init__()

        self.name = name
        self.role_arn = role_arn
        self.recording_group = recording_group

        if not status:
            self.status = ConfigRecorderStatus(name)
        else:
            self.status = status


class AccountAggregatorSource(ConfigEmptyDictable):
    def __init__(self, account_ids, aws_regions=None, all_aws_regions=None):
        super().__init__(capitalize_start=True)

        # Can't have both the regions and all_regions flag present -- also
        # can't have them both missing:
        if aws_regions and all_aws_regions:
            raise InvalidParameterValueException(
                "Your configuration aggregator contains a list of regions "
                "and also specifies the use of all regions. You must choose "
                "one of these options."
            )

        if not (aws_regions or all_aws_regions):
            raise InvalidParameterValueException(
                "Your request does not specify any regions. Select AWS Config-supported "
                "regions and try again."
            )

        self.account_ids = account_ids
        self.aws_regions = aws_regions

        if not all_aws_regions:
            all_aws_regions = False

        self.all_aws_regions = all_aws_regions


class OrganizationAggregationSource(ConfigEmptyDictable):
    def __init__(self, role_arn, aws_regions=None, all_aws_regions=None):
        super().__init__(capitalize_start=True, capitalize_arn=False)

        # Can't have both the regions and all_regions flag present -- also
        # can't have them both missing:
        if aws_regions and all_aws_regions:
            raise InvalidParameterValueException(
                "Your configuration aggregator contains a list of regions and also specifies "
                "the use of all regions. You must choose one of these options."
            )

        if not (aws_regions or all_aws_regions):
            raise InvalidParameterValueException(
                "Your request does not specify any regions. Select AWS Config-supported "
                "regions and try again."
            )

        self.role_arn = role_arn
        self.aws_regions = aws_regions

        if not all_aws_regions:
            all_aws_regions = False

        self.all_aws_regions = all_aws_regions


class ConfigAggregator(ConfigEmptyDictable):
    def __init__(self, name, region, account_sources=None, org_source=None, tags=None):
        super().__init__(capitalize_start=True, capitalize_arn=False)

        self.configuration_aggregator_name = name
        self.configuration_aggregator_arn = "arn:aws:config:{region}:{id}:config-aggregator/config-aggregator-{random}".format(
            region=region, id=DEFAULT_ACCOUNT_ID, random=random_string()
        )
        self.account_aggregation_sources = account_sources
        self.organization_aggregation_source = org_source
        self.creation_time = datetime2int(datetime.utcnow())
        self.last_updated_time = datetime2int(datetime.utcnow())

        # Tags are listed in the list_tags_for_resource API call.
        self.tags = tags or {}

    # Override the to_dict so that we can format the tags properly...
    def to_dict(self):
        result = super().to_dict()

        # Override the account aggregation sources if present:
        if self.account_aggregation_sources:
            result["AccountAggregationSources"] = [
                a.to_dict() for a in self.account_aggregation_sources
            ]

        if self.tags:
            result["Tags"] = [
                {"Key": key, "Value": value} for key, value in self.tags.items()
            ]

        return result


class ConfigAggregationAuthorization(ConfigEmptyDictable):
    def __init__(
        self, current_region, authorized_account_id, authorized_aws_region, tags=None
    ):
        super().__init__(capitalize_start=True, capitalize_arn=False)

        self.aggregation_authorization_arn = (
            "arn:aws:config:{region}:{id}:aggregation-authorization/"
            "{auth_account}/{auth_region}".format(
                region=current_region,
                id=DEFAULT_ACCOUNT_ID,
                auth_account=authorized_account_id,
                auth_region=authorized_aws_region,
            )
        )
        self.authorized_account_id = authorized_account_id
        self.authorized_aws_region = authorized_aws_region
        self.creation_time = datetime2int(datetime.utcnow())

        # Tags are listed in the list_tags_for_resource API call.
        self.tags = tags or {}


class OrganizationConformancePack(ConfigEmptyDictable):
    def __init__(
        self,
        region,
        name,
        delivery_s3_bucket,
        delivery_s3_key_prefix=None,
        input_parameters=None,
        excluded_accounts=None,
    ):
        super().__init__(capitalize_start=True, capitalize_arn=False)

        self._status = "CREATE_SUCCESSFUL"
        self._unique_pack_name = "{0}-{1}".format(name, random_string())

        self.conformance_pack_input_parameters = input_parameters or []
        self.delivery_s3_bucket = delivery_s3_bucket
        self.delivery_s3_key_prefix = delivery_s3_key_prefix
        self.excluded_accounts = excluded_accounts or []
        self.last_update_time = datetime2int(datetime.utcnow())
        self.organization_conformance_pack_arn = (
            "arn:aws:config:{0}:{1}:organization-conformance-pack/{2}".format(
                region, DEFAULT_ACCOUNT_ID, self._unique_pack_name
            )
        )
        self.organization_conformance_pack_name = name

    def update(
        self,
        delivery_s3_bucket,
        delivery_s3_key_prefix,
        input_parameters,
        excluded_accounts,
    ):
        self._status = "UPDATE_SUCCESSFUL"

        self.conformance_pack_input_parameters = input_parameters
        self.delivery_s3_bucket = delivery_s3_bucket
        self.delivery_s3_key_prefix = delivery_s3_key_prefix
        self.excluded_accounts = excluded_accounts
        self.last_update_time = datetime2int(datetime.utcnow())


class Scope(ConfigEmptyDictable):

    """Defines resources that can trigger an evaluation for the rule.

    Per boto3 documentation, Scope can be one of:
    - one or more resource types,
    - combo of one resource type and one resource ID,
    - combo of tag key and value.

    If no scope is specified, evaluations are trigged when any resource
    in the recording group changes.
    """

    def __init__(
        self,
        compliance_resource_types=None,
        tag_key=None,
        tag_value=None,
        compliance_resource_id=None,
    ):
        super().__init__(capitalize_start=True, capitalize_arn=False)
        self.tags = None
        if tag_key or tag_value:
            if tag_value and not tag_key:
                raise InvalidParameterValueException(
                    "Tag key should not be empty when tag value is provided in scope"
                )
            if tag_key and len(tag_key) > 128:
                raise TagKeyTooBig(tag_key, "ConfigRule.Scope.TagKey")
            if tag_value and len(tag_value) > 256:
                raise TagValueTooBig(tag_value, "ConfigRule.Scope.TagValue")
            self.tags = {tag_key: tag_value}

        # Can't use more than one combo to specify scope - either tags,
        # resource types, or resource id and resource type.
        if self.tags and (compliance_resource_types or compliance_resource_id):
            raise InvalidParameterValueException(
                "Scope cannot be applied to both resource and tag"
            )

        if compliance_resource_id and len(compliance_resource_types) != 1:
            raise InvalidParameterValueException(
                "A single resourceType should be provided when resourceId "
                "is provided in scope"
            )
        self.compliance_resource_types = compliance_resource_types
        self.compliance_resource_id = compliance_resource_id


class SourceDetail(ConfigEmptyDictable):

    """Source and type of event triggering AWS Config resource evaluation.

    Applies only to customer rules.
    """

    MESSAGE_TYPES = {
        "ConfigurationItemChangeNotification",
        "ConfigurationSnapshotDeliveryCompleted",
        "OversizedConfigurationItemChangeNotification",
        "ScheduledNotification",
    }
    DEFAULT_FREQUENCY = "TwentyFour_Hours"
    FREQUENCY_TYPES = {
        "One_Hour",
        "Six_Hours",
        "Three_Hours",
        "Twelve_Hours",
        "TwentyFour_Hours",
    }
    EVENT_SOURCES = ["aws.config"]

    def __init__(
        self, event_source=None, message_type=None, maximum_execution_frequency=None
    ):
        super().__init__(capitalize_start=True, capitalize_arn=False)

        # If the event_source or message_type fields are not provided,
        # boto3 reports:  "SourceDetails should be null/empty if the owner is
        # AWS. SourceDetails should be provided if the owner is CUSTOM_LAMBDA."
        # A more specific message will be used here instead.
        if not event_source:
            raise MissingRequiredConfigRuleParameterException(
                "Missing required parameter in ConfigRule.SourceDetails: "
                "'EventSource'"
            )
        if event_source not in SourceDetail.EVENT_SOURCES:
            raise ValidationException(
                f"Value '{event_source}' at "
                f"'configRule.source.sourceDetails.eventSource' failed "
                f"to satisfy constraint: Member must satisfy enum value set: {{"
                + ", ".join((SourceDetail.EVENT_SOURCES))
                + "}"
            )

        if not message_type:
            # boto3 doesn't have a specific error if this field is missing.
            raise MissingRequiredConfigRuleParameterException(
                "Missing required parameter in ConfigRule.SourceDetails: 'MessageType'"
            )
        if message_type not in SourceDetail.MESSAGE_TYPES:
            raise ValidationException(
                f"Value '{message_type}' at "
                f"'configRule.source.sourceDetails.message_type' failed "
                f"to satisfy constraint: Member must satisfy enum value set: {{"
                + ", ".join(sorted(SourceDetail.MESSAGE_TYPES))
                + "}"
            )

        if maximum_execution_frequency:
            if maximum_execution_frequency not in SourceDetail.FREQUENCY_TYPES:
                raise ValidationException(
                    f"Value '{maximum_execution_frequency}' at "
                    f"'configRule.source.sourceDetails.maximumExecutionFrequency' "
                    f"failed to satisfy constraint: "
                    f"Member must satisfy enum value set: {{"
                    + ", ".join(sorted(SourceDetail.FREQUENCY_TYPES))
                    + "}"
                )
            if message_type in [
                "ConfigurationItemChangeNotification",
                "OversizedConfigurationItemChangeNotification",
            ]:
                raise InvalidParameterValueException(
                    "A maximum execution frequency is not allowed if "
                    "MessageType is ConfigurationItemChangeNotification or "
                    "OversizedConfigurationItemChangeNotification"
                )
        else:
            # If no value is specified, use a default value for
            # maximum_execution_frequency for message types representing a
            # periodic trigger.
            if message_type in [
                "ScheduledNotification",
                "ConfigurationSnapshotDeliveryCompleted",
            ]:
                maximum_execution_frequency = SourceDetail.DEFAULT_FREQUENCY

        self.event_source = event_source
        self.message_type = message_type
        self.maximum_execution_frequency = maximum_execution_frequency


class Source(ConfigEmptyDictable):

    """Defines rule owner, id and notification for triggering evaluation."""

    OWNERS = {"AWS", "CUSTOM_LAMBDA"}

    def __init__(self, region, owner, source_identifier, source_details=None):
        super().__init__(capitalize_start=True, capitalize_arn=False)
        if owner not in Source.OWNERS:
            raise ValidationException(
                f"Value '{owner}' at 'configRule.source.owner' failed to "
                f"satisfy constraint: Member must satisfy enum value set: {{"
                + ", ".join(sorted(Source.OWNERS))
                + "}"
            )

        if owner == "AWS":
            # Can the Source ID be found in the dict of managed rule IDs?
            if source_identifier not in MANAGED_RULES_CONSTRAINTS:
                raise InvalidParameterValueException(
                    f"The sourceIdentifier {source_identifier} is invalid.  "
                    f"Please refer to the documentation for a list of valid "
                    f"sourceIdentifiers that can be used when AWS is the Owner"
                )
            if source_details:
                raise InvalidParameterValueException(
                    "SourceDetails should be null/empty if the owner is AWS. "
                    "SourceDetails should be provided if the owner is "
                    "CUSTOM_LAMBDA"
                )

            self.owner = owner
            self.source_identifier = source_identifier
            self.source_details = None
            return

        # Otherwise, owner == "CUSTOM_LAMBDA"
        if not source_details:
            raise InvalidParameterValueException(
                "SourceDetails should be null/empty if the owner is AWS. "
                "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
            )

        # Import is slow and as it's not needed for all config service
        # operations, only load it if needed.
        from moto.awslambda import lambda_backends

        try:
            lambda_backends[region].get_function(source_identifier)
        except Exception:
            raise InsufficientPermissionsException(
                f"The AWS Lambda function {source_identifier} cannot be "
                f"invoked. Check the specified function ARN, and check the "
                f"function's permissions"
            )

        details = []
        for detail in source_details:
            detail_dict = convert_to_class_args(detail)
            details.append(SourceDetail(**detail_dict))

        self.source_details = details
        self.owner = owner
        self.source_identifier = source_identifier

    def to_dict(self):
        """Format the SourceDetails properly."""
        result = super().to_dict()
        if self.source_details:
            result["SourceDetails"] = [x.to_dict() for x in self.source_details]
        return result


class ConfigRule(ConfigEmptyDictable):

    """AWS Config Rule to evaluate compliance of resources to configuration.

    Can be a managed or custom config rule.  Contains the instantiations of
    the Source and SourceDetail classes, and optionally the Scope class.
    """

    MAX_RULES = 150
    RULE_STATES = {"ACTIVE", "DELETING", "DELETING_RESULTS", "EVALUATING"}

    def __init__(self, region, config_rule, tags):
        super().__init__(capitalize_start=True, capitalize_arn=False)
        self.config_rule_name = config_rule.get("ConfigRuleName")
        if config_rule.get("ConfigRuleArn") or config_rule.get("ConfigRuleId"):
            raise InvalidParameterValueException(
                "ConfigRule Arn and Id can not be specified when creating a "
                "new ConfigRule. ConfigRule Arn and Id are generated by the "
                "service. Please try the request again without specifying "
                "ConfigRule Arn or Id"
            )

        self.maximum_execution_frequency = None  # keeps pylint happy
        self.modify_fields(region, config_rule, tags)
        self.config_rule_id = f"config-rule-{random_string():.6}"
        self.config_rule_arn = f"arn:aws:config:{region}:{DEFAULT_ACCOUNT_ID}:config-rule/{self.config_rule_id}"

    def modify_fields(self, region, config_rule, tags):
        """Initialize or update ConfigRule fields."""
        self.config_rule_state = config_rule.get("ConfigRuleState", "ACTIVE")
        if self.config_rule_state not in ConfigRule.RULE_STATES:
            raise ValidationException(
                f"Value '{self.config_rule_state}' at "
                f"'configRule.configRuleState' failed to satisfy constraint: "
                f"Member must satisfy enum value set: {{"
                + ", ".join(sorted(ConfigRule.RULE_STATES))
                + "}"
            )
        if self.config_rule_state != "ACTIVE":
            raise InvalidParameterValueException(
                f"The ConfigRuleState {self.config_rule_state} is invalid.  "
                f"Only the following values are permitted: ACTIVE"
            )

        self.description = config_rule.get("Description")

        self.scope = None
        if "Scope" in config_rule:
            scope_dict = convert_to_class_args(config_rule["Scope"])
            self.scope = Scope(**scope_dict)

        source_dict = convert_to_class_args(config_rule["Source"])
        self.source = Source(region, **source_dict)

        self.input_parameters = config_rule.get("InputParameters")
        self.input_parameters_dict = {}
        if self.input_parameters:
            try:
                # A dictionary will be more useful when these parameters
                # are actually needed.
                self.input_parameters_dict = json.loads(self.input_parameters)
            except ValueError:
                raise InvalidParameterValueException(  # pylint: disable=raise-missing-from
                    f"Invalid json {self.input_parameters} passed in the "
                    f"InputParameters field"
                )

        self.maximum_execution_frequency = config_rule.get("MaximumExecutionFrequency")
        if self.maximum_execution_frequency:
            if self.maximum_execution_frequency not in SourceDetail.FREQUENCY_TYPES:
                raise ValidationException(
                    f"Value '{self.maximum_execution_frequency}' at "
                    f"'configRule.maximumExecutionFrequency' failed to "
                    f"satisfy constraint: Member must satisfy enum value set: {{"
                    + ", ".join(sorted(SourceDetail.FREQUENCY_TYPES))
                    + "}"
                )

        # For an AWS managed rule, validate the parameters and trigger type.
        # Verify the MaximumExecutionFrequency makes sense as well.
        if self.source.owner == "AWS":
            self.validate_managed_rule()
        else:
            # Per the AWS documentation for a custom rule, ConfigRule's
            # MaximumExecutionFrequency can only be set if the message type
            # is ConfigSnapshotDeliveryProperties. However, if
            # ConfigSnapshotDeliveryProperties is used, the AWS console
            # leaves the Trigger Type blank and doesn't show the frequency.
            # If you edit the rule, it doesn't show the frequency either.
            #
            # If you provide two custom rules, one with a message type of
            # ConfigurationSnapshotDeliveryCompleted, one with
            # ScheduleNotification and specify a MaximumExecutionFrequency
            # for each, the first one is shown on the AWS console and the
            # second frequency is shown on the edit page.
            #
            # If you provide a custom rule for
            # OversizedConfigurationItemChangeNotification (not a periodic
            # trigger) with a MaximumExecutionFrequency for ConfigRule itself,
            # boto3 doesn't complain and describe_config_rule() shows the
            # frequency, but the AWS console and the edit page do not.
            #
            # So I'm not sure how to validate this situation or when to
            # set this value to a default value.
            pass

        self.created_by = config_rule.get("CreatedBy")
        if self.created_by:
            raise InvalidParameterValueException(
                "AWS Config populates the CreatedBy field for "
                "ServiceLinkedConfigRule. Try again without populating the "
                "CreatedBy field"
            )

        self.last_updated_time = datetime2int(datetime.utcnow())
        self.tags = tags

    def validate_managed_rule(self):
        """Validate parameters specific to managed rules."""
        rule_info = MANAGED_RULES_CONSTRAINTS[self.source.source_identifier]
        param_names = self.input_parameters_dict.keys()

        # Verify input parameter names are actual parameters for the rule ID.
        if param_names:
            allowed_names = {x["Name"] for x in rule_info["Parameters"]}
            if not set(param_names).issubset(allowed_names):
                raise InvalidParameterValueException(
                    "Unknown parameters provided in the inputParameters: "
                    + self.input_parameters
                )

        # Verify all the required parameters are specified.
        required_names = {
            x["Name"] for x in rule_info["Parameters"] if not x["Optional"]
        }
        diffs = required_names.difference(set(param_names))
        if diffs:
            raise InvalidParameterValueException(
                "The required parameter ["
                + ", ".join(sorted(diffs))
                + "] is not present in the inputParameters"
            )

        # boto3 doesn't appear to be checking for valid types in the
        # InputParameters.  It did give an error if a unquoted number was
        # used:  "Blank spaces are not acceptable for input parameter:
        # MinimumPasswordLength.  InputParameters':
        # '{"RequireNumbers":"true","MinimumPasswordLength":10}'
        # but I'm not going to attempt to detect that error.  I could
        # check for ints, floats, strings and stringmaps, but boto3 doesn't
        # check.

        # WARNING: The AWS documentation indicates MaximumExecutionFrequency
        # can be specified for managed rules triggered at a periodic frequency.
        # However, boto3 allows a MaximumExecutionFrequency to be specified
        # for a AWS managed rule regardless of the frequency type.  Also of
        # interest:  triggers of "Configuration Changes and Periodic",
        # i.e., both trigger types.  But again, the trigger type is ignored.
        # if rule_info["Trigger type"] == "Configuration changes":
        #     if self.maximum_execution_frequency:
        #         raise InvalidParameterValueException(
        #             "A maximum execution frequency is not allowed for "
        #             "rules triggered by configuration changes"
        #         )
        #
        # WARNING:  boto3's describe_config_rule is not showing the
        # MaximumExecutionFrequency value as being updated, but the AWS
        # console shows the default value on the console. The default value
        # is used even if the rule is non-periodic
        # if "Periodic" in rule_info["Trigger type"]:
        #     if not self.maximum_execution_frequency:
        #         self.maximum_execution_frequency = SourceDetail.DEFAULT_FREQUENCY
        # if not self.maximum_execution_frequency:
        #     self.maximum_execution_frequency = SourceDetail.DEFAULT_FREQUENCY

        # Verify the rule is allowed for this region -- not yet implemented.


class ConfigBackend(BaseBackend):
    def __init__(self, region=None):
        self.recorders = {}
        self.delivery_channels = {}
        self.config_aggregators = {}
        self.aggregation_authorizations = {}
        self.organization_conformance_packs = {}
        self.config_rules = {}
        self.config_schema = None
        self.region = region

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """List of dicts representing default VPC endpoints for this service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "config"
        )

    def _validate_resource_types(self, resource_list):
        if not self.config_schema:
            self.config_schema = AWSServiceSpec(
                path="data/config/2014-11-12/service-2.json"
            )

        # Verify that each entry exists in the supported list:
        bad_list = []
        for resource in resource_list:
            if resource not in self.config_schema.shapes["ResourceType"]["enum"]:
                bad_list.append(resource)

        if bad_list:
            raise InvalidResourceTypeException(
                bad_list, self.config_schema.shapes["ResourceType"]["enum"]
            )

    def _validate_delivery_snapshot_properties(self, properties):
        if not self.config_schema:
            self.config_schema = AWSServiceSpec(
                path="data/config/2014-11-12/service-2.json"
            )

        # Verify that the deliveryFrequency is set to an acceptable value:
        if (
            properties.get("deliveryFrequency", None)
            not in self.config_schema.shapes["MaximumExecutionFrequency"]["enum"]
        ):
            raise InvalidDeliveryFrequency(
                properties.get("deliveryFrequency", None),
                self.config_schema.shapes["MaximumExecutionFrequency"]["enum"],
            )

    def put_configuration_aggregator(self, config_aggregator):
        # Validate the name:
        if len(config_aggregator["ConfigurationAggregatorName"]) > 256:
            raise NameTooLongException(
                config_aggregator["ConfigurationAggregatorName"],
                "configurationAggregatorName",
            )

        account_sources = None
        org_source = None

        # Tag validation:
        tags = validate_tags(config_aggregator.get("Tags", []))

        # Exception if both AccountAggregationSources and
        # OrganizationAggregationSource are supplied:
        if config_aggregator.get("AccountAggregationSources") and config_aggregator.get(
            "OrganizationAggregationSource"
        ):
            raise InvalidParameterValueException(
                "The configuration aggregator cannot be created because your "
                "request contains both the AccountAggregationSource and the "
                "OrganizationAggregationSource. Include only one aggregation "
                "source and try again."
            )

        # If neither are supplied:
        if not config_aggregator.get(
            "AccountAggregationSources"
        ) and not config_aggregator.get("OrganizationAggregationSource"):
            raise InvalidParameterValueException(
                "The configuration aggregator cannot be created because your "
                "request is missing either the AccountAggregationSource or "
                "the OrganizationAggregationSource. Include the "
                "appropriate aggregation source and try again."
            )

        if config_aggregator.get("AccountAggregationSources"):
            # Currently, only 1 account aggregation source can be set:
            if len(config_aggregator["AccountAggregationSources"]) > 1:
                raise TooManyAccountSources(
                    len(config_aggregator["AccountAggregationSources"])
                )

            account_sources = []
            for source in config_aggregator["AccountAggregationSources"]:
                account_sources.append(
                    AccountAggregatorSource(
                        source["AccountIds"],
                        aws_regions=source.get("AwsRegions"),
                        all_aws_regions=source.get("AllAwsRegions"),
                    )
                )

        else:
            org_source = OrganizationAggregationSource(
                config_aggregator["OrganizationAggregationSource"]["RoleArn"],
                aws_regions=config_aggregator["OrganizationAggregationSource"].get(
                    "AwsRegions"
                ),
                all_aws_regions=config_aggregator["OrganizationAggregationSource"].get(
                    "AllAwsRegions"
                ),
            )

        # Grab the existing one if it exists and update it:
        if not self.config_aggregators.get(
            config_aggregator["ConfigurationAggregatorName"]
        ):
            aggregator = ConfigAggregator(
                config_aggregator["ConfigurationAggregatorName"],
                self.region,
                account_sources=account_sources,
                org_source=org_source,
                tags=tags,
            )
            self.config_aggregators[
                config_aggregator["ConfigurationAggregatorName"]
            ] = aggregator

        else:
            aggregator = self.config_aggregators[
                config_aggregator["ConfigurationAggregatorName"]
            ]
            aggregator.tags = tags
            aggregator.account_aggregation_sources = account_sources
            aggregator.organization_aggregation_source = org_source
            aggregator.last_updated_time = datetime2int(datetime.utcnow())

        return aggregator.to_dict()

    def describe_configuration_aggregators(self, names, token, limit):
        limit = DEFAULT_PAGE_SIZE if not limit or limit < 0 else limit
        agg_list = []
        result = {"ConfigurationAggregators": []}

        if names:
            for name in names:
                if not self.config_aggregators.get(name):
                    raise NoSuchConfigurationAggregatorException(number=len(names))

                agg_list.append(name)

        else:
            agg_list = list(self.config_aggregators.keys())

        # Empty?
        if not agg_list:
            return result

        # Sort by name:
        sorted_aggregators = sorted(agg_list)

        # Get the start:
        if not token:
            start = 0
        else:
            # Tokens for this moto feature are just the next names of the items in the list:
            if not self.config_aggregators.get(token):
                raise InvalidNextTokenException()

            start = sorted_aggregators.index(token)

        # Get the list of items to collect:
        agg_list = sorted_aggregators[start : (start + limit)]
        result["ConfigurationAggregators"] = [
            self.config_aggregators[agg].to_dict() for agg in agg_list
        ]

        if len(sorted_aggregators) > (start + limit):
            result["NextToken"] = sorted_aggregators[start + limit]

        return result

    def delete_configuration_aggregator(self, config_aggregator):
        if not self.config_aggregators.get(config_aggregator):
            raise NoSuchConfigurationAggregatorException()

        del self.config_aggregators[config_aggregator]

    def put_aggregation_authorization(
        self, authorized_account, authorized_region, tags
    ):
        # Tag validation:
        tags = validate_tags(tags or [])

        # Does this already exist?
        key = "{}/{}".format(authorized_account, authorized_region)
        agg_auth = self.aggregation_authorizations.get(key)
        if not agg_auth:
            agg_auth = ConfigAggregationAuthorization(
                self.region, authorized_account, authorized_region, tags=tags
            )
            self.aggregation_authorizations[
                "{}/{}".format(authorized_account, authorized_region)
            ] = agg_auth
        else:
            # Only update the tags:
            agg_auth.tags = tags

        return agg_auth.to_dict()

    def describe_aggregation_authorizations(self, token, limit):
        limit = DEFAULT_PAGE_SIZE if not limit or limit < 0 else limit
        result = {"AggregationAuthorizations": []}

        if not self.aggregation_authorizations:
            return result

        # Sort by name:
        sorted_authorizations = sorted(self.aggregation_authorizations.keys())

        # Get the start:
        if not token:
            start = 0
        else:
            # Tokens for this moto feature are just the next names of the items in the list:
            if not self.aggregation_authorizations.get(token):
                raise InvalidNextTokenException()

            start = sorted_authorizations.index(token)

        # Get the list of items to collect:
        auth_list = sorted_authorizations[start : (start + limit)]
        result["AggregationAuthorizations"] = [
            self.aggregation_authorizations[auth].to_dict() for auth in auth_list
        ]

        if len(sorted_authorizations) > (start + limit):
            result["NextToken"] = sorted_authorizations[start + limit]

        return result

    def delete_aggregation_authorization(self, authorized_account, authorized_region):
        # This will always return a 200 -- regardless if there is or isn't an existing
        # aggregation authorization.
        key = "{}/{}".format(authorized_account, authorized_region)
        self.aggregation_authorizations.pop(key, None)

    def put_configuration_recorder(self, config_recorder):
        # Validate the name:
        if not config_recorder.get("name"):
            raise InvalidConfigurationRecorderNameException(config_recorder.get("name"))
        if len(config_recorder.get("name")) > 256:
            raise NameTooLongException(
                config_recorder.get("name"), "configurationRecorder.name"
            )

        # We're going to assume that the passed in Role ARN is correct.

        # Config currently only allows 1 configuration recorder for an account:
        if len(self.recorders) == 1 and not self.recorders.get(config_recorder["name"]):
            raise MaxNumberOfConfigurationRecordersExceededException(
                config_recorder["name"]
            )

        # Is this updating an existing one?
        recorder_status = None
        if self.recorders.get(config_recorder["name"]):
            recorder_status = self.recorders[config_recorder["name"]].status

        # Validate the Recording Group:
        if config_recorder.get("recordingGroup") is None:
            recording_group = RecordingGroup()
        else:
            rgroup = config_recorder["recordingGroup"]

            # If an empty dict is passed in, then bad:
            if not rgroup:
                raise InvalidRecordingGroupException()

            # Can't have both the resource types specified and the other flags as True.
            if rgroup.get("resourceTypes") and (
                rgroup.get("allSupported", False)
                or rgroup.get("includeGlobalResourceTypes", False)
            ):
                raise InvalidRecordingGroupException()

            # Must supply resourceTypes if 'allSupported' is not supplied:
            if not rgroup.get("allSupported") and not rgroup.get("resourceTypes"):
                raise InvalidRecordingGroupException()

            # Validate that the list provided is correct:
            self._validate_resource_types(rgroup.get("resourceTypes", []))

            recording_group = RecordingGroup(
                all_supported=rgroup.get("allSupported", True),
                include_global_resource_types=rgroup.get(
                    "includeGlobalResourceTypes", False
                ),
                resource_types=rgroup.get("resourceTypes", []),
            )

        self.recorders[config_recorder["name"]] = ConfigRecorder(
            config_recorder["roleARN"],
            recording_group,
            name=config_recorder["name"],
            status=recorder_status,
        )

    def describe_configuration_recorders(self, recorder_names):
        recorders = []

        if recorder_names:
            for rname in recorder_names:
                if not self.recorders.get(rname):
                    raise NoSuchConfigurationRecorderException(rname)

                # Format the recorder:
                recorders.append(self.recorders[rname].to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.to_dict())

        return recorders

    def describe_configuration_recorder_status(self, recorder_names):
        recorders = []

        if recorder_names:
            for rname in recorder_names:
                if not self.recorders.get(rname):
                    raise NoSuchConfigurationRecorderException(rname)

                # Format the recorder:
                recorders.append(self.recorders[rname].status.to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.status.to_dict())

        return recorders

    def put_delivery_channel(self, delivery_channel):
        # Must have a configuration recorder:
        if not self.recorders:
            raise NoAvailableConfigurationRecorderException()

        # Validate the name:
        if not delivery_channel.get("name"):
            raise InvalidDeliveryChannelNameException(delivery_channel.get("name"))
        if len(delivery_channel.get("name")) > 256:
            raise NameTooLongException(
                delivery_channel.get("name"), "deliveryChannel.name"
            )

        # We are going to assume that the bucket exists -- but will verify if
        # the bucket provided is blank:
        if not delivery_channel.get("s3BucketName"):
            raise NoSuchBucketException()

        # We are going to assume that the bucket has the correct policy
        # attached to it. We are only going to verify
        # if the prefix provided is not an empty string:
        if delivery_channel.get("s3KeyPrefix", None) == "":
            raise InvalidS3KeyPrefixException()

        # Ditto for SNS -- Only going to assume that the ARN provided is not
        # an empty string:
        if delivery_channel.get("snsTopicARN", None) == "":
            raise InvalidSNSTopicARNException()

        # Config currently only allows 1 delivery channel for an account:
        if len(self.delivery_channels) == 1 and not self.delivery_channels.get(
            delivery_channel["name"]
        ):
            raise MaxNumberOfDeliveryChannelsExceededException(delivery_channel["name"])

        if not delivery_channel.get("configSnapshotDeliveryProperties"):
            dprop = None

        else:
            # Validate the config snapshot delivery properties:
            self._validate_delivery_snapshot_properties(
                delivery_channel["configSnapshotDeliveryProperties"]
            )

            dprop = ConfigDeliverySnapshotProperties(
                delivery_channel["configSnapshotDeliveryProperties"][
                    "deliveryFrequency"
                ]
            )

        self.delivery_channels[delivery_channel["name"]] = ConfigDeliveryChannel(
            delivery_channel["name"],
            delivery_channel["s3BucketName"],
            prefix=delivery_channel.get("s3KeyPrefix", None),
            sns_arn=delivery_channel.get("snsTopicARN", None),
            snapshot_properties=dprop,
        )

    def describe_delivery_channels(self, channel_names):
        channels = []

        if channel_names:
            for cname in channel_names:
                if not self.delivery_channels.get(cname):
                    raise NoSuchDeliveryChannelException(cname)

                # Format the delivery channel:
                channels.append(self.delivery_channels[cname].to_dict())

        else:
            for channel in self.delivery_channels.values():
                channels.append(channel.to_dict())

        return channels

    def start_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        # Must have a delivery channel available as well:
        if not self.delivery_channels:
            raise NoAvailableDeliveryChannelException()

        # Start recording:
        self.recorders[recorder_name].status.start()

    def stop_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        # Stop recording:
        self.recorders[recorder_name].status.stop()

    def delete_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        del self.recorders[recorder_name]

    def delete_delivery_channel(self, channel_name):
        if not self.delivery_channels.get(channel_name):
            raise NoSuchDeliveryChannelException(channel_name)

        # Check if a channel is recording -- if so, bad -- (there can only be 1 recorder):
        for recorder in self.recorders.values():
            if recorder.status.recording:
                raise LastDeliveryChannelDeleteFailedException(channel_name)

        del self.delivery_channels[channel_name]

    def list_discovered_resources(
        self,
        resource_type,
        backend_region,
        resource_ids,
        resource_name,
        limit,
        next_token,
    ):
        """Queries against AWS Config (non-aggregated) listing function.

        The listing function must exist for the resource backend.

        :param resource_type:
        :param backend_region:
        :param ids:
        :param name:
        :param limit:
        :param next_token:
        :return:
        """
        identifiers = []
        new_token = None

        limit = limit or DEFAULT_PAGE_SIZE
        if limit > DEFAULT_PAGE_SIZE:
            raise InvalidLimitException(limit)

        if resource_ids and resource_name:
            raise InvalidResourceParameters()

        # Only 20 maximum Resource IDs:
        if resource_ids and len(resource_ids) > 20:
            raise TooManyResourceIds()

        # If resource type exists and the backend region is implemented in
        # moto, then call upon the resource type's Config Query class to
        # retrieve the list of resources that match the criteria:
        if RESOURCE_MAP.get(resource_type, {}):
            # Is this a global resource type? -- if so, re-write the region to 'global':
            backend_query_region = (
                backend_region  # Always provide the backend this request arrived from.
            )
            if RESOURCE_MAP[resource_type].backends.get("global"):
                backend_region = "global"

            # For non-aggregated queries, the we only care about the
            # backend_region. Need to verify that moto has implemented
            # the region for the given backend:
            if RESOURCE_MAP[resource_type].backends.get(backend_region):
                # Fetch the resources for the backend's region:
                identifiers, new_token = RESOURCE_MAP[
                    resource_type
                ].list_config_service_resources(
                    resource_ids,
                    resource_name,
                    limit,
                    next_token,
                    backend_region=backend_query_region,
                )

        resource_identifiers = []
        for identifier in identifiers:
            item = {"resourceType": identifier["type"], "resourceId": identifier["id"]}

            # Some resource types lack names:
            if identifier.get("name"):
                item["resourceName"] = identifier["name"]

            resource_identifiers.append(item)

        result = {"resourceIdentifiers": resource_identifiers}

        if new_token:
            result["nextToken"] = new_token

        return result

    def list_aggregate_discovered_resources(
        self, aggregator_name, resource_type, filters, limit, next_token
    ):
        """Queries AWS Config listing function that must exist for resource backend.

        As far a moto goes -- the only real difference between this function
        and the `list_discovered_resources` function is that this will require
        a Config Aggregator be set up a priori and can search based on resource
        regions.

        :param aggregator_name:
        :param resource_type:
        :param filters:
        :param limit:
        :param next_token:
        :return:
        """
        if not self.config_aggregators.get(aggregator_name):
            raise NoSuchConfigurationAggregatorException()

        identifiers = []
        new_token = None
        filters = filters or {}

        limit = limit or DEFAULT_PAGE_SIZE
        if limit > DEFAULT_PAGE_SIZE:
            raise InvalidLimitException(limit)

        # If the resource type exists and the backend region is implemented
        # in moto, then call upon the resource type's Config Query class to
        # retrieve the list of resources that match the criteria:
        if RESOURCE_MAP.get(resource_type, {}):
            # We only care about a filter's Region, Resource Name, and Resource ID:
            resource_region = filters.get("Region")
            resource_id = [filters["ResourceId"]] if filters.get("ResourceId") else None
            resource_name = filters.get("ResourceName")

            identifiers, new_token = RESOURCE_MAP[
                resource_type
            ].list_config_service_resources(
                resource_id,
                resource_name,
                limit,
                next_token,
                resource_region=resource_region,
                aggregator=self.config_aggregators.get(aggregator_name).__dict__,
            )

        resource_identifiers = []
        for identifier in identifiers:
            item = {
                "SourceAccountId": DEFAULT_ACCOUNT_ID,
                "SourceRegion": identifier["region"],
                "ResourceType": identifier["type"],
                "ResourceId": identifier["id"],
            }
            if identifier.get("name"):
                item["ResourceName"] = identifier["name"]

            resource_identifiers.append(item)

        result = {"ResourceIdentifiers": resource_identifiers}

        if new_token:
            result["NextToken"] = new_token

        return result

    def get_resource_config_history(self, resource_type, resource_id, backend_region):
        """Returns configuration of resource for the current regional backend.

        Item returned in AWS Config format.

        NOTE: This is --NOT-- returning history as it is not supported in
        moto at this time. (PR's welcome!)

        As such, the later_time, earlier_time, limit, and next_token are
        ignored as this will only return 1 item. (If no items, it raises an
        exception).
        """
        # If the type isn't implemented then we won't find the item:
        if resource_type not in RESOURCE_MAP:
            raise ResourceNotDiscoveredException(resource_type, resource_id)

        # Is the resource type global?
        backend_query_region = (
            backend_region  # Always provide the backend this request arrived from.
        )
        if RESOURCE_MAP[resource_type].backends.get("global"):
            backend_region = "global"

        # If the backend region isn't implemented then we won't find the item:
        if not RESOURCE_MAP[resource_type].backends.get(backend_region):
            raise ResourceNotDiscoveredException(resource_type, resource_id)

        # Get the item:
        item = RESOURCE_MAP[resource_type].get_config_resource(
            resource_id, backend_region=backend_query_region
        )
        if not item:
            raise ResourceNotDiscoveredException(resource_type, resource_id)

        item["accountId"] = DEFAULT_ACCOUNT_ID

        return {"configurationItems": [item]}

    def batch_get_resource_config(self, resource_keys, backend_region):
        """Returns configuration of resource for the current regional backend.

        Item is returned in AWS Config format.

        :param resource_keys:
        :param backend_region:
        """
        # Can't have more than 100 items
        if len(resource_keys) > 100:
            raise TooManyResourceKeys(
                ["com.amazonaws.starling.dove.ResourceKey@12345"] * len(resource_keys)
            )

        results = []
        for resource in resource_keys:
            # Does the resource type exist?
            if not RESOURCE_MAP.get(resource["resourceType"]):
                # Not found so skip.
                continue

            # Is the resource type global?
            config_backend_region = backend_region
            backend_query_region = (
                backend_region  # Always provide the backend this request arrived from.
            )
            if RESOURCE_MAP[resource["resourceType"]].backends.get("global"):
                config_backend_region = "global"

            # If the backend region isn't implemented then we won't find the item:
            if not RESOURCE_MAP[resource["resourceType"]].backends.get(
                config_backend_region
            ):
                continue

            # Get the item:
            item = RESOURCE_MAP[resource["resourceType"]].get_config_resource(
                resource["resourceId"], backend_region=backend_query_region
            )
            if not item:
                continue

            item["accountId"] = DEFAULT_ACCOUNT_ID

            results.append(item)

        return {
            "baseConfigurationItems": results,
            "unprocessedResourceKeys": [],
        }  # At this time, moto is not adding unprocessed items.

    def batch_get_aggregate_resource_config(
        self, aggregator_name, resource_identifiers
    ):
        """Returns configuration of resource for current regional backend.

        Item is returned in AWS Config format.

        As far a moto goes -- the only real difference between this function
        and the `batch_get_resource_config` function is that this will require
        a Config Aggregator be set up a priori and can search based on resource
        regions.

        Note: moto will IGNORE the resource account ID in the search query.
        """
        if not self.config_aggregators.get(aggregator_name):
            raise NoSuchConfigurationAggregatorException()

        # Can't have more than 100 items
        if len(resource_identifiers) > 100:
            raise TooManyResourceKeys(
                ["com.amazonaws.starling.dove.AggregateResourceIdentifier@12345"]
                * len(resource_identifiers)
            )

        found = []
        not_found = []
        for identifier in resource_identifiers:
            resource_type = identifier["ResourceType"]
            resource_region = identifier["SourceRegion"]
            resource_id = identifier["ResourceId"]
            resource_name = identifier.get("ResourceName", None)

            # Does the resource type exist?
            if not RESOURCE_MAP.get(resource_type):
                not_found.append(identifier)
                continue

            # Get the item:
            item = RESOURCE_MAP[resource_type].get_config_resource(
                resource_id,
                resource_name=resource_name,
                resource_region=resource_region,
            )
            if not item:
                not_found.append(identifier)
                continue

            item["accountId"] = DEFAULT_ACCOUNT_ID

            # The 'tags' field is not included in aggregate results for some reason...
            item.pop("tags", None)

            found.append(item)

        return {
            "BaseConfigurationItems": found,
            "UnprocessedResourceIdentifiers": not_found,
        }

    def put_evaluations(self, evaluations=None, result_token=None, test_mode=False):
        if not evaluations:
            raise InvalidParameterValueException(
                "The Evaluations object in your request cannot be null."
                "Add the required parameters and try again."
            )

        if not result_token:
            raise InvalidResultTokenException()

        # Moto only supports PutEvaluations with test mode currently
        # (missing rule and token support).
        if not test_mode:
            raise NotImplementedError(
                "PutEvaluations without TestMode is not yet implemented"
            )

        return {
            "FailedEvaluations": [],
        }  # At this time, moto is not adding failed evaluations.

    def put_organization_conformance_pack(
        self,
        name,
        template_s3_uri,
        template_body,
        delivery_s3_bucket,
        delivery_s3_key_prefix,
        input_parameters,
        excluded_accounts,
    ):
        # a real validation of the content of the template is missing at the moment
        if not template_s3_uri and not template_body:
            raise ValidationException("Template body is invalid")

        if not re.match(r"s3://.*", template_s3_uri):
            raise ValidationException(
                "1 validation error detected: "
                "Value '{}' at 'templateS3Uri' failed to satisfy constraint: "
                "Member must satisfy regular expression pattern: "
                "s3://.*".format(template_s3_uri)
            )

        pack = self.organization_conformance_packs.get(name)

        if pack:
            pack.update(
                delivery_s3_bucket=delivery_s3_bucket,
                delivery_s3_key_prefix=delivery_s3_key_prefix,
                input_parameters=input_parameters,
                excluded_accounts=excluded_accounts,
            )
        else:
            pack = OrganizationConformancePack(
                region=self.region,
                name=name,
                delivery_s3_bucket=delivery_s3_bucket,
                delivery_s3_key_prefix=delivery_s3_key_prefix,
                input_parameters=input_parameters,
                excluded_accounts=excluded_accounts,
            )

        self.organization_conformance_packs[name] = pack

        return {
            "OrganizationConformancePackArn": pack.organization_conformance_pack_arn
        }

    def describe_organization_conformance_packs(self, names):
        packs = []

        for name in names:
            pack = self.organization_conformance_packs.get(name)

            if not pack:
                raise NoSuchOrganizationConformancePackException(
                    "One or more organization conformance packs with "
                    "specified names are not present. Ensure your names are "
                    "correct and try your request again later."
                )

            packs.append(pack.to_dict())

        return {"OrganizationConformancePacks": packs}

    def describe_organization_conformance_pack_statuses(self, names):
        packs = []
        statuses = []

        if names:
            for name in names:
                pack = self.organization_conformance_packs.get(name)

                if not pack:
                    raise NoSuchOrganizationConformancePackException(
                        "One or more organization conformance packs with "
                        "specified names are not present. Ensure your names "
                        "are correct and try your request again later."
                    )

                packs.append(pack)
        else:
            packs = list(self.organization_conformance_packs.values())

        for pack in packs:
            statuses.append(
                {
                    "OrganizationConformancePackName": pack.organization_conformance_pack_name,
                    "Status": pack._status,
                    "LastUpdateTime": pack.last_update_time,
                }
            )

        return {"OrganizationConformancePackStatuses": statuses}

    def get_organization_conformance_pack_detailed_status(self, name):
        pack = self.organization_conformance_packs.get(name)

        if not pack:
            raise NoSuchOrganizationConformancePackException(
                "One or more organization conformance packs with specified names are not present. "
                "Ensure your names are correct and try your request again later."
            )

        # actually here would be a list of all accounts in the organization
        statuses = [
            {
                "AccountId": DEFAULT_ACCOUNT_ID,
                "ConformancePackName": "OrgConformsPack-{0}".format(
                    pack._unique_pack_name
                ),
                "Status": pack._status,
                "LastUpdateTime": datetime2int(datetime.utcnow()),
            }
        ]

        return {"OrganizationConformancePackDetailedStatuses": statuses}

    def delete_organization_conformance_pack(self, name):
        pack = self.organization_conformance_packs.get(name)

        if not pack:
            raise NoSuchOrganizationConformancePackException(
                "Could not find an OrganizationConformancePack for given "
                "request with resourceName {}".format(name)
            )

        self.organization_conformance_packs.pop(name)

    def _match_arn(self, resource_arn):
        """Return config instance that has a matching ARN."""
        # The allowed resources are ConfigRule, ConfigurationAggregator,
        # and AggregatorAuthorization.
        allowed_resources = [
            {
                "configs": self.config_aggregators,
                "arn_attribute": "configuration_aggregator_arn",
            },
            {
                "configs": self.aggregation_authorizations,
                "arn_attribute": "aggregation_authorization_arn",
            },
            {"configs": self.config_rules, "arn_attribute": "config_rule_arn"},
        ]

        # Find matching config for given resource_arn among all the
        # allowed config resources.
        matched_config = None
        for resource in allowed_resources:
            for config in resource["configs"].values():
                if resource_arn == getattr(config, resource["arn_attribute"]):
                    matched_config = config
                    break

        if not matched_config:
            raise ResourceNotFoundException(resource_arn)
        return matched_config

    def tag_resource(self, resource_arn, tags):
        """Add tags in config with a matching ARN."""
        # Tag validation:
        tags = validate_tags(tags)

        # Find config with a matching ARN.
        matched_config = self._match_arn(resource_arn)

        # Merge the new tags with the existing tags.
        matched_config.tags.update(tags)

    def untag_resource(self, resource_arn, tag_keys):
        """Remove tags in config with a matching ARN.

        If the tags in the tag_keys don't match any keys for that
        ARN, they're just ignored.
        """
        if len(tag_keys) > MAX_TAGS_IN_ARG:
            raise TooManyTags(tag_keys)

        # Find config with a matching ARN.
        matched_config = self._match_arn(resource_arn)

        for tag_key in tag_keys:
            matched_config.tags.pop(tag_key, None)

    def list_tags_for_resource(
        self, resource_arn, limit, next_token
    ):  # pylint: disable=unused-argument
        """Return list of tags for AWS Config resource."""
        # The limit argument is essentially ignored as a config instance
        # can only have 50 tags, but we'll check the argument anyway.
        # Although the boto3 documentation indicates the limit is 50, boto3
        # accepts a limit value up to 100 as does the AWS CLI.
        limit = limit or DEFAULT_PAGE_SIZE
        if limit > DEFAULT_PAGE_SIZE:
            raise InvalidLimitException(limit)

        matched_config = self._match_arn(resource_arn)
        return {
            "Tags": [
                {"Key": k, "Value": v} for k, v in sorted(matched_config.tags.items())
            ]
        }

    def put_config_rule(self, config_rule, tags=None):
        """Add/Update config rule for evaluating resource compliance.

        TBD - Only the "accounting" of config rules are handled at the
        moment.  No events are created or triggered.  There is no
        interaction with the config recorder.
        """
        # If there is no rule_name, use the ARN or ID to get the
        # rule_name.
        rule_name = config_rule.get("ConfigRuleName")
        if rule_name:
            if len(rule_name) > 128:
                raise NameTooLongException(rule_name, "configRule.configRuleName", 128)
        else:
            # Can we find the rule using the ARN or ID?
            rule_arn = config_rule.get("ConfigRuleArn")
            rule_id = config_rule.get("ConfigRuleId")
            if not rule_arn and not rule_id:
                raise InvalidParameterValueException(
                    "One or more identifiers needs to be provided. Provide "
                    "Name or Id or Arn"
                )
            for config_rule_obj in self.config_rules.values():
                if rule_id and config_rule_obj.config_rule_id == rule_id:
                    rule_name = config_rule_obj.config_rule_name
                    break
                if rule_arn and config_rule_obj.config_rule_arn == rule_arn:
                    rule_name = config_rule_obj.config_rule_name
                    break
            else:
                raise InvalidParameterValueException(
                    "One or more identifiers needs to be provided. Provide "
                    "Name or Id or Arn"
                )

        tags = validate_tags(tags or [])

        # With the rule_name, determine whether it's for an existing rule
        # or whether a new rule should be created.
        rule = self.config_rules.get(rule_name)
        if rule:
            # Rule exists.  Make sure it isn't in use for another activity.
            rule_state = rule.config_rule_state
            if rule_state != "ACTIVE":
                activity = "deleted" if rule_state.startswith("DELET") else "evaluated"
                raise ResourceInUseException(
                    f"The rule {rule_name} is currently being {activity}.  "
                    f"Please retry after some time"
                )

            # Update the current rule.
            rule.modify_fields(self.region, config_rule, tags)
        else:
            # Create a new ConfigRule if the limit hasn't been reached.
            if len(self.config_rules) == ConfigRule.MAX_RULES:
                raise MaxNumberOfConfigRulesExceededException(
                    rule_name, ConfigRule.MAX_RULES
                )
            rule = ConfigRule(self.region, config_rule, tags)
            self.config_rules[rule_name] = rule
        return ""

    def describe_config_rules(self, config_rule_names, next_token):
        """Return details for the given ConfigRule names or for all rules."""
        result = {"ConfigRules": []}
        if not self.config_rules:
            return result

        rule_list = []
        if config_rule_names:
            for name in config_rule_names:
                if not self.config_rules.get(name):
                    raise NoSuchConfigRuleException(name)
                rule_list.append(name)
        else:
            rule_list = list(self.config_rules.keys())

        # The rules are not sorted alphanumerically.
        sorted_rules = sorted(rule_list)
        start = 0
        if next_token:
            if not self.config_rules.get(next_token):
                raise InvalidNextTokenException()
            start = sorted_rules.index(next_token)

        rule_list = sorted_rules[start : start + CONFIG_RULE_PAGE_SIZE]
        result["ConfigRules"] = [self.config_rules[x].to_dict() for x in rule_list]

        if len(sorted_rules) > (start + CONFIG_RULE_PAGE_SIZE):
            result["NextToken"] = sorted_rules[start + CONFIG_RULE_PAGE_SIZE]
        return result

    def delete_config_rule(self, rule_name):
        """Delete config rule used for evaluating resource compliance."""
        rule = self.config_rules.get(rule_name)
        if not rule:
            raise NoSuchConfigRuleException(rule_name)

        # The following logic is not applicable for moto as far as I can tell.
        # if rule.config_rule_state == "DELETING":
        #     raise ResourceInUseException(
        #         f"The rule {rule_name} is currently being deleted.  Please "
        #         f"retry after some time"
        #     )
        rule.config_rule_state = "DELETING"
        self.config_rules.pop(rule_name)


config_backends = BackendDict(ConfigBackend, "config")
