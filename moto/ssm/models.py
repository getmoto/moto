from __future__ import unicode_literals

from collections import defaultdict

from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.ec2 import ec2_backends

import datetime
import time
import uuid


class Parameter(BaseModel):
    def __init__(self, name, value, type, description, keyid, last_modified_date, version):
        self.name = name
        self.type = type
        self.description = description
        self.keyid = keyid
        self.last_modified_date = last_modified_date
        self.version = version

        if self.type == 'SecureString':
            self.value = self.encrypt(value)
        else:
            self.value = value

    def encrypt(self, value):
        return 'kms:{}:'.format(self.keyid or 'default') + value

    def decrypt(self, value):
        if self.type != 'SecureString':
            return value

        prefix = 'kms:{}:'.format(self.keyid or 'default')
        if value.startswith(prefix):
            return value[len(prefix):]

    def response_object(self, decrypt=False):
        r = {
            'Name': self.name,
            'Type': self.type,
            'Value': self.decrypt(self.value) if decrypt else self.value,
            'Version': self.version,
        }

        return r

    def describe_response_object(self, decrypt=False):
        r = self.response_object(decrypt)
        r['LastModifiedDate'] = int(self.last_modified_date)
        r['LastModifiedUser'] = 'N/A'

        if self.description:
            r['Description'] = self.description

        if self.keyid:
            r['KeyId'] = self.keyid
        return r


MAX_TIMEOUT_SECONDS = 3600


class Command(BaseModel):
    def __init__(self, comment='', document_name='', timeout_seconds=MAX_TIMEOUT_SECONDS,
            instance_ids=None, max_concurrency='', max_errors='',
            notification_config=None, output_s3_bucket_name='',
            output_s3_key_prefix='', output_s3_region='', parameters=None,
            service_role_arn='', targets=None):

        if instance_ids is None:
            instance_ids = []

        if notification_config is None:
            notification_config = {}

        if parameters is None:
            parameters = {}

        if targets is None:
            targets = []

        self.error_count = 0
        self.completed_count = len(instance_ids)
        self.target_count = len(instance_ids)
        self.command_id = str(uuid.uuid4())
        self.status = 'Success'
        self.status_details = 'Details placeholder'

        now = datetime.datetime.now()
        self.requested_date_time = now.isoformat()
        expires_after = now + datetime.timedelta(0, timeout_seconds)
        self.expires_after = expires_after.isoformat()

        self.comment = comment
        self.document_name = document_name
        self.instance_ids = instance_ids
        self.max_concurrency = max_concurrency
        self.max_errors = max_errors
        self.notification_config = notification_config
        self.output_s3_bucket_name = output_s3_bucket_name
        self.output_s3_key_prefix = output_s3_key_prefix
        self.output_s3_region = output_s3_region
        self.parameters = parameters
        self.service_role_arn = service_role_arn
        self.targets = targets

    def response_object(self):
        r = {
            'CommandId': self.command_id,
            'Comment': self.comment,
            'CompletedCount': self.completed_count,
            'DocumentName': self.document_name,
            'ErrorCount': self.error_count,
            'ExpiresAfter': self.expires_after,
            'InstanceIds': self.instance_ids,
            'MaxConcurrency': self.max_concurrency,
            'MaxErrors': self.max_errors,
            'NotificationConfig': self.notification_config,
            'OutputS3Region': self.output_s3_region,
            'OutputS3BucketName': self.output_s3_bucket_name,
            'OutputS3KeyPrefix': self.output_s3_key_prefix,
            'Parameters': self.parameters,
            'RequestedDateTime': self.requested_date_time,
            'ServiceRole': self.service_role_arn,
            'Status': self.status,
            'StatusDetails': self.status_details,
            'TargetCount': self.target_count,
            'Targets': self.targets,
        }

        return r


