from __future__ import unicode_literals

import hashlib
import random
import re
import string
import time
import uuid
from collections import OrderedDict
from datetime import datetime

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from .exceptions import (
    CertificateStateException,
    DeleteConflictException,
    ResourceNotFoundException,
    InvalidRequestException,
    InvalidStateTransitionException,
    VersionConflictException,
    ResourceAlreadyExistsException,
)
from moto.utilities.utils import random_string


class FakeThing(BaseModel):
    def __init__(self, thing_name, thing_type, attributes, region_name):
        self.region_name = region_name
        self.thing_name = thing_name
        self.thing_type = thing_type
        self.attributes = attributes
        self.arn = "arn:aws:iot:%s:1:thing/%s" % (self.region_name, thing_name)
        self.version = 1
        # TODO: we need to handle "version"?

        # for iot-data
        self.thing_shadow = None

    def to_dict(self, include_default_client_id=False):
        obj = {
            "thingName": self.thing_name,
            "thingArn": self.arn,
            "attributes": self.attributes,
            "version": self.version,
        }
        if self.thing_type:
            obj["thingTypeName"] = self.thing_type.thing_type_name
        if include_default_client_id:
            obj["defaultClientId"] = self.thing_name
        return obj


class FakeThingType(BaseModel):
    def __init__(self, thing_type_name, thing_type_properties, region_name):
        self.region_name = region_name
        self.thing_type_name = thing_type_name
        self.thing_type_properties = thing_type_properties
        self.thing_type_id = str(uuid.uuid4())  # I don't know the rule of id
        t = time.time()
        self.metadata = {"deprecated": False, "creationDate": int(t * 1000) / 1000.0}
        self.arn = "arn:aws:iot:%s:1:thingtype/%s" % (self.region_name, thing_type_name)

    def to_dict(self):
        return {
            "thingTypeName": self.thing_type_name,
            "thingTypeId": self.thing_type_id,
            "thingTypeProperties": self.thing_type_properties,
            "thingTypeMetadata": self.metadata,
        }


class FakeThingGroup(BaseModel):
    def __init__(
        self,
        thing_group_name,
        parent_group_name,
        thing_group_properties,
        region_name,
        thing_groups,
    ):
        self.region_name = region_name
        self.thing_group_name = thing_group_name
        self.thing_group_id = str(uuid.uuid4())  # I don't know the rule of id
        self.version = 1  # TODO: tmp
        self.parent_group_name = parent_group_name
        self.thing_group_properties = thing_group_properties or {}
        t = time.time()
        self.metadata = {"creationDate": int(t * 1000) / 1000.0}
        if parent_group_name:
            self.metadata["parentGroupName"] = parent_group_name
            # initilize rootToParentThingGroups
            if "rootToParentThingGroups" not in self.metadata:
                self.metadata["rootToParentThingGroups"] = []
            # search for parent arn
            for thing_group_arn, thing_group in thing_groups.items():
                if thing_group.thing_group_name == parent_group_name:
                    parent_thing_group_structure = thing_group
                    break
            # if parent arn found (should always be found)
            if parent_thing_group_structure:
                # copy parent's rootToParentThingGroups
                if "rootToParentThingGroups" in parent_thing_group_structure.metadata:
                    self.metadata["rootToParentThingGroups"].extend(
                        parent_thing_group_structure.metadata["rootToParentThingGroups"]
                    )
                self.metadata["rootToParentThingGroups"].extend(
                    [
                        {
                            "groupName": parent_group_name,
                            "groupArn": parent_thing_group_structure.arn,
                        }
                    ]
                )
        self.arn = "arn:aws:iot:%s:1:thinggroup/%s" % (
            self.region_name,
            thing_group_name,
        )
        self.things = OrderedDict()

    def to_dict(self):
        return {
            "thingGroupName": self.thing_group_name,
            "thingGroupId": self.thing_group_id,
            "version": self.version,
            "thingGroupProperties": self.thing_group_properties,
            "thingGroupMetadata": self.metadata,
        }


class FakeCertificate(BaseModel):
    def __init__(self, certificate_pem, status, region_name, ca_certificate_pem=None):
        m = hashlib.sha256()
        m.update(certificate_pem.encode("utf-8"))
        self.certificate_id = m.hexdigest()
        self.arn = "arn:aws:iot:%s:1:cert/%s" % (region_name, self.certificate_id)
        self.certificate_pem = certificate_pem
        self.status = status

        # TODO: must adjust
        self.owner = "1"
        self.transfer_data = {}
        self.creation_date = time.time()
        self.last_modified_date = self.creation_date

        self.ca_certificate_id = None
        self.ca_certificate_pem = ca_certificate_pem
        if ca_certificate_pem:
            m.update(ca_certificate_pem.encode("utf-8"))
            self.ca_certificate_id = m.hexdigest()

    def to_dict(self):
        return {
            "certificateArn": self.arn,
            "certificateId": self.certificate_id,
            "caCertificateId": self.ca_certificate_id,
            "status": self.status,
            "creationDate": self.creation_date,
        }

    def to_description_dict(self):
        """
        You might need keys below in some situation
          - caCertificateId
          - previousOwnedBy
        """
        return {
            "certificateArn": self.arn,
            "certificateId": self.certificate_id,
            "status": self.status,
            "certificatePem": self.certificate_pem,
            "ownedBy": self.owner,
            "creationDate": self.creation_date,
            "lastModifiedDate": self.last_modified_date,
            "transferData": self.transfer_data,
        }


