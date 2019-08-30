import json
import re
import time
import pkg_resources
import random
import string

from datetime import datetime

from boto3 import Session

from moto.config.exceptions import InvalidResourceTypeException, InvalidDeliveryFrequency, \
    InvalidConfigurationRecorderNameException, NameTooLongException, \
    MaxNumberOfConfigurationRecordersExceededException, InvalidRecordingGroupException, \
    NoSuchConfigurationRecorderException, NoAvailableConfigurationRecorderException, \
    InvalidDeliveryChannelNameException, NoSuchBucketException, InvalidS3KeyPrefixException, \
    InvalidSNSTopicARNException, MaxNumberOfDeliveryChannelsExceededException, NoAvailableDeliveryChannelException, \
    NoSuchDeliveryChannelException, LastDeliveryChannelDeleteFailedException, TagKeyTooBig, \
    TooManyTags, TagValueTooBig, TooManyAccountSources, InvalidParameterValueException, InvalidNextTokenException, \
    NoSuchConfigurationAggregatorException, InvalidTagCharacters, DuplicateTags

from moto.core import BaseBackend, BaseModel

DEFAULT_ACCOUNT_ID = 123456789012
POP_STRINGS = [
    'capitalizeStart',
    'CapitalizeStart',
    'capitalizeArn',
    'CapitalizeArn',
    'capitalizeARN',
    'CapitalizeARN'
]
DEFAULT_PAGE_SIZE = 100


def datetime2int(date):
    return int(time.mktime(date.timetuple()))


def snake_to_camels(original, cap_start, cap_arn):
    parts = original.split('_')

    camel_cased = parts[0].lower() + ''.join(p.title() for p in parts[1:])

    if cap_arn:
        camel_cased = camel_cased.replace('Arn', 'ARN')  # Some config services use 'ARN' instead of 'Arn'

    if cap_start:
        camel_cased = camel_cased[0].upper() + camel_cased[1::]

    return camel_cased


def random_string():
    """Returns a random set of 8 lowercase letters for the Config Aggregator ARN"""
    chars = []
    for x in range(0, 8):
        chars.append(random.choice(string.ascii_lowercase))

    return "".join(chars)


def validate_tag_key(tag_key, exception_param='tags.X.member.key'):
    """Validates the tag key.

    :param tag_key: The tag key to check against.
    :param exception_param: The exception parameter to send over to help format the message. This is to reflect
                            the difference between the tag and untag APIs.
    :return:
    """
    # Validate that the key length is correct:
    if len(tag_key) > 128:
        raise TagKeyTooBig(tag_key, param=exception_param)

    # Validate that the tag key fits the proper Regex:
    # [\w\s_.:/=+\-@]+ SHOULD be the same as the Java regex on the AWS documentation: [\p{L}\p{Z}\p{N}_.:/=+\-@]+
    match = re.findall(r'[\w\s_.:/=+\-@]+', tag_key)
    # Kudos if you can come up with a better way of doing a global search :)
    if not len(match) or len(match[0]) < len(tag_key):
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

    if len(tags) > 50:
        raise TooManyTags(tags)

    for tag in tags:
        # Validate the Key:
        validate_tag_key(tag['Key'])
        check_tag_duplicate(proper_tags, tag['Key'])

        # Validate the Value:
        if len(tag['Value']) > 256:
            raise TagValueTooBig(tag['Value'])

        proper_tags[tag['Key']] = tag['Value']

    return proper_tags


class ConfigEmptyDictable(BaseModel):
    """Base class to make serialization easy. This assumes that the sub-class will NOT return 'None's in the JSON."""

    def __init__(self, capitalize_start=False, capitalize_arn=True):
        """Assists with the serialization of the config object
        :param capitalize_start: For some Config services, the first letter is lowercase -- for others it's capital
        :param capitalize_arn: For some Config services, the API expects 'ARN' and for others, it expects 'Arn'
        """
        self.capitalize_start = capitalize_start
        self.capitalize_arn = capitalize_arn

    def to_dict(self):
        data = {}
        for item, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, ConfigEmptyDictable):
                    data[snake_to_camels(item, self.capitalize_start, self.capitalize_arn)] = value.to_dict()
                else:
                    data[snake_to_camels(item, self.capitalize_start, self.capitalize_arn)] = value

        # Cleanse the extra properties:
        for prop in POP_STRINGS:
            data.pop(prop, None)

        return data


