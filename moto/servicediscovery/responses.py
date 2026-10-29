"""Handles incoming servicediscovery requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import ServiceDiscoveryBackend, servicediscovery_backends


class ServiceDiscoveryResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="servicediscovery")
        self.automated_parameter_parsing = True

    @property
    def servicediscovery_backend(self) -> ServiceDiscoveryBackend:
        """Return backend instance specific for this region."""
        return servicediscovery_backends[self.current_account][self.region]

    def list_namespaces(self) -> ActionResult:
        namespaces = self.servicediscovery_backend.list_namespaces()
        result = {
            "Namespaces": [
                {
                    "Id": ns.id,
                    "Arn": ns.arn,
                    "Name": ns.name,
                    "Type": ns.type,
                    "Description": ns.description,
                    "Properties": {
                        "DnsProperties": ns.dns_properties,
                        "HttpProperties": ns.http_properties,
                    },
                    "CreateDate": ns.created,
                }
                for ns in namespaces
            ]
        }
        return ActionResult(result)

    def create_http_namespace(self) -> ActionResult:
        name = self._get_param("Name")
        creator_request_id = self._get_param("CreatorRequestId")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        operation_id = self.servicediscovery_backend.create_http_namespace(
            name=name,
            creator_request_id=creator_request_id,
            description=description,
            tags=tags,
        )
        return ActionResult({"OperationId": operation_id})

    def delete_namespace(self) -> ActionResult:
        namespace_id = self._get_param("Id")
        operation_id = self.servicediscovery_backend.delete_namespace(
            namespace_id=namespace_id
        )
        return ActionResult({"OperationId": operation_id})

    def list_operations(self) -> ActionResult:
        operations = self.servicediscovery_backend.list_operations()
        result = {
            "Operations": [{"Id": op.id, "Status": op.status} for op in operations]
        }
        return ActionResult(result)

    def get_operation(self) -> ActionResult:
        operation_id = self._get_param("OperationId")
        operation = self.servicediscovery_backend.get_operation(
            operation_id=operation_id
        )
        result = {
            "Operation": {
                "Id": operation.id,
                "Status": operation.status,
                "Type": operation.operation_type,
                "CreateDate": operation.created,
                "UpdateDate": operation.updated,
                "Targets": operation.targets,
            }
        }
        return ActionResult(result)

    def get_namespace(self) -> ActionResult:
        namespace_id = self._get_param("Id")
        namespace = self.servicediscovery_backend.get_namespace(
            namespace_id=namespace_id
        )
        result = {
            "Namespace": {
                "Id": namespace.id,
                "Arn": namespace.arn,
                "Name": namespace.name,
                "Type": namespace.type,
                "Description": namespace.description,
                "Properties": {
                    "DnsProperties": namespace.dns_properties,
                    "HttpProperties": namespace.http_properties,
                },
                "CreateDate": namespace.created,
                "CreatorRequestId": namespace.creator_request_id,
            }
        }
        return ActionResult(result)

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tags = self._get_param("Tags")
        self.servicediscovery_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tag_keys = self._get_param("TagKeys")
        self.servicediscovery_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tags = self.servicediscovery_backend.list_tags_for_resource(
            resource_arn=resource_arn
        )
        return ActionResult(tags)

    def create_private_dns_namespace(self) -> ActionResult:
        name = self._get_param("Name")
        creator_request_id = self._get_param("CreatorRequestId")
        description = self._get_param("Description")
        vpc = self._get_param("Vpc")
        tags = self._get_param("Tags")
        properties = self._get_param("Properties")
        operation_id = self.servicediscovery_backend.create_private_dns_namespace(
            name=name,
            creator_request_id=creator_request_id,
            description=description,
            vpc=vpc,
            tags=tags,
            properties=properties,
        )
        return ActionResult({"OperationId": operation_id})

    def create_public_dns_namespace(self) -> ActionResult:
        name = self._get_param("Name")
        creator_request_id = self._get_param("CreatorRequestId")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        properties = self._get_param("Properties")
        operation_id = self.servicediscovery_backend.create_public_dns_namespace(
            name=name,
            creator_request_id=creator_request_id,
            description=description,
            tags=tags,
            properties=properties,
        )
        return ActionResult({"OperationId": operation_id})

    def create_service(self) -> ActionResult:
        name = self._get_param("Name")
        namespace_id = self._get_param("NamespaceId")
        creator_request_id = self._get_param("CreatorRequestId")
        description = self._get_param("Description")
        dns_config = self._get_param("DnsConfig")
        health_check_config = self._get_param("HealthCheckConfig")
        health_check_custom_config = self._get_param("HealthCheckCustomConfig")
        tags = self._get_param("Tags")
        service_type = self._get_param("Type")
        service = self.servicediscovery_backend.create_service(
            name=name,
            namespace_id=namespace_id,
            creator_request_id=creator_request_id,
            description=description,
            dns_config=dns_config,
            health_check_config=health_check_config,
            health_check_custom_config=health_check_custom_config,
            tags=tags,
            service_type=service_type,
        )
        result = {
            "Service": {
                "Id": service.id,
                "Arn": service.arn,
                "Name": service.name,
                "NamespaceId": service.namespace_id,
                "Description": service.description,
                "DnsConfig": service.dns_config,
                "Type": service.service_type,
                "HealthCheckConfig": service.health_check_config,
                "HealthCheckCustomConfig": service.health_check_custom_config,
                "CreateDate": service.created,
                "CreatorRequestId": service.creator_request_id,
            }
        }
        return ActionResult(result)

    def get_service(self) -> ActionResult:
        service_id = self._get_param("Id")
        service = self.servicediscovery_backend.get_service(service_id=service_id)
        result = {
            "Service": {
                "Id": service.id,
                "Arn": service.arn,
                "Name": service.name,
                "NamespaceId": service.namespace_id,
                "Description": service.description,
                "DnsConfig": service.dns_config,
                "Type": service.service_type,
                "HealthCheckConfig": service.health_check_config,
                "HealthCheckCustomConfig": service.health_check_custom_config,
                "CreateDate": service.created,
                "CreatorRequestId": service.creator_request_id,
            }
        }
        return ActionResult(result)

    def delete_service(self) -> ActionResult:
        service_id = self._get_param("Id")
        self.servicediscovery_backend.delete_service(service_id=service_id)
        return EmptyResult()

    def list_services(self) -> ActionResult:
        services = self.servicediscovery_backend.list_services()
        result = {
            "Services": [
                {
                    "Id": service.id,
                    "Arn": service.arn,
                    "Name": service.name,
                    "Type": service.service_type,
                    "Description": service.description,
                    "DnsConfig": service.dns_config,
                    "HealthCheckConfig": service.health_check_config,
                    "HealthCheckCustomConfig": service.health_check_custom_config,
                    "CreateDate": service.created,
                }
                for service in services
            ]
        }
        return ActionResult(result)

    def update_service(self) -> ActionResult:
        service_id = self._get_param("Id")
        details = self._get_param("Service")
        operation_id = self.servicediscovery_backend.update_service(
            service_id=service_id, details=details
        )
        return ActionResult({"OperationId": operation_id})

    def get_service_attributes(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        service = self.servicediscovery_backend.get_service_attributes(
            service_id=service_id
        )
        result = {
            "ServiceAttributes": {
                "ServiceArn": service.arn,
                "ResourceOwner": service.account_id,
                "Attributes": service.attributes,
            }
        }
        return ActionResult(result)

    def update_service_attributes(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        attributes = self._get_param("Attributes")
        self.servicediscovery_backend.update_service_attributes(
            service_id=service_id, attributes=attributes
        )
        return EmptyResult()

    def delete_service_attributes(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        attributes = self._get_param("Attributes")
        self.servicediscovery_backend.delete_service_attributes(
            service_id=service_id, attributes=attributes
        )
        return EmptyResult()

    def update_http_namespace(self) -> ActionResult:
        _id = self._get_param("Id")
        updater_request_id = self._get_param("UpdaterRequestId")
        namespace = self._get_param("Namespace")
        operation_id = self.servicediscovery_backend.update_http_namespace(
            _id=_id,
            updater_request_id=updater_request_id,
            namespace_dict=namespace,
        )
        return ActionResult({"OperationId": operation_id})

    def update_private_dns_namespace(self) -> ActionResult:
        _id = self._get_param("Id")
        namespace = self._get_param("Namespace", {})
        description = namespace.get("Description")
        properties = namespace.get("Properties", {}).get("DnsProperties")
        operation_id = self.servicediscovery_backend.update_private_dns_namespace(
            _id=_id,
            description=description,
            properties=properties,
        )
        return ActionResult({"OperationId": operation_id})

    def update_public_dns_namespace(self) -> ActionResult:
        _id = self._get_param("Id")
        namespace = self._get_param("Namespace", {})
        description = namespace.get("Description")
        properties = namespace.get("Properties", {}).get("DnsProperties")
        operation_id = self.servicediscovery_backend.update_public_dns_namespace(
            _id=_id,
            description=description,
            properties=properties,
        )
        return ActionResult({"OperationId": operation_id})

    def register_instance(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        instance_id = self._get_param("InstanceId")
        creator_request_id = self._get_param("CreatorRequestId")
        attributes = self._get_param("Attributes")
        operation_id = self.servicediscovery_backend.register_instance(
            service_id=service_id,
            instance_id=instance_id,
            creator_request_id=creator_request_id,
            attributes=attributes,
        )
        return ActionResult({"OperationId": operation_id})

    def deregister_instance(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        instance_id = self._get_param("InstanceId")
        operation_id = self.servicediscovery_backend.deregister_instance(
            service_id=service_id,
            instance_id=instance_id,
        )
        return ActionResult({"OperationId": operation_id})

    def get_instance(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        instance_id = self._get_param("InstanceId")
        instance = self.servicediscovery_backend.get_instance(
            service_id=service_id,
            instance_id=instance_id,
        )
        result = {
            "Instance": {
                "Id": instance.instance_id,
                "CreatorRequestId": instance.creator_request_id,
                "Attributes": instance.attributes,
            }
        }
        return ActionResult(result)

    def get_instances_health_status(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        instances = self._get_param("Instances")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        status_records = self.servicediscovery_backend.get_instances_health_status(
            service_id=service_id,
            instances=instances,
        )
        page, new_token = self.servicediscovery_backend.paginate(
            status_records, max_results=max_results, next_token=next_token
        )
        result: dict[str, Any] = {"Status": {}}
        for record in page:
            result["Status"][record[0]] = record[1]
        if new_token:
            result["NextToken"] = new_token
        return ActionResult(result)

    def update_instance_custom_health_status(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        instance_id = self._get_param("InstanceId")
        status = self._get_param("Status")
        self.servicediscovery_backend.update_instance_custom_health_status(
            service_id=service_id,
            instance_id=instance_id,
            status=status,
        )
        return EmptyResult()

    def list_instances(self) -> ActionResult:
        service_id = self._get_param("ServiceId")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        instances = self.servicediscovery_backend.list_instances(service_id=service_id)
        page, new_token = self.servicediscovery_backend.paginate(
            instances, max_results=max_results, next_token=next_token
        )
        result: dict[str, Any] = {"Instances": []}
        for instance in page:
            result["Instances"].append(
                {"Id": instance.instance_id, "Attributes": instance.attributes}
            )
        if new_token:
            result["NextToken"] = new_token
        return ActionResult(result)

    def discover_instances(self) -> ActionResult:
        namespace_name = self._get_param("NamespaceName")
        service_name = self._get_param("ServiceName")
        max_results = self._get_param("MaxResults")
        query_parameters = self._get_param("QueryParameters")
        optional_parameters = self._get_param("OptionalParameters")
        health_status = self._get_param("HealthStatus")
        instances, instances_revision = (
            self.servicediscovery_backend.discover_instances(
                namespace_name=namespace_name,
                service_name=service_name,
                query_parameters=query_parameters,
                optional_parameters=optional_parameters,
                health_status=health_status,
            )
        )
        page, new_token = self.servicediscovery_backend.paginate(
            instances, max_results=max_results
        )
        result_instances: list[dict[str, Any]] = []
        instances_revision_total = 0
        for instance in page:
            result_instances.append(
                {
                    "InstanceId": instance.instance_id,
                    "NamespaceName": namespace_name,
                    "ServiceName": service_name,
                    "Attributes": instance.attributes,
                    "HealthStatus": instance.health_status,
                }
            )
            instances_revision_total += instances_revision[instance.instance_id]
        result = {
            "Instances": result_instances,
            "InstancesRevision": instances_revision_total,
        }
        return ActionResult(result)

    def discover_instances_revision(self) -> ActionResult:
        namespace_name = self._get_param("NamespaceName")
        service_name = self._get_param("ServiceName")
        instances_revision = self.servicediscovery_backend.discover_instances_revision(
            namespace_name=namespace_name,
            service_name=service_name,
        )
        return ActionResult({"InstancesRevision": instances_revision})
