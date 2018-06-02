from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import iot_backends
import json


class IoTResponse(BaseResponse):
    SERVICE_NAME = 'iot'

    @property
    def iot_backend(self):
        return iot_backends[self.region]

    def create_thing(self):
        thing_name = self._get_param("thingName")
        thing_type_name = self._get_param("thingTypeName")
        attribute_payload = self._get_param("attributePayload")
        thing_name, thing_arn = self.iot_backend.create_thing(
            thing_name=thing_name,
            thing_type_name=thing_type_name,
            attribute_payload=attribute_payload,
        )
        return json.dumps(dict(thingName=thing_name, thingArn=thing_arn))

    def create_thing_type(self):
        thing_type_name = self._get_param("thingTypeName")
        thing_type_properties = self._get_param("thingTypeProperties")
        thing_type_name, thing_type_arn = self.iot_backend.create_thing_type(
            thing_type_name=thing_type_name,
            thing_type_properties=thing_type_properties,
        )
        return json.dumps(dict(thingTypeName=thing_type_name, thingTypeArn=thing_type_arn))

    def list_thing_types(self):
        # previous_next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        thing_type_name = self._get_param("thingTypeName")
        thing_types = self.iot_backend.list_thing_types(
            thing_type_name=thing_type_name
        )
        # TODO: implement pagination in the future
        next_token = None
        return json.dumps(dict(thingTypes=[_.to_dict() for _ in thing_types], nextToken=next_token))

    def list_things(self):
        # previous_next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        attribute_name = self._get_param("attributeName")
        attribute_value = self._get_param("attributeValue")
        thing_type_name = self._get_param("thingTypeName")
        things = self.iot_backend.list_things(
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            thing_type_name=thing_type_name,
        )
        # TODO: implement pagination in the future
        next_token = None
        return json.dumps(dict(things=[_.to_dict() for _ in things], nextToken=next_token))

    def describe_thing(self):
        thing_name = self._get_param("thingName")
        thing = self.iot_backend.describe_thing(
            thing_name=thing_name,
        )
        return json.dumps(thing.to_dict(include_default_client_id=True))

    def describe_thing_type(self):
        thing_type_name = self._get_param("thingTypeName")
        thing_type = self.iot_backend.describe_thing_type(
            thing_type_name=thing_type_name,
        )
        return json.dumps(thing_type.to_dict())

    def delete_thing(self):
        thing_name = self._get_param("thingName")
        expected_version = self._get_param("expectedVersion")
        self.iot_backend.delete_thing(
            thing_name=thing_name,
            expected_version=expected_version,
        )
        return json.dumps(dict())

    def delete_thing_type(self):
        thing_type_name = self._get_param("thingTypeName")
        self.iot_backend.delete_thing_type(
            thing_type_name=thing_type_name,
        )
        return json.dumps(dict())

    def update_thing(self):
        thing_name = self._get_param("thingName")
        thing_type_name = self._get_param("thingTypeName")
        attribute_payload = self._get_param("attributePayload")
        expected_version = self._get_param("expectedVersion")
        remove_thing_type = self._get_param("removeThingType")
        self.iot_backend.update_thing(
            thing_name=thing_name,
            thing_type_name=thing_type_name,
            attribute_payload=attribute_payload,
            expected_version=expected_version,
            remove_thing_type=remove_thing_type,
        )
        return json.dumps(dict())

    def create_job(self):
        job_arn, job_id, description = self.iot_backend.create_job(
            job_id=self._get_param("jobId"),
            targets=self._get_param("targets"),
            description=self._get_param("description"),
            document_source=self._get_param("documentSource"),
            document=self._get_param("document"),
            presigned_url_config=self._get_param("presignedUrlConfig"),
            target_selection=self._get_param("targetSelection"),
            job_executions_rollout_config=self._get_param("jobExecutionsRolloutConfig"),
            document_parameters=self._get_param("documentParameters")
        )

        return json.dumps(dict(jobArn=job_arn, jobId=job_id, description=description))

    def describe_job(self):
        job = self.iot_backend.describe_job(job_id=self._get_param("jobId"))
        return json.dumps(dict(
            documentSource=job.document_source,
            job=dict(
                comment=job.comment,
                completedAt=job.completed_at,
                createdAt=job.created_at,
                description=job.description,
                documentParameters=job.document_parameters,
                jobArn=job.job_arn,
                jobExecutionsRolloutConfig=job.job_executions_rollout_config,
                jobId=job.job_id,
                jobProcessDetails=job.job_process_details,
                lastUpdatedAt=job.last_updated_at,
                presignedUrlConfig=job.presigned_url_config,
                status=job.status,
                targets=job.targets,
                targetSelection=job.target_selection
            )))

    def create_keys_and_certificate(self):
        set_as_active = self._get_bool_param("setAsActive")
        cert, key_pair = self.iot_backend.create_keys_and_certificate(
            set_as_active=set_as_active,
        )
        return json.dumps(dict(
            certificateArn=cert.arn,
            certificateId=cert.certificate_id,
            certificatePem=cert.certificate_pem,
            keyPair=key_pair
        ))

    def delete_certificate(self):
        certificate_id = self._get_param("certificateId")
        self.iot_backend.delete_certificate(
            certificate_id=certificate_id,
        )
        return json.dumps(dict())

    def describe_certificate(self):
        certificate_id = self._get_param("certificateId")
        certificate = self.iot_backend.describe_certificate(
            certificate_id=certificate_id,
        )
        return json.dumps(dict(certificateDescription=certificate.to_description_dict()))

    def list_certificates(self):
        # page_size = self._get_int_param("pageSize")
        # marker = self._get_param("marker")
        # ascending_order = self._get_param("ascendingOrder")
        certificates = self.iot_backend.list_certificates()
        # TODO: implement pagination in the future
        return json.dumps(dict(certificates=[_.to_dict() for _ in certificates]))

    def update_certificate(self):
        certificate_id = self._get_param("certificateId")
        new_status = self._get_param("newStatus")
        self.iot_backend.update_certificate(
            certificate_id=certificate_id,
            new_status=new_status,
        )
        return json.dumps(dict())

    def create_policy(self):
        policy_name = self._get_param("policyName")
        policy_document = self._get_param("policyDocument")
        policy = self.iot_backend.create_policy(
            policy_name=policy_name,
            policy_document=policy_document,
        )
        return json.dumps(policy.to_dict_at_creation())

    def list_policies(self):
        # marker = self._get_param("marker")
        # page_size = self._get_int_param("pageSize")
        # ascending_order = self._get_param("ascendingOrder")
        policies = self.iot_backend.list_policies()

        # TODO: implement pagination in the future
        return json.dumps(dict(policies=[_.to_dict() for _ in policies]))

    def get_policy(self):
        policy_name = self._get_param("policyName")
        policy = self.iot_backend.get_policy(
            policy_name=policy_name,
        )
        return json.dumps(policy.to_get_dict())

    def delete_policy(self):
        policy_name = self._get_param("policyName")
        self.iot_backend.delete_policy(
            policy_name=policy_name,
        )
        return json.dumps(dict())

    def attach_principal_policy(self):
        policy_name = self._get_param("policyName")
        principal = self.headers.get('x-amzn-iot-principal')
        self.iot_backend.attach_principal_policy(
            policy_name=policy_name,
            principal_arn=principal,
        )
        return json.dumps(dict())

    def detach_principal_policy(self):
        policy_name = self._get_param("policyName")
        principal = self.headers.get('x-amzn-iot-principal')
        self.iot_backend.detach_principal_policy(
            policy_name=policy_name,
            principal_arn=principal,
        )
        return json.dumps(dict())

    def list_principal_policies(self):
        principal = self.headers.get('x-amzn-iot-principal')
        # marker = self._get_param("marker")
        # page_size = self._get_int_param("pageSize")
        # ascending_order = self._get_param("ascendingOrder")
        policies = self.iot_backend.list_principal_policies(
            principal_arn=principal
        )
        # TODO: implement pagination in the future
        next_marker = None
        return json.dumps(dict(policies=[_.to_dict() for _ in policies], nextMarker=next_marker))

    def list_policy_principals(self):
        policy_name = self.headers.get('x-amzn-iot-policy')
        # marker = self._get_param("marker")
        # page_size = self._get_int_param("pageSize")
        # ascending_order = self._get_param("ascendingOrder")
        principals = self.iot_backend.list_policy_principals(
            policy_name=policy_name,
        )
        # TODO: implement pagination in the future
        next_marker = None
        return json.dumps(dict(principals=principals, nextMarker=next_marker))

    def attach_thing_principal(self):
        thing_name = self._get_param("thingName")
        principal = self.headers.get('x-amzn-principal')
        self.iot_backend.attach_thing_principal(
            thing_name=thing_name,
            principal_arn=principal,
        )
        return json.dumps(dict())

    def detach_thing_principal(self):
        thing_name = self._get_param("thingName")
        principal = self.headers.get('x-amzn-principal')
        self.iot_backend.detach_thing_principal(
            thing_name=thing_name,
            principal_arn=principal,
        )
        return json.dumps(dict())

    def list_principal_things(self):
        next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        principal = self.headers.get('x-amzn-principal')
        things = self.iot_backend.list_principal_things(
            principal_arn=principal,
        )
        # TODO: implement pagination in the future
        next_token = None
        return json.dumps(dict(things=things, nextToken=next_token))

    def list_thing_principals(self):
        thing_name = self._get_param("thingName")
        principals = self.iot_backend.list_thing_principals(
            thing_name=thing_name,
        )
        return json.dumps(dict(principals=principals))

    def describe_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        thing_group = self.iot_backend.describe_thing_group(
            thing_group_name=thing_group_name,
        )
        return json.dumps(thing_group.to_dict())

    def create_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        parent_group_name = self._get_param("parentGroupName")
        thing_group_properties = self._get_param("thingGroupProperties")
        thing_group_name, thing_group_arn, thing_group_id = self.iot_backend.create_thing_group(
            thing_group_name=thing_group_name,
            parent_group_name=parent_group_name,
            thing_group_properties=thing_group_properties,
        )
        return json.dumps(dict(
            thingGroupName=thing_group_name,
            thingGroupArn=thing_group_arn,
            thingGroupId=thing_group_id)
        )

    def delete_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        expected_version = self._get_param("expectedVersion")
        self.iot_backend.delete_thing_group(
            thing_group_name=thing_group_name,
            expected_version=expected_version,
        )
        return json.dumps(dict())

    def list_thing_groups(self):
        # next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        parent_group = self._get_param("parentGroup")
        name_prefix_filter = self._get_param("namePrefixFilter")
        recursive = self._get_param("recursive")
        thing_groups = self.iot_backend.list_thing_groups(
            parent_group=parent_group,
            name_prefix_filter=name_prefix_filter,
            recursive=recursive,
        )
        next_token = None
        rets = [{'groupName': _.thing_group_name, 'groupArn': _.arn} for _ in thing_groups]
        # TODO: implement pagination in the future
        return json.dumps(dict(thingGroups=rets, nextToken=next_token))

    def update_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        thing_group_properties = self._get_param("thingGroupProperties")
        expected_version = self._get_param("expectedVersion")
        version = self.iot_backend.update_thing_group(
            thing_group_name=thing_group_name,
            thing_group_properties=thing_group_properties,
            expected_version=expected_version,
        )
        return json.dumps(dict(version=version))

    def add_thing_to_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        thing_group_arn = self._get_param("thingGroupArn")
        thing_name = self._get_param("thingName")
        thing_arn = self._get_param("thingArn")
        self.iot_backend.add_thing_to_thing_group(
            thing_group_name=thing_group_name,
            thing_group_arn=thing_group_arn,
            thing_name=thing_name,
            thing_arn=thing_arn,
        )
        return json.dumps(dict())

    def remove_thing_from_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        thing_group_arn = self._get_param("thingGroupArn")
        thing_name = self._get_param("thingName")
        thing_arn = self._get_param("thingArn")
        self.iot_backend.remove_thing_from_thing_group(
            thing_group_name=thing_group_name,
            thing_group_arn=thing_group_arn,
            thing_name=thing_name,
            thing_arn=thing_arn,
        )
        return json.dumps(dict())

    def list_things_in_thing_group(self):
        thing_group_name = self._get_param("thingGroupName")
        recursive = self._get_param("recursive")
        # next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        things = self.iot_backend.list_things_in_thing_group(
            thing_group_name=thing_group_name,
            recursive=recursive,
        )
        next_token = None
        thing_names = [_.thing_name for _ in things]
        # TODO: implement pagination in the future
        return json.dumps(dict(things=thing_names, nextToken=next_token))

    def list_thing_groups_for_thing(self):
        thing_name = self._get_param("thingName")
        # next_token = self._get_param("nextToken")
        # max_results = self._get_int_param("maxResults")
        thing_groups = self.iot_backend.list_thing_groups_for_thing(
            thing_name=thing_name
        )
        next_token = None
        # TODO: implement pagination in the future
        return json.dumps(dict(thingGroups=thing_groups, nextToken=next_token))

    def update_thing_groups_for_thing(self):
        thing_name = self._get_param("thingName")
        thing_groups_to_add = self._get_param("thingGroupsToAdd") or []
        thing_groups_to_remove = self._get_param("thingGroupsToRemove") or []
        self.iot_backend.update_thing_groups_for_thing(
            thing_name=thing_name,
            thing_groups_to_add=thing_groups_to_add,
            thing_groups_to_remove=thing_groups_to_remove,
        )
        return json.dumps(dict())