class ConfigRecorderStatus(ConfigEmptyDictable):

    def __init__(self, name):
        super(ConfigRecorderStatus, self).__init__()

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
        self.last_status = 'PENDING'
        self.last_start_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())

    def stop(self):
        self.recording = False
        self.last_stop_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())


class ConfigDeliverySnapshotProperties(ConfigEmptyDictable):

    def __init__(self, delivery_frequency):
        super(ConfigDeliverySnapshotProperties, self).__init__()

        self.delivery_frequency = delivery_frequency


class ConfigDeliveryChannel(ConfigEmptyDictable):

    def __init__(self, name, s3_bucket_name, prefix=None, sns_arn=None, snapshot_properties=None):
        super(ConfigDeliveryChannel, self).__init__()

        self.name = name
        self.s3_bucket_name = s3_bucket_name
        self.s3_key_prefix = prefix
        self.sns_topic_arn = sns_arn
        self.config_snapshot_delivery_properties = snapshot_properties


class RecordingGroup(ConfigEmptyDictable):

    def __init__(self, all_supported=True, include_global_resource_types=False, resource_types=None):
        super(RecordingGroup, self).__init__()

        self.all_supported = all_supported
        self.include_global_resource_types = include_global_resource_types
        self.resource_types = resource_types


class ConfigRecorder(ConfigEmptyDictable):

    def __init__(self, role_arn, recording_group, name='default', status=None):
        super(ConfigRecorder, self).__init__()

        self.name = name
        self.role_arn = role_arn
        self.recording_group = recording_group

        if not status:
            self.status = ConfigRecorderStatus(name)
        else:
            self.status = status


class AccountAggregatorSource(ConfigEmptyDictable):

    def __init__(self, account_ids, aws_regions=None, all_aws_regions=None):
        super(AccountAggregatorSource, self).__init__(capitalize_start=True)

        # Can't have both the regions and all_regions flag present -- also can't have them both missing:
        if aws_regions and all_aws_regions:
            raise InvalidParameterValueException('Your configuration aggregator contains a list of regions and also specifies '
                                                 'the use of all regions. You must choose one of these options.')

        if not (aws_regions or all_aws_regions):
            raise InvalidParameterValueException('Your request does not specify any regions. Select AWS Config-supported '
                                                 'regions and try again.')

        self.account_ids = account_ids
        self.aws_regions = aws_regions

        if not all_aws_regions:
            all_aws_regions = False

        self.all_aws_regions = all_aws_regions


class OrganizationAggregationSource(ConfigEmptyDictable):

    def __init__(self, role_arn, aws_regions=None, all_aws_regions=None):
        super(OrganizationAggregationSource, self).__init__(capitalize_start=True, capitalize_arn=False)

        # Can't have both the regions and all_regions flag present -- also can't have them both missing:
        if aws_regions and all_aws_regions:
            raise InvalidParameterValueException('Your configuration aggregator contains a list of regions and also specifies '
                                                 'the use of all regions. You must choose one of these options.')

        if not (aws_regions or all_aws_regions):
            raise InvalidParameterValueException('Your request does not specify any regions. Select AWS Config-supported '
                                                 'regions and try again.')

        self.role_arn = role_arn
        self.aws_regions = aws_regions

        if not all_aws_regions:
            all_aws_regions = False

        self.all_aws_regions = all_aws_regions


class ConfigAggregator(ConfigEmptyDictable):

    def __init__(self, name, region, account_sources=None, org_source=None, tags=None):
        super(ConfigAggregator, self).__init__(capitalize_start=True, capitalize_arn=False)

        self.configuration_aggregator_name = name
        self.configuration_aggregator_arn = 'arn:aws:config:{region}:{id}:config-aggregator/config-aggregator-{random}'.format(
            region=region,
            id=DEFAULT_ACCOUNT_ID,
            random=random_string()
        )
        self.account_aggregation_sources = account_sources
        self.organization_aggregation_source = org_source
        self.creation_time = datetime2int(datetime.utcnow())
        self.last_updated_time = datetime2int(datetime.utcnow())

        # Tags are listed in the list_tags_for_resource API call ... not implementing yet -- please feel free to!
        self.tags = tags or {}

    # Override the to_dict so that we can format the tags properly...
    def to_dict(self):
        result = super(ConfigAggregator, self).to_dict()

        # Override the account aggregation sources if present:
        if self.account_aggregation_sources:
            result['AccountAggregationSources'] = [a.to_dict() for a in self.account_aggregation_sources]

        # Tags are listed in the list_tags_for_resource API call ... not implementing yet -- please feel free to!
        # if self.tags:
        #     result['Tags'] = [{'Key': key, 'Value': value} for key, value in self.tags.items()]

        return result