class FakePolicy(BaseModel):
    def __init__(self, name, document, region_name, default_version_id="1"):
        self.name = name
        self.document = document
        self.arn = "arn:aws:iot:%s:1:policy/%s" % (region_name, name)
        self.default_version_id = default_version_id
        self.versions = [FakePolicyVersion(self.name, document, True, region_name)]

    def to_get_dict(self):
        return {
            "policyName": self.name,
            "policyArn": self.arn,
            "policyDocument": self.document,
            "defaultVersionId": self.default_version_id,
        }

    def to_dict_at_creation(self):
        return {
            "policyName": self.name,
            "policyArn": self.arn,
            "policyDocument": self.document,
            "policyVersionId": self.default_version_id,
        }

    def to_dict(self):
        return {"policyName": self.name, "policyArn": self.arn}


class FakePolicyVersion(object):
    def __init__(self, policy_name, document, is_default, region_name):
        self.name = policy_name
        self.arn = "arn:aws:iot:%s:1:policy/%s" % (region_name, policy_name)
        self.document = document or {}
        self.is_default = is_default
        self.version_id = "1"

        self.create_datetime = time.mktime(datetime(2015, 1, 1).timetuple())
        self.last_modified_datetime = time.mktime(datetime(2015, 1, 2).timetuple())

    def to_get_dict(self):
        return {
            "policyName": self.name,
            "policyArn": self.arn,
            "policyDocument": self.document,
            "policyVersionId": self.version_id,
            "isDefaultVersion": self.is_default,
            "creationDate": self.create_datetime,
            "lastModifiedDate": self.last_modified_datetime,
            "generationId": self.version_id,
        }

    def to_dict_at_creation(self):
        return {
            "policyArn": self.arn,
            "policyDocument": self.document,
            "policyVersionId": self.version_id,
            "isDefaultVersion": self.is_default,
        }

    def to_dict(self):
        return {
            "versionId": self.version_id,
            "isDefaultVersion": self.is_default,
            "createDate": self.create_datetime,
        }


class FakeJob(BaseModel):
    JOB_ID_REGEX_PATTERN = "[a-zA-Z0-9_-]"
    JOB_ID_REGEX = re.compile(JOB_ID_REGEX_PATTERN)

    def __init__(
        self,
        job_id,
        targets,
        document_source,
        document,
        description,
        presigned_url_config,
        target_selection,
        job_executions_rollout_config,
        document_parameters,
        region_name,
    ):
        if not self._job_id_matcher(self.JOB_ID_REGEX, job_id):
            raise InvalidRequestException()

        self.region_name = region_name
        self.job_id = job_id
        self.job_arn = "arn:aws:iot:%s:1:job/%s" % (self.region_name, job_id)
        self.targets = targets
        self.document_source = document_source
        self.document = document
        self.force = False
        self.description = description
        self.presigned_url_config = presigned_url_config
        self.target_selection = target_selection
        self.job_executions_rollout_config = job_executions_rollout_config
        self.status = "QUEUED"  # IN_PROGRESS | CANCELED | COMPLETED
        self.comment = None
        self.reason_code = None
        self.created_at = time.mktime(datetime(2015, 1, 1).timetuple())
        self.last_updated_at = time.mktime(datetime(2015, 1, 1).timetuple())
        self.completed_at = None
        self.job_process_details = {
            "processingTargets": targets,
            "numberOfQueuedThings": 1,
            "numberOfCanceledThings": 0,
            "numberOfSucceededThings": 0,
            "numberOfFailedThings": 0,
            "numberOfRejectedThings": 0,
            "numberOfInProgressThings": 0,
            "numberOfRemovedThings": 0,
        }
        self.document_parameters = document_parameters

    def to_dict(self):
        obj = {
            "jobArn": self.job_arn,
            "jobId": self.job_id,
            "targets": self.targets,
            "description": self.description,
            "presignedUrlConfig": self.presigned_url_config,
            "targetSelection": self.target_selection,
            "jobExecutionsRolloutConfig": self.job_executions_rollout_config,
            "status": self.status,
            "comment": self.comment,
            "forceCanceled": self.force,
            "reasonCode": self.reason_code,
            "createdAt": self.created_at,
            "lastUpdatedAt": self.last_updated_at,
            "completedAt": self.completed_at,
            "jobProcessDetails": self.job_process_details,
            "documentParameters": self.document_parameters,
            "document": self.document,
            "documentSource": self.document_source,
        }

        return obj

    def _job_id_matcher(self, regex, argument):
        regex_match = regex.match(argument)
        length_match = len(argument) <= 64
        return regex_match and length_match


