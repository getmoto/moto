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
        previous_next_token = self._get_param("nextToken")
        max_results = self._get_int_param("maxResults")
        thing_type_name = self._get_param("thingTypeName")
        thing_types = self.iot_backend.list_thing_types(
            thing_type_name=thing_type_name
        )

        # TODO: support next_token and max_results
        next_token = None
        return json.dumps(dict(thingTypes=[_.to_json() for _ in thing_types], nextToken=next_token))

    def list_things(self):
        previous_next_token = self._get_param("nextToken")
        max_results = self._get_int_param("maxResults")
        attribute_name = self._get_param("attributeName")
        attribute_value = self._get_param("attributeValue")
        thing_type_name = self._get_param("thingTypeName")
        things = self.iot_backend.list_things(
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            thing_type_name=thing_type_name,
        )
        # TODO: support next_token and max_results
        next_token = None
        return json.dumps(dict(things=[_.to_json() for _ in things], nextToken=next_token))

    def describe_thing(self):
        thing_name = self._get_param("thingName")
        thing = self.iot_backend.describe_thing(
            thing_name=thing_name,
        )
        print(thing.to_json(include_default_client_id=True))
        return json.dumps(thing.to_json(include_default_client_id=True))

    def describe_thing_type(self):
        thing_type_name = self._get_param("thingTypeName")
        thing_type = self.iot_backend.describe_thing_type(
            thing_type_name=thing_type_name,
        )
        return json.dumps(thing_type.to_json())

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

    def create_keys_and_certificate(self):
        set_as_active = self._get_param("setAsActive")
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
        return json.dumps(dict(certificateDescription=certificate.to_description_json()))

    def list_certificates(self):
        page_size = self._get_int_param("pageSize")
        marker = self._get_param("marker")
        ascending_order = self._get_param("ascendingOrder")
        certificates = self.iot_backend.list_certificates()
        # TODO: handle pagination
        return json.dumps(dict(certificates=[_.to_json() for _ in certificates]))

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
        marker = self._get_param("marker")
        page_size = self._get_int_param("pageSize")
        ascending_order = self._get_param("ascendingOrder")
        policies = self.iot_backend.list_policies()

        # TODO: handle pagination
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