class ConfigAggregationAuthorization(ConfigEmptyDictable):

    def __init__(self, current_region, authorized_account_id, authorized_aws_region, tags=None):
        super(ConfigAggregationAuthorization, self).__init__(capitalize_start=True, capitalize_arn=False)

        self.aggregation_authorization_arn = 'arn:aws:config:{region}:{id}:aggregation-authorization/' \
                                             '{auth_account}/{auth_region}'.format(region=current_region,
                                                                                   id=DEFAULT_ACCOUNT_ID,
                                                                                   auth_account=authorized_account_id,
                                                                                   auth_region=authorized_aws_region)
        self.authorized_account_id = authorized_account_id
        self.authorized_aws_region = authorized_aws_region
        self.creation_time = datetime2int(datetime.utcnow())

        # Tags are listed in the list_tags_for_resource API call ... not implementing yet -- please feel free to!
        self.tags = tags or {}


class ConfigBackend(BaseBackend):

    def __init__(self):
        self.recorders = {}
        self.delivery_channels = {}
        self.config_aggregators = {}
        self.aggregation_authorizations = {}

    @staticmethod
    def _validate_resource_types(resource_list):
        # Load the service file:
        resource_package = 'botocore'
        resource_path = '/'.join(('data', 'config', '2014-11-12', 'service-2.json'))
        config_schema = json.loads(pkg_resources.resource_string(resource_package, resource_path))

        # Verify that each entry exists in the supported list:
        bad_list = []
        for resource in resource_list:
            # For PY2:
            r_str = str(resource)

            if r_str not in config_schema['shapes']['ResourceType']['enum']:
                bad_list.append(r_str)

        if bad_list:
            raise InvalidResourceTypeException(bad_list, config_schema['shapes']['ResourceType']['enum'])

    @staticmethod
    def _validate_delivery_snapshot_properties(properties):
        # Load the service file:
        resource_package = 'botocore'
        resource_path = '/'.join(('data', 'config', '2014-11-12', 'service-2.json'))
        conifg_schema = json.loads(pkg_resources.resource_string(resource_package, resource_path))

        # Verify that the deliveryFrequency is set to an acceptable value:
        if properties.get('deliveryFrequency', None) not in \
                conifg_schema['shapes']['MaximumExecutionFrequency']['enum']:
            raise InvalidDeliveryFrequency(properties.get('deliveryFrequency', None),
                                           conifg_schema['shapes']['MaximumExecutionFrequency']['enum'])

    def put_configuration_aggregator(self, config_aggregator, region):
        # Validate the name:
        if len(config_aggregator['ConfigurationAggregatorName']) > 256:
            raise NameTooLongException(config_aggregator['ConfigurationAggregatorName'], 'configurationAggregatorName')

        account_sources = None
        org_source = None

        # Tag validation:
        tags = validate_tags(config_aggregator.get('Tags', []))

        # Exception if both AccountAggregationSources and OrganizationAggregationSource are supplied:
        if config_aggregator.get('AccountAggregationSources') and config_aggregator.get('OrganizationAggregationSource'):
            raise InvalidParameterValueException('The configuration aggregator cannot be created because your request contains both the'
                                                 ' AccountAggregationSource and the OrganizationAggregationSource. Include only '
                                                 'one aggregation source and try again.')

        # If neither are supplied:
        if not config_aggregator.get('AccountAggregationSources') and not config_aggregator.get('OrganizationAggregationSource'):
            raise InvalidParameterValueException('The configuration aggregator cannot be created because your request is missing either '
                                                 'the AccountAggregationSource or the OrganizationAggregationSource. Include the '
                                                 'appropriate aggregation source and try again.')

        if config_aggregator.get('AccountAggregationSources'):
            # Currently, only 1 account aggregation source can be set:
            if len(config_aggregator['AccountAggregationSources']) > 1:
                raise TooManyAccountSources(len(config_aggregator['AccountAggregationSources']))

            account_sources = []
            for a in config_aggregator['AccountAggregationSources']:
                account_sources.append(AccountAggregatorSource(a['AccountIds'], aws_regions=a.get('AwsRegions'),
                                                               all_aws_regions=a.get('AllAwsRegions')))

        else:
            org_source = OrganizationAggregationSource(config_aggregator['OrganizationAggregationSource']['RoleArn'],
                                                       aws_regions=config_aggregator['OrganizationAggregationSource'].get('AwsRegions'),
                                                       all_aws_regions=config_aggregator['OrganizationAggregationSource'].get(
                                                           'AllAwsRegions'))

        # Grab the existing one if it exists and update it:
        if not self.config_aggregators.get(config_aggregator['ConfigurationAggregatorName']):
            aggregator = ConfigAggregator(config_aggregator['ConfigurationAggregatorName'], region, account_sources=account_sources,
                                          org_source=org_source, tags=tags)
            self.config_aggregators[config_aggregator['ConfigurationAggregatorName']] = aggregator

        else:
            aggregator = self.config_aggregators[config_aggregator['ConfigurationAggregatorName']]
            aggregator.tags = tags
            aggregator.account_aggregation_sources = account_sources
            aggregator.organization_aggregation_source = org_source
            aggregator.last_updated_time = datetime2int(datetime.utcnow())

        return aggregator.to_dict()

    def describe_configuration_aggregators(self, names, token, limit):
        limit = DEFAULT_PAGE_SIZE if not limit or limit < 0 else limit
        agg_list = []
        result = {'ConfigurationAggregators': []}

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
        agg_list = sorted_aggregators[start:(start + limit)]
        result['ConfigurationAggregators'] = [self.config_aggregators[agg].to_dict() for agg in agg_list]

        if len(sorted_aggregators) > (start + limit):
            result['NextToken'] = sorted_aggregators[start + limit]

        return result

    def delete_configuration_aggregator(self, config_aggregator):
        if not self.config_aggregators.get(config_aggregator):
            raise NoSuchConfigurationAggregatorException()

        del self.config_aggregators[config_aggregator]

    def put_aggregation_authorization(self, current_region, authorized_account, authorized_region, tags):
        # Tag validation:
        tags = validate_tags(tags or [])

        # Does this already exist?
        key = '{}/{}'.format(authorized_account, authorized_region)
        agg_auth = self.aggregation_authorizations.get(key)
        if not agg_auth:
            agg_auth = ConfigAggregationAuthorization(current_region, authorized_account, authorized_region, tags=tags)
            self.aggregation_authorizations['{}/{}'.format(authorized_account, authorized_region)] = agg_auth
        else:
            # Only update the tags:
            agg_auth.tags = tags

        return agg_auth.to_dict()

    def describe_aggregation_authorizations(self, token, limit):
        limit = DEFAULT_PAGE_SIZE if not limit or limit < 0 else limit
        result = {'AggregationAuthorizations': []}

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
        auth_list = sorted_authorizations[start:(start + limit)]
        result['AggregationAuthorizations'] = [self.aggregation_authorizations[auth].to_dict() for auth in auth_list]

        if len(sorted_authorizations) > (start + limit):
            result['NextToken'] = sorted_authorizations[start + limit]

        return result

    def delete_aggregation_authorization(self, authorized_account, authorized_region):
        # This will always return a 200 -- regardless if there is or isn't an existing
        # aggregation authorization.
        key = '{}/{}'.format(authorized_account, authorized_region)
        self.aggregation_authorizations.pop(key, None)

    def put_configuration_recorder(self, config_recorder):
        # Validate the name:
        if not config_recorder.get('name'):
            raise InvalidConfigurationRecorderNameException(config_recorder.get('name'))
        if len(config_recorder.get('name')) > 256:
            raise NameTooLongException(config_recorder.get('name'), 'configurationRecorder.name')

        # We're going to assume that the passed in Role ARN is correct.

        # Config currently only allows 1 configuration recorder for an account:
        if len(self.recorders) == 1 and not self.recorders.get(config_recorder['name']):
            raise MaxNumberOfConfigurationRecordersExceededException(config_recorder['name'])

        # Is this updating an existing one?
        recorder_status = None
        if self.recorders.get(config_recorder['name']):
            recorder_status = self.recorders[config_recorder['name']].status

        # Validate the Recording Group:
        if config_recorder.get('recordingGroup') is None:
            recording_group = RecordingGroup()
        else:
            rg = config_recorder['recordingGroup']

            # If an empty dict is passed in, then bad:
            if not rg:
                raise InvalidRecordingGroupException()

            # Can't have both the resource types specified and the other flags as True.
            if rg.get('resourceTypes') and (
                    rg.get('allSupported', False) or
                    rg.get('includeGlobalResourceTypes', False)):
                raise InvalidRecordingGroupException()

            # Must supply resourceTypes if 'allSupported' is not supplied:
            if not rg.get('allSupported') and not rg.get('resourceTypes'):
                raise InvalidRecordingGroupException()

            # Validate that the list provided is correct:
            self._validate_resource_types(rg.get('resourceTypes', []))

            recording_group = RecordingGroup(
                all_supported=rg.get('allSupported', True),
                include_global_resource_types=rg.get('includeGlobalResourceTypes', False),
                resource_types=rg.get('resourceTypes', [])
            )

        self.recorders[config_recorder['name']] = \
            ConfigRecorder(config_recorder['roleARN'], recording_group, name=config_recorder['name'],
                           status=recorder_status)

    def describe_configuration_recorders(self, recorder_names):
        recorders = []

        if recorder_names:
            for rn in recorder_names:
                if not self.recorders.get(rn):
                    raise NoSuchConfigurationRecorderException(rn)

                # Format the recorder:
                recorders.append(self.recorders[rn].to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.to_dict())

        return recorders

    def describe_configuration_recorder_status(self, recorder_names):
        recorders = []

        if recorder_names:
            for rn in recorder_names:
                if not self.recorders.get(rn):
                    raise NoSuchConfigurationRecorderException(rn)

                # Format the recorder:
                recorders.append(self.recorders[rn].status.to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.status.to_dict())

        return recorders

    def put_delivery_channel(self, delivery_channel):
        # Must have a configuration recorder:
        if not self.recorders:
            raise NoAvailableConfigurationRecorderException()

        # Validate the name:
        if not delivery_channel.get('name'):
            raise InvalidDeliveryChannelNameException(delivery_channel.get('name'))
        if len(delivery_channel.get('name')) > 256:
            raise NameTooLongException(delivery_channel.get('name'), 'deliveryChannel.name')

        # We are going to assume that the bucket exists -- but will verify if the bucket provided is blank:
        if not delivery_channel.get('s3BucketName'):
            raise NoSuchBucketException()

        # We are going to assume that the bucket has the correct policy attached to it. We are only going to verify
        # if the prefix provided is not an empty string:
        if delivery_channel.get('s3KeyPrefix', None) == '':
            raise InvalidS3KeyPrefixException()

        # Ditto for SNS -- Only going to assume that the ARN provided is not an empty string:
        if delivery_channel.get('snsTopicARN', None) == '':
            raise InvalidSNSTopicARNException()

        # Config currently only allows 1 delivery channel for an account:
        if len(self.delivery_channels) == 1 and not self.delivery_channels.get(delivery_channel['name']):
            raise MaxNumberOfDeliveryChannelsExceededException(delivery_channel['name'])

        if not delivery_channel.get('configSnapshotDeliveryProperties'):
            dp = None

        else:
            # Validate the config snapshot delivery properties:
            self._validate_delivery_snapshot_properties(delivery_channel['configSnapshotDeliveryProperties'])

            dp = ConfigDeliverySnapshotProperties(
                delivery_channel['configSnapshotDeliveryProperties']['deliveryFrequency'])

        self.delivery_channels[delivery_channel['name']] = \
            ConfigDeliveryChannel(delivery_channel['name'], delivery_channel['s3BucketName'],
                                  prefix=delivery_channel.get('s3KeyPrefix', None),
                                  sns_arn=delivery_channel.get('snsTopicARN', None),
                                  snapshot_properties=dp)

    def describe_delivery_channels(self, channel_names):
        channels = []

        if channel_names:
            for cn in channel_names:
                if not self.delivery_channels.get(cn):
                    raise NoSuchDeliveryChannelException(cn)

                # Format the delivery channel:
                channels.append(self.delivery_channels[cn].to_dict())

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


config_backends = {}
boto3_session = Session()
for region in boto3_session.get_available_regions('config'):
    config_backends[region] = ConfigBackend()
