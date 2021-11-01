import json
import threading

from moto import settings
from moto.core.models import CloudFormationModel
from moto.awslambda import lambda_backends
from uuid import uuid4


class CustomModel(CloudFormationModel):
    def __init__(self, region_name, request_id, logical_id, resource_name):
        self.region_name = region_name
        self.request_id = request_id
        self.logical_id = logical_id
        self.resource_name = resource_name
        self.data = dict()
        self._finished = False

    def set_data(self, data):
        self.data = data
        self._finished = True

    def is_created(self):
        return self._finished

    @property
    def physical_resource_id(self):
        return self.resource_name

    @staticmethod
    def cloudformation_type():
        return "?"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        logical_id = kwargs["LogicalId"]
        stack_id = kwargs["StackId"]
        resource_type = kwargs["ResourceType"]
        properties = cloudformation_json["Properties"]
        service_token = properties["ServiceToken"]

        backend = lambda_backends[region_name]
        fn = backend.get_function(service_token)

        request_id = str(uuid4())

        custom_resource = CustomModel(
            region_name, request_id, logical_id, resource_name
        )

        from moto.cloudformation import cloudformation_backends

        stack = cloudformation_backends[region_name].get_stack(stack_id)
        stack.add_custom_resource(custom_resource)

        event = {
            "RequestType": "Create",
            "ServiceToken": service_token,
            # A request will be send to this URL to indicate success/failure
            # This request will be coming from inside a Docker container
            # Note that, in order to reach the Moto host, the Moto-server should be listening on 0.0.0.0
            #
            # Alternative: Maybe we should let the user pass in a container-name where Moto is running?
            # Similar to how we know for sure that the container in our CI is called 'motoserver'
            "ResponseURL": f"{settings.moto_server_host()}/cloudformation_{region_name}/cfnresponse?stack={stack_id}",
            "StackId": stack_id,
            "RequestId": request_id,
            "LogicalResourceId": logical_id,
            "ResourceType": resource_type,
            "ResourceProperties": properties,
        }

        invoke_thread = threading.Thread(
            target=fn.invoke, args=(json.dumps(event), {}, {})
        )
        invoke_thread.start()

        return custom_resource

    @classmethod
    def has_cfn_attr(cls, attribute):
        # We don't know which attributes are supported for third-party resources
        return True

    def get_cfn_attribute(self, attribute_name):
        if attribute_name in self.data:
            return self.data[attribute_name]
        return None