class SimpleSystemManagerBackend(BaseBackend):

    def __init__(self):
        self._parameters = {}
        self._resource_tags = defaultdict(lambda: defaultdict(dict))
        self._commands = []

    def delete_parameter(self, name):
        try:
            del self._parameters[name]
        except KeyError:
            pass

    def delete_parameters(self, names):
        result = []
        for name in names:
            try:
                del self._parameters[name]
                result.append(name)
            except KeyError:
                pass
        return result

    def get_all_parameters(self):
        result = []
        for k, _ in self._parameters.items():
            result.append(self._parameters[k])
        return result

    def get_parameters(self, names, with_decryption):
        result = []
        for name in names:
            if name in self._parameters:
                result.append(self._parameters[name])
        return result

    def get_parameters_by_path(self, path, with_decryption, recursive, filters=None):
        """Implement the get-parameters-by-path-API in the backend."""
        result = []
        # path could be with or without a trailing /. we handle this
        # difference here.
        path = path.rstrip('/') + '/'
        for param in self._parameters:
            if path != '/' and not param.startswith(path):
                continue
            if '/' in param[len(path) + 1:] and not recursive:
                continue
            if not self._match_filters(self._parameters[param], filters):
                continue
            result.append(self._parameters[param])

        return result

    @staticmethod
    def _match_filters(parameter, filters=None):
        """Return True if the given parameter matches all the filters"""
        for filter_obj in (filters or []):
            key = filter_obj['Key']
            option = filter_obj.get('Option', 'Equals')
            values = filter_obj.get('Values', [])

            what = None
            if key == 'Type':
                what = parameter.type
            elif key == 'KeyId':
                what = parameter.keyid

            if option == 'Equals'\
                    and not any(what == value for value in values):
                return False
            elif option == 'BeginsWith'\
                    and not any(what.startswith(value) for value in values):
                return False
        # True if no false match (or no filters at all)
        return True

    def get_parameter(self, name, with_decryption):
        if name in self._parameters:
            return self._parameters[name]
        return None

    def put_parameter(self, name, description, value, type, keyid, overwrite):
        previous_parameter = self._parameters.get(name)
        version = 1

        if previous_parameter:
            version = previous_parameter.version + 1

            if not overwrite:
                return

        last_modified_date = time.time()
        self._parameters[name] = Parameter(
            name, value, type, description, keyid, last_modified_date, version)
        return version

    def add_tags_to_resource(self, resource_type, resource_id, tags):
        for key, value in tags.items():
            self._resource_tags[resource_type][resource_id][key] = value

    def remove_tags_from_resource(self, resource_type, resource_id, keys):
        tags = self._resource_tags[resource_type][resource_id]
        for key in keys:
            if key in tags:
                del tags[key]

    def list_tags_for_resource(self, resource_type, resource_id):
        return self._resource_tags[resource_type][resource_id]

    def send_command(self, **kwargs):
        command = Command(
            comment=kwargs.get('Comment', ''),
            document_name=kwargs.get('DocumentName'),
            timeout_seconds=kwargs.get('TimeoutSeconds', 3600),
            instance_ids=kwargs.get('InstanceIds', []),
            max_concurrency=kwargs.get('MaxConcurrency', '50'),
            max_errors=kwargs.get('MaxErrors', '0'),
            notification_config=kwargs.get('NotificationConfig', {
                'NotificationArn': 'string',
                'NotificationEvents': ['Success'],
                'NotificationType': 'Command'
            }),
            output_s3_bucket_name=kwargs.get('OutputS3BucketName', ''),
            output_s3_key_prefix=kwargs.get('OutputS3KeyPrefix', ''),
            output_s3_region=kwargs.get('OutputS3Region', ''),
            parameters=kwargs.get('Parameters', {}),
            service_role_arn=kwargs.get('ServiceRoleArn', ''),
            targets=kwargs.get('Targets', []))

        self._commands.append(command)
        return {
            'Command': command.response_object()
        }

    def list_commands(self, **kwargs):
        """
        https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_ListCommands.html
        """
        commands = self._commands

        command_id = kwargs.get('CommandId', None)
        if command_id:
            commands = [self.get_command_by_id(command_id)]
        instance_id = kwargs.get('InstanceId', None)
        if instance_id:
            commands = self.get_commands_by_instance_id(instance_id)

        return {
            'Commands': [command.response_object() for command in commands]
        }

    def get_command_by_id(self, id):
        command = next(
            (command for command in self._commands if command.command_id == id), None)

        if command is None:
            raise RESTError('InvalidCommandId', 'Invalid command id.')

        return command

    def get_commands_by_instance_id(self, instance_id):
        return [
            command for command in self._commands
            if instance_id in command.instance_ids]


ssm_backends = {}
for region, ec2_backend in ec2_backends.items():
    ssm_backends[region] = SimpleSystemManagerBackend()