class FakeJobExecution(BaseModel):
    def __init__(
        self,
        job_id,
        thing_arn,
        status="QUEUED",
        force_canceled=False,
        status_details_map={},
    ):
        self.job_id = job_id
        self.status = status  # IN_PROGRESS | CANCELED | COMPLETED
        self.force_canceled = force_canceled
        self.status_details_map = status_details_map
        self.thing_arn = thing_arn
        self.queued_at = time.mktime(datetime(2015, 1, 1).timetuple())
        self.started_at = time.mktime(datetime(2015, 1, 1).timetuple())
        self.last_updated_at = time.mktime(datetime(2015, 1, 1).timetuple())
        self.execution_number = 123
        self.version_number = 123
        self.approximate_seconds_before_time_out = 123

    def to_get_dict(self):
        obj = {
            "jobId": self.job_id,
            "status": self.status,
            "forceCanceled": self.force_canceled,
            "statusDetails": {"detailsMap": self.status_details_map},
            "thingArn": self.thing_arn,
            "queuedAt": self.queued_at,
            "startedAt": self.started_at,
            "lastUpdatedAt": self.last_updated_at,
            "executionNumber": self.execution_number,
            "versionNumber": self.version_number,
            "approximateSecondsBeforeTimedOut": self.approximate_seconds_before_time_out,
        }

        return obj

    def to_dict(self):
        obj = {
            "jobId": self.job_id,
            "thingArn": self.thing_arn,
            "jobExecutionSummary": {
                "status": self.status,
                "queuedAt": self.queued_at,
                "startedAt": self.started_at,
                "lastUpdatedAt": self.last_updated_at,
                "executionNumber": self.execution_number,
            },
        }

        return obj


class FakeEndpoint(BaseModel):
    def __init__(self, endpoint_type, region_name):
        if endpoint_type not in [
            "iot:Data",
            "iot:Data-ATS",
            "iot:CredentialProvider",
            "iot:Jobs",
        ]:
            raise InvalidRequestException(
                " An error occurred (InvalidRequestException) when calling the DescribeEndpoint "
                "operation: Endpoint type %s not recognized." % endpoint_type
            )
        self.region_name = region_name
        data_identifier = random_string(14)
        if endpoint_type == "iot:Data":
            self.endpoint = "{i}.iot.{r}.amazonaws.com".format(
                i=data_identifier, r=self.region_name
            )
        elif "iot:Data-ATS" in endpoint_type:
            self.endpoint = "{i}-ats.iot.{r}.amazonaws.com".format(
                i=data_identifier, r=self.region_name
            )
        elif "iot:CredentialProvider" in endpoint_type:
            identifier = random_string(14)
            self.endpoint = "{i}.credentials.iot.{r}.amazonaws.com".format(
                i=identifier, r=self.region_name
            )
        elif "iot:Jobs" in endpoint_type:
            identifier = random_string(14)
            self.endpoint = "{i}.jobs.iot.{r}.amazonaws.com".format(
                i=identifier, r=self.region_name
            )
        self.endpoint_type = endpoint_type

    def to_get_dict(self):
        obj = {
            "endpointAddress": self.endpoint,
        }

        return obj

    def to_dict(self):
        obj = {
            "endpointAddress": self.endpoint,
        }

        return obj


class FakeRule(BaseModel):
    def __init__(
        self,
        rule_name,
        description,
        created_at,
        rule_disabled,
        topic_pattern,
        actions,
        error_action,
        sql,
        aws_iot_sql_version,
        region_name,
    ):
        self.region_name = region_name
        self.rule_name = rule_name
        self.description = description or ""
        self.created_at = created_at
        self.rule_disabled = bool(rule_disabled)
        self.topic_pattern = topic_pattern
        self.actions = actions or []
        self.error_action = error_action or {}
        self.sql = sql
        self.aws_iot_sql_version = aws_iot_sql_version or "2016-03-23"
        self.arn = "arn:aws:iot:%s:1:rule/%s" % (self.region_name, rule_name)

    def to_get_dict(self):
        return {
            "rule": {
                "actions": self.actions,
                "awsIotSqlVersion": self.aws_iot_sql_version,
                "createdAt": self.created_at,
                "description": self.description,
                "errorAction": self.error_action,
                "ruleDisabled": self.rule_disabled,
                "ruleName": self.rule_name,
                "sql": self.sql,
            },
            "ruleArn": self.arn,
        }

    def to_dict(self):
        return {
            "ruleName": self.rule_name,
            "createdAt": self.created_at,
            "ruleArn": self.arn,
            "ruleDisabled": self.rule_disabled,
            "topicPattern": self.topic_pattern,
        }


class IoTBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(IoTBackend, self).__init__()
        self.region_name = region_name
        self.things = OrderedDict()
        self.jobs = OrderedDict()
        self.job_executions = OrderedDict()
        self.thing_types = OrderedDict()
        self.thing_groups = OrderedDict()
        self.certificates = OrderedDict()
        self.policies = OrderedDict()
        self.principal_policies = OrderedDict()
        self.principal_things = OrderedDict()
        self.rules = OrderedDict()
        self.endpoint = None

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_thing(self, thing_name, thing_type_name, attribute_payload):
        thing_types = self.list_thing_types()
        thing_type = None
        if thing_type_name:
            filtered_thing_types = [
                _ for _ in thing_types if _.thing_type_name == thing_type_name
            ]
            if len(filtered_thing_types) == 0:
                raise ResourceNotFoundException()
            thing_type = filtered_thing_types[0]
        if attribute_payload is None:
            attributes = {}
        elif "attributes" not in attribute_payload:
            attributes = {}
        else:
            attributes = attribute_payload["attributes"]
        thing = FakeThing(thing_name, thing_type, attributes, self.region_name)
        self.things[thing.arn] = thing
        return thing.thing_name, thing.arn

    def create_thing_type(self, thing_type_name, thing_type_properties):
        if thing_type_properties is None:
            thing_type_properties = {}
        thing_type = FakeThingType(
            thing_type_name, thing_type_properties, self.region_name
        )
        self.thing_types[thing_type.arn] = thing_type
        return thing_type.thing_type_name, thing_type.arn

    def list_thing_types(self, thing_type_name=None):
        if thing_type_name:
            # It's weird but thing_type_name is filtered by forward match, not complete match
            return [
                _
                for _ in self.thing_types.values()
                if _.thing_type_name.startswith(thing_type_name)
            ]
        return self.thing_types.values()

    def list_things(
        self, attribute_name, attribute_value, thing_type_name, max_results, token
    ):
        all_things = [_.to_dict() for _ in self.things.values()]
        if attribute_name is not None and thing_type_name is not None:
            filtered_things = list(
                filter(
                    lambda elem: attribute_name in elem["attributes"]
                    and elem["attributes"][attribute_name] == attribute_value
                    and "thingTypeName" in elem
                    and elem["thingTypeName"] == thing_type_name,
                    all_things,
                )
            )
        elif attribute_name is not None and thing_type_name is None:
            filtered_things = list(
                filter(
                    lambda elem: attribute_name in elem["attributes"]
                    and elem["attributes"][attribute_name] == attribute_value,
                    all_things,
                )
            )
        elif attribute_name is None and thing_type_name is not None:
            filtered_things = list(
                filter(
                    lambda elem: "thingTypeName" in elem
                    and elem["thingTypeName"] == thing_type_name,
                    all_things,
                )
            )
        else:
            filtered_things = all_things

        if token is None:
            things = filtered_things[0:max_results]
            next_token = (
                str(max_results) if len(filtered_things) > max_results else None
            )
        else:
            token = int(token)
            things = filtered_things[token : token + max_results]
            next_token = (
                str(token + max_results)
                if len(filtered_things) > token + max_results
                else None
            )

        return things, next_token

    def describe_thing(self, thing_name):
        things = [_ for _ in self.things.values() if _.thing_name == thing_name]
        if len(things) == 0:
            raise ResourceNotFoundException()
        return things[0]

    def describe_thing_type(self, thing_type_name):
        thing_types = [
            _ for _ in self.thing_types.values() if _.thing_type_name == thing_type_name
        ]
        if len(thing_types) == 0:
            raise ResourceNotFoundException()
        return thing_types[0]

    def describe_endpoint(self, endpoint_type):
        self.endpoint = FakeEndpoint(endpoint_type, self.region_name)
        return self.endpoint

    def delete_thing(self, thing_name, expected_version):
        # TODO: handle expected_version

        # can raise ResourceNotFoundError
        thing = self.describe_thing(thing_name)

        # detach all principals
        for k in list(self.principal_things.keys()):
            if k[1] == thing_name:
                del self.principal_things[k]

        del self.things[thing.arn]

    def delete_thing_type(self, thing_type_name):
        # can raise ResourceNotFoundError
        thing_type = self.describe_thing_type(thing_type_name)
        del self.thing_types[thing_type.arn]

    def update_thing(
        self,
        thing_name,
        thing_type_name,
        attribute_payload,
        expected_version,
        remove_thing_type,
    ):
        # if attributes payload = {}, nothing
        thing = self.describe_thing(thing_name)
        thing_type = None

        if remove_thing_type and thing_type_name:
            raise InvalidRequestException()

        # thing_type
        if thing_type_name:
            thing_types = self.list_thing_types()
            filtered_thing_types = [
                _ for _ in thing_types if _.thing_type_name == thing_type_name
            ]
            if len(filtered_thing_types) == 0:
                raise ResourceNotFoundException()
            thing_type = filtered_thing_types[0]
            thing.thing_type = thing_type

        if remove_thing_type:
            thing.thing_type = None

        # attribute
        if attribute_payload is not None and "attributes" in attribute_payload:
            do_merge = attribute_payload.get("merge", False)
            attributes = attribute_payload["attributes"]
            if not do_merge:
                thing.attributes = attributes
            else:
                thing.attributes.update(attributes)

    def _random_string(self):
        n = 20
        random_str = "".join(
            [random.choice(string.ascii_letters + string.digits) for i in range(n)]
        )
        return random_str

    def create_keys_and_certificate(self, set_as_active):
        # implement here
        # caCertificate can be blank
        key_pair = {
            "PublicKey": self._random_string(),
            "PrivateKey": self._random_string(),
        }
        certificate_pem = self._random_string()
        status = "ACTIVE" if set_as_active else "INACTIVE"
        certificate = FakeCertificate(certificate_pem, status, self.region_name)
        self.certificates[certificate.certificate_id] = certificate
        return certificate, key_pair

    def delete_certificate(self, certificate_id):
        cert = self.describe_certificate(certificate_id)
        if cert.status == "ACTIVE":
            raise CertificateStateException(
                "Certificate must be deactivated (not ACTIVE) before deletion.",
                certificate_id,
            )

        certs = [
            k[0]
            for k, v in self.principal_things.items()
            if self._get_principal(k[0]).certificate_id == certificate_id
        ]
        if len(certs) > 0:
            raise DeleteConflictException(
                "Things must be detached before deletion (arn: %s)" % certs[0]
            )

        certs = [
            k[0]
            for k, v in self.principal_policies.items()
            if self._get_principal(k[0]).certificate_id == certificate_id
        ]
        if len(certs) > 0:
            raise DeleteConflictException(
                "Certificate policies must be detached before deletion (arn: %s)"
                % certs[0]
            )

        del self.certificates[certificate_id]

    def describe_certificate(self, certificate_id):
        certs = [
            _ for _ in self.certificates.values() if _.certificate_id == certificate_id
        ]
        if len(certs) == 0:
            raise ResourceNotFoundException()
        return certs[0]

    def list_certificates(self):
        return self.certificates.values()

    def __raise_if_certificate_already_exists(self, certificate_id):
        if certificate_id in self.certificates:
            raise ResourceAlreadyExistsException(
                "The certificate is already provisioned or registered"
            )

    def register_certificate(
        self, certificate_pem, ca_certificate_pem, set_as_active, status
    ):
        certificate = FakeCertificate(
            certificate_pem,
            "ACTIVE" if set_as_active else status,
            self.region_name,
            ca_certificate_pem,
        )
        self.__raise_if_certificate_already_exists(certificate.certificate_id)

        self.certificates[certificate.certificate_id] = certificate
        return certificate

    def register_certificate_without_ca(self, certificate_pem, status):
        certificate = FakeCertificate(certificate_pem, status, self.region_name)
        self.__raise_if_certificate_already_exists(certificate.certificate_id)

        self.certificates[certificate.certificate_id] = certificate
        return certificate

    def update_certificate(self, certificate_id, new_status):
        cert = self.describe_certificate(certificate_id)
        # TODO: validate new_status
        cert.status = new_status

    def create_policy(self, policy_name, policy_document):
        policy = FakePolicy(policy_name, policy_document, self.region_name)
        self.policies[policy.name] = policy
        return policy

    def attach_policy(self, policy_name, target):
        principal = self._get_principal(target)
        policy = self.get_policy(policy_name)
        k = (target, policy_name)
        if k in self.principal_policies:
            return
        self.principal_policies[k] = (principal, policy)

    def detach_policy(self, policy_name, target):
        # this may raises ResourceNotFoundException
        self._get_principal(target)
        self.get_policy(policy_name)

        k = (target, policy_name)
        if k not in self.principal_policies:
            raise ResourceNotFoundException()
        del self.principal_policies[k]

    def list_attached_policies(self, target):
        policies = [v[1] for k, v in self.principal_policies.items() if k[0] == target]
        return policies

    def list_policies(self):
        policies = self.policies.values()
        return policies

    def get_policy(self, policy_name):
        policies = [_ for _ in self.policies.values() if _.name == policy_name]
        if len(policies) == 0:
            raise ResourceNotFoundException()
        return policies[0]

    def delete_policy(self, policy_name):

        policies = [
            k[1] for k, v in self.principal_policies.items() if k[1] == policy_name
        ]
        if len(policies) > 0:
            raise DeleteConflictException(
                "The policy cannot be deleted as the policy is attached to one or more principals (name=%s)"
                % policy_name
            )

        policy = self.get_policy(policy_name)
        del self.policies[policy.name]

    def create_policy_version(self, policy_name, policy_document, set_as_default):
        policy = self.get_policy(policy_name)
        if not policy:
            raise ResourceNotFoundException()
        version = FakePolicyVersion(
            policy_name, policy_document, set_as_default, self.region_name
        )
        policy.versions.append(version)
        version.version_id = "{0}".format(len(policy.versions))
        if set_as_default:
            self.set_default_policy_version(policy_name, version.version_id)
        return version

    def set_default_policy_version(self, policy_name, version_id):
        policy = self.get_policy(policy_name)
        if not policy:
            raise ResourceNotFoundException()
        for version in policy.versions:
            if version.version_id == version_id:
                version.is_default = True
                policy.default_version_id = version.version_id
                policy.document = version.document
            else:
                version.is_default = False

    def get_policy_version(self, policy_name, version_id):
        policy = self.get_policy(policy_name)
        if not policy:
            raise ResourceNotFoundException()
        for version in policy.versions:
            if version.version_id == version_id:
                return version
        raise ResourceNotFoundException()

    def list_policy_versions(self, policy_name):
        policy = self.get_policy(policy_name)
        if not policy:
            raise ResourceNotFoundException()
        return policy.versions

    def delete_policy_version(self, policy_name, version_id):
        policy = self.get_policy(policy_name)
        if not policy:
            raise ResourceNotFoundException()
        if version_id == policy.default_version_id:
            raise InvalidRequestException(
                "Cannot delete the default version of a policy"
            )
        for i, v in enumerate(policy.versions):
            if v.version_id == version_id:
                del policy.versions[i]
                return
        raise ResourceNotFoundException()

    def _get_principal(self, principal_arn):
        """
        raise ResourceNotFoundException
        """
        if ":cert/" in principal_arn:
            certs = [_ for _ in self.certificates.values() if _.arn == principal_arn]
            if len(certs) == 0:
                raise ResourceNotFoundException()
            principal = certs[0]
            return principal
        else:
            # TODO: search for cognito_ids
            pass
        raise ResourceNotFoundException()

    def attach_principal_policy(self, policy_name, principal_arn):
        principal = self._get_principal(principal_arn)
        policy = self.get_policy(policy_name)
        k = (principal_arn, policy_name)
        if k in self.principal_policies:
            return
        self.principal_policies[k] = (principal, policy)

    def detach_principal_policy(self, policy_name, principal_arn):
        # this may raises ResourceNotFoundException
        self._get_principal(principal_arn)
        self.get_policy(policy_name)

        k = (principal_arn, policy_name)
        if k not in self.principal_policies:
            raise ResourceNotFoundException()
        del self.principal_policies[k]

    def list_principal_policies(self, principal_arn):
        policies = [
            v[1] for k, v in self.principal_policies.items() if k[0] == principal_arn
        ]
        return policies

    def list_policy_principals(self, policy_name):
        principals = [
            k[0] for k, v in self.principal_policies.items() if k[1] == policy_name
        ]
        return principals

    def attach_thing_principal(self, thing_name, principal_arn):
        principal = self._get_principal(principal_arn)
        thing = self.describe_thing(thing_name)
        k = (principal_arn, thing_name)
        if k in self.principal_things:
            return
        self.principal_things[k] = (principal, thing)

    def detach_thing_principal(self, thing_name, principal_arn):
        # this may raises ResourceNotFoundException
        self._get_principal(principal_arn)
        self.describe_thing(thing_name)

        k = (principal_arn, thing_name)
        if k not in self.principal_things:
            raise ResourceNotFoundException()
        del self.principal_things[k]

    def list_principal_things(self, principal_arn):
        thing_names = [
            k[0] for k, v in self.principal_things.items() if k[0] == principal_arn
        ]
        return thing_names

    def list_thing_principals(self, thing_name):

        things = [_ for _ in self.things.values() if _.thing_name == thing_name]
        if len(things) == 0:
            raise ResourceNotFoundException(
                "Failed to list principals for thing %s because the thing does not exist in your account"
                % thing_name
            )

        principals = [
            k[0] for k, v in self.principal_things.items() if k[1] == thing_name
        ]
        return principals

    def describe_thing_group(self, thing_group_name):
        thing_groups = [
            _
            for _ in self.thing_groups.values()
            if _.thing_group_name == thing_group_name
        ]
        if len(thing_groups) == 0:
            raise ResourceNotFoundException()
        return thing_groups[0]

    def create_thing_group(
        self, thing_group_name, parent_group_name, thing_group_properties
    ):
        thing_group = FakeThingGroup(
            thing_group_name,
            parent_group_name,
            thing_group_properties,
            self.region_name,
            self.thing_groups,
        )
        self.thing_groups[thing_group.arn] = thing_group
        return thing_group.thing_group_name, thing_group.arn, thing_group.thing_group_id

    def delete_thing_group(self, thing_group_name, expected_version):
        child_groups = [
            thing_group
            for _, thing_group in self.thing_groups.items()
            if thing_group.parent_group_name == thing_group_name
        ]
        if len(child_groups) > 0:
            raise InvalidRequestException(
                " Cannot delete thing group : "
                + thing_group_name
                + " when there are still child groups attached to it"
            )
        try:
            thing_group = self.describe_thing_group(thing_group_name)
            del self.thing_groups[thing_group.arn]
        except ResourceNotFoundException:
            # AWS returns success even if the thing group does not exist.
            pass

    def list_thing_groups(self, parent_group, name_prefix_filter, recursive):
        if recursive is None:
            recursive = True
        if name_prefix_filter is None:
            name_prefix_filter = ""
        if parent_group and parent_group not in [
            _.thing_group_name for _ in self.thing_groups.values()
        ]:
            raise ResourceNotFoundException()
        thing_groups = [
            _ for _ in self.thing_groups.values() if _.parent_group_name == parent_group
        ]
        if recursive:
            for g in thing_groups:
                thing_groups.extend(
                    self.list_thing_groups(
                        parent_group=g.thing_group_name,
                        name_prefix_filter=None,
                        recursive=False,
                    )
                )
        # thing_groups = groups_to_process.values()
        return [
            _ for _ in thing_groups if _.thing_group_name.startswith(name_prefix_filter)
        ]

    def update_thing_group(
        self, thing_group_name, thing_group_properties, expected_version
    ):
        thing_group = self.describe_thing_group(thing_group_name)
        if expected_version and expected_version != thing_group.version:
            raise VersionConflictException(thing_group_name)
        attribute_payload = thing_group_properties.get("attributePayload", None)
        if attribute_payload is not None and "attributes" in attribute_payload:
            do_merge = attribute_payload.get("merge", False)
            attributes = attribute_payload["attributes"]
            if not do_merge:
                thing_group.thing_group_properties["attributePayload"][
                    "attributes"
                ] = attributes
            else:
                thing_group.thing_group_properties["attributePayload"][
                    "attributes"
                ].update(attributes)
        elif attribute_payload is not None and "attributes" not in attribute_payload:
            thing_group.attributes = {}
        thing_group.version = thing_group.version + 1
        return thing_group.version

    def _identify_thing_group(self, thing_group_name, thing_group_arn):
        # identify thing group
        if thing_group_name is None and thing_group_arn is None:
            raise InvalidRequestException(
                " Both thingGroupArn and thingGroupName are empty. Need to specify at least one of them"
            )
        if thing_group_name is not None:
            thing_group = self.describe_thing_group(thing_group_name)
            if thing_group_arn and thing_group.arn != thing_group_arn:
                raise InvalidRequestException(
                    "ThingGroupName thingGroupArn does not match specified thingGroupName in request"
                )
        elif thing_group_arn is not None:
            if thing_group_arn not in self.thing_groups:
                raise InvalidRequestException()
            thing_group = self.thing_groups[thing_group_arn]
        return thing_group

    def _identify_thing(self, thing_name, thing_arn):
        # identify thing
        if thing_name is None and thing_arn is None:
            raise InvalidRequestException(
                "Both thingArn and thingName are empty. Need to specify at least one of them"
            )
        if thing_name is not None:
            thing = self.describe_thing(thing_name)
            if thing_arn and thing.arn != thing_arn:
                raise InvalidRequestException(
                    "ThingName thingArn does not match specified thingName in request"
                )
        elif thing_arn is not None:
            if thing_arn not in self.things:
                raise InvalidRequestException()
            thing = self.things[thing_arn]
        return thing

    def add_thing_to_thing_group(
        self, thing_group_name, thing_group_arn, thing_name, thing_arn
    ):
        thing_group = self._identify_thing_group(thing_group_name, thing_group_arn)
        thing = self._identify_thing(thing_name, thing_arn)
        if thing.arn in thing_group.things:
            # aws ignores duplicate registration
            return
        thing_group.things[thing.arn] = thing

    def remove_thing_from_thing_group(
        self, thing_group_name, thing_group_arn, thing_name, thing_arn
    ):
        thing_group = self._identify_thing_group(thing_group_name, thing_group_arn)
        thing = self._identify_thing(thing_name, thing_arn)
        if thing.arn not in thing_group.things:
            # aws ignores non-registered thing
            return
        del thing_group.things[thing.arn]

    def list_things_in_thing_group(self, thing_group_name, recursive):
        thing_group = self.describe_thing_group(thing_group_name)
        return thing_group.things.values()

    def list_thing_groups_for_thing(self, thing_name):
        thing = self.describe_thing(thing_name)
        all_thing_groups = self.list_thing_groups(None, None, None)
        ret = []
        for thing_group in all_thing_groups:
            if thing.arn in thing_group.things:
                ret.append(
                    {
                        "groupName": thing_group.thing_group_name,
                        "groupArn": thing_group.arn,
                    }
                )
        return ret

    def update_thing_groups_for_thing(
        self, thing_name, thing_groups_to_add, thing_groups_to_remove
    ):
        thing = self.describe_thing(thing_name)
        for thing_group_name in thing_groups_to_add:
            thing_group = self.describe_thing_group(thing_group_name)
            self.add_thing_to_thing_group(
                thing_group.thing_group_name, None, thing.thing_name, None
            )
        for thing_group_name in thing_groups_to_remove:
            thing_group = self.describe_thing_group(thing_group_name)
            self.remove_thing_from_thing_group(
                thing_group.thing_group_name, None, thing.thing_name, None
            )

    def create_job(
        self,
        job_id,
        targets,
        document_source,
        document,
        description,
        presigned_url_config,
        target_selection,
        job_executions_rollout_config,
        document_parameters,
    ):
        job = FakeJob(
            job_id,
            targets,
            document_source,
            document,
            description,
            presigned_url_config,
            target_selection,
            job_executions_rollout_config,
            document_parameters,
            self.region_name,
        )
        self.jobs[job_id] = job

        for thing_arn in targets:
            thing_name = thing_arn.split(":")[-1].split("/")[-1]
            job_execution = FakeJobExecution(job_id, thing_arn)
            self.job_executions[(job_id, thing_name)] = job_execution
        return job.job_arn, job_id, description

    def describe_job(self, job_id):
        jobs = [_ for _ in self.jobs.values() if _.job_id == job_id]
        if len(jobs) == 0:
            raise ResourceNotFoundException()
        return jobs[0]

    def delete_job(self, job_id, force):
        job = self.jobs[job_id]

        if job.status == "IN_PROGRESS" and force:
            del self.jobs[job_id]
        elif job.status != "IN_PROGRESS":
            del self.jobs[job_id]
        else:
            raise InvalidStateTransitionException()

    def cancel_job(self, job_id, reason_code, comment, force):
        job = self.jobs[job_id]

        job.reason_code = reason_code if reason_code is not None else job.reason_code
        job.comment = comment if comment is not None else job.comment
        job.force = force if force is not None and force != job.force else job.force
        job.status = "CANCELED"

        if job.status == "IN_PROGRESS" and force:
            self.jobs[job_id] = job
        elif job.status != "IN_PROGRESS":
            self.jobs[job_id] = job
        else:
            raise InvalidStateTransitionException()

        return job

    def get_job_document(self, job_id):
        return self.jobs[job_id]

    def list_jobs(
        self,
        status,
        target_selection,
        max_results,
        token,
        thing_group_name,
        thing_group_id,
    ):
        # TODO: implement filters
        all_jobs = [_.to_dict() for _ in self.jobs.values()]
        filtered_jobs = all_jobs

        if token is None:
            jobs = filtered_jobs[0:max_results]
            next_token = str(max_results) if len(filtered_jobs) > max_results else None
        else:
            token = int(token)
            jobs = filtered_jobs[token : token + max_results]
            next_token = (
                str(token + max_results)
                if len(filtered_jobs) > token + max_results
                else None
            )

        return jobs, next_token

    def describe_job_execution(self, job_id, thing_name, execution_number):
        try:
            job_execution = self.job_executions[(job_id, thing_name)]
        except KeyError:
            raise ResourceNotFoundException()

        if job_execution is None or (
            execution_number is not None
            and job_execution.execution_number != execution_number
        ):
            raise ResourceNotFoundException()

        return job_execution

    def cancel_job_execution(
        self, job_id, thing_name, force, expected_version, status_details
    ):
        job_execution = self.job_executions[(job_id, thing_name)]

        if job_execution is None:
            raise ResourceNotFoundException()

        job_execution.force_canceled = (
            force if force is not None else job_execution.force_canceled
        )
        # TODO: implement expected_version and status_details (at most 10 can be specified)

        if job_execution.status == "IN_PROGRESS" and force:
            job_execution.status = "CANCELED"
            self.job_executions[(job_id, thing_name)] = job_execution
        elif job_execution.status != "IN_PROGRESS":
            job_execution.status = "CANCELED"
            self.job_executions[(job_id, thing_name)] = job_execution
        else:
            raise InvalidStateTransitionException()

    def delete_job_execution(self, job_id, thing_name, execution_number, force):
        job_execution = self.job_executions[(job_id, thing_name)]

        if job_execution.execution_number != execution_number:
            raise ResourceNotFoundException()

        if job_execution.status == "IN_PROGRESS" and force:
            del self.job_executions[(job_id, thing_name)]
        elif job_execution.status != "IN_PROGRESS":
            del self.job_executions[(job_id, thing_name)]
        else:
            raise InvalidStateTransitionException()

    def list_job_executions_for_job(self, job_id, status, max_results, next_token):
        job_executions = [
            self.job_executions[je].to_dict()
            for je in self.job_executions
            if je[0] == job_id
        ]

        if status is not None:
            job_executions = list(
                filter(
                    lambda elem: status in elem["status"] and elem["status"] == status,
                    job_executions,
                )
            )

        token = next_token
        if token is None:
            job_executions = job_executions[0:max_results]
            next_token = str(max_results) if len(job_executions) > max_results else None
        else:
            token = int(token)
            job_executions = job_executions[token : token + max_results]
            next_token = (
                str(token + max_results)
                if len(job_executions) > token + max_results
                else None
            )

        return job_executions, next_token

    def list_job_executions_for_thing(
        self, thing_name, status, max_results, next_token
    ):
        job_executions = [
            self.job_executions[je].to_dict()
            for je in self.job_executions
            if je[1] == thing_name
        ]

        if status is not None:
            job_executions = list(
                filter(
                    lambda elem: status in elem["status"] and elem["status"] == status,
                    job_executions,
                )
            )

        token = next_token
        if token is None:
            job_executions = job_executions[0:max_results]
            next_token = str(max_results) if len(job_executions) > max_results else None
        else:
            token = int(token)
            job_executions = job_executions[token : token + max_results]
            next_token = (
                str(token + max_results)
                if len(job_executions) > token + max_results
                else None
            )

        return job_executions, next_token

    def list_topic_rules(self):
        return [r.to_dict() for r in self.rules.values()]

    def get_topic_rule(self, rule_name):
        if rule_name not in self.rules:
            raise ResourceNotFoundException()
        return self.rules[rule_name].to_get_dict()

    def create_topic_rule(self, rule_name, sql, **kwargs):
        if rule_name in self.rules:
            raise ResourceAlreadyExistsException("Rule with given name already exists")
        result = re.search(r"FROM\s+([^\s]*)", sql)
        topic = result.group(1).strip("'") if result else None
        self.rules[rule_name] = FakeRule(
            rule_name=rule_name,
            created_at=int(time.time()),
            topic_pattern=topic,
            sql=sql,
            region_name=self.region_name,
            **kwargs
        )

    def replace_topic_rule(self, rule_name, **kwargs):
        self.delete_topic_rule(rule_name)
        self.create_topic_rule(rule_name, **kwargs)

    def delete_topic_rule(self, rule_name):
        if rule_name not in self.rules:
            raise ResourceNotFoundException()
        del self.rules[rule_name]

    def enable_topic_rule(self, rule_name):
        if rule_name not in self.rules:
            raise ResourceNotFoundException()
        self.rules[rule_name].rule_disabled = False

    def disable_topic_rule(self, rule_name):
        if rule_name not in self.rules:
            raise ResourceNotFoundException()
        self.rules[rule_name].rule_disabled = True


iot_backends = {}
for region in Session().get_available_regions("iot"):
    iot_backends[region] = IoTBackend(region)
for region in Session().get_available_regions("iot", partition_name="aws-us-gov"):
    iot_backends[region] = IoTBackend(region)
for region in Session().get_available_regions("iot", partition_name="aws-cn"):
    iot_backends[region] = IoTBackend(region)
