from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ecs_backends


class EC2ContainerServiceResponse(BaseResponse):
    @property
    def ecs_backend(self):
        """
        ECS Backend

        :return: ECS Backend object
        :rtype: moto.ecs.models.EC2ContainerServiceBackend
        """
        return ecs_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def create_cluster(self):
        cluster_name = self._get_param("clusterName")
        if cluster_name is None:
            cluster_name = "default"
        cluster = self.ecs_backend.create_cluster(cluster_name)
        return json.dumps({"cluster": cluster.response_object})

    def list_clusters(self):
        cluster_arns = self.ecs_backend.list_clusters()
        return json.dumps(
            {
                "clusterArns": cluster_arns
                #  'nextToken': str(uuid.uuid4())
            }
        )

    def describe_clusters(self):
        list_clusters_name = self._get_param("clusters")
        clusters, failures = self.ecs_backend.describe_clusters(list_clusters_name)
        return json.dumps(
            {
                "clusters": clusters,
                "failures": [cluster.response_object for cluster in failures],
            }
        )

    def delete_cluster(self):
        cluster_str = self._get_param("cluster")
        cluster = self.ecs_backend.delete_cluster(cluster_str)
        return json.dumps({"cluster": cluster.response_object})

    def register_task_definition(self):
        family = self._get_param("family")
        container_definitions = self._get_param("containerDefinitions")
        volumes = self._get_param("volumes")
        tags = self._get_param("tags")
        network_mode = self._get_param("networkMode")
        placement_constraints = self._get_param("placementConstraints")
        requires_compatibilities = self._get_param("requiresCompatibilities")
        cpu = self._get_param("cpu")
        memory = self._get_param("memory")
        task_role_arn = self._get_param("taskRoleArn")
        execution_role_arn = self._get_param("executionRoleArn")

        task_definition = self.ecs_backend.register_task_definition(
            family,
            container_definitions,
            volumes=volumes,
            network_mode=network_mode,
            tags=tags,
            placement_constraints=placement_constraints,
            requires_compatibilities=requires_compatibilities,
            cpu=cpu,
            memory=memory,
            task_role_arn=task_role_arn,
            execution_role_arn=execution_role_arn,
        )
        return json.dumps({"taskDefinition": task_definition.response_object})

    def list_task_definitions(self):
        family_prefix = self._get_param("familyPrefix")
        task_definition_arns = self.ecs_backend.list_task_definitions(family_prefix)
        return json.dumps(
            {
                "taskDefinitionArns": task_definition_arns
                #  'nextToken': str(uuid.uuid4())
            }
        )

    def describe_task_definition(self):
        task_definition_str = self._get_param("taskDefinition")
        data = self.ecs_backend.describe_task_definition(task_definition_str)
        resp = {"taskDefinition": data.response_object, "failures": []}
        if "TAGS" in self._get_param("include", []):
            resp["tags"] = self.ecs_backend.list_tags_for_resource(data.arn)
        return json.dumps(resp)

    def deregister_task_definition(self):
        task_definition_str = self._get_param("taskDefinition")
        task_definition = self.ecs_backend.deregister_task_definition(
            task_definition_str
        )
        return json.dumps({"taskDefinition": task_definition.response_object})

    def run_task(self):
        cluster_str = self._get_param("cluster", "default")
        overrides = self._get_param("overrides")
        task_definition_str = self._get_param("taskDefinition")
        count = self._get_int_param("count")
        started_by = self._get_param("startedBy")
        tags = self._get_param("tags")
        tasks = self.ecs_backend.run_task(
            cluster_str, task_definition_str, count, overrides, started_by, tags
        )
        return json.dumps(
            {"tasks": [task.response_object for task in tasks], "failures": []}
        )

    def describe_tasks(self):
        cluster = self._get_param("cluster", "default")
        tasks = self._get_param("tasks")
        data = self.ecs_backend.describe_tasks(cluster, tasks)
        return json.dumps(
            {"tasks": [task.response_object for task in data], "failures": []}
        )

    def start_task(self):
        cluster_str = self._get_param("cluster", "default")
        overrides = self._get_param("overrides")
        task_definition_str = self._get_param("taskDefinition")
        container_instances = self._get_param("containerInstances")
        started_by = self._get_param("startedBy")
        tasks = self.ecs_backend.start_task(
            cluster_str, task_definition_str, container_instances, overrides, started_by
        )
        return json.dumps(
            {"tasks": [task.response_object for task in tasks], "failures": []}
        )

    def list_tasks(self):
        cluster_str = self._get_param("cluster", "default")
        container_instance = self._get_param("containerInstance")
        family = self._get_param("family")
        started_by = self._get_param("startedBy")
        service_name = self._get_param("serviceName")
        desiredStatus = self._get_param("desiredStatus")
        task_arns = self.ecs_backend.list_tasks(
            cluster_str,
            container_instance,
            family,
            started_by,
            service_name,
            desiredStatus,
        )
        return json.dumps({"taskArns": task_arns})

    def stop_task(self):
        cluster_str = self._get_param("cluster", "default")
        task = self._get_param("task")
        reason = self._get_param("reason")
        task = self.ecs_backend.stop_task(cluster_str, task, reason)
        return json.dumps({"task": task.response_object})

    def create_service(self):
        cluster_str = self._get_param("cluster", "default")
        service_name = self._get_param("serviceName")
        task_definition_str = self._get_param("taskDefinition")
        desired_count = self._get_int_param("desiredCount")
        load_balancers = self._get_param("loadBalancers")
        scheduling_strategy = self._get_param("schedulingStrategy")
        tags = self._get_param("tags")
        deployment_controller = self._get_param("deploymentController")
        launch_type = self._get_param("launchType")
        service = self.ecs_backend.create_service(
            cluster_str,
            service_name,
            desired_count,
            task_definition_str,
            load_balancers,
            scheduling_strategy,
            tags,
            deployment_controller,
            launch_type,
        )
        return json.dumps({"service": service.response_object})

    def list_services(self):
        cluster_str = self._get_param("cluster", "default")
        scheduling_strategy = self._get_param("schedulingStrategy")
        service_arns = self.ecs_backend.list_services(cluster_str, scheduling_strategy)
        return json.dumps(
            {
                "serviceArns": service_arns
                # ,
                # 'nextToken': str(uuid.uuid4())
            }
        )

    def describe_services(self):
        cluster_str = self._get_param("cluster", "default")
        service_names = self._get_param("services")
        services, failures = self.ecs_backend.describe_services(
            cluster_str, service_names
        )
        resp = {
            "services": [service.response_object for service in services],
            "failures": failures,
        }
        if "TAGS" in self._get_param("include", []):
            for i, service in enumerate(services):
                resp["services"][i]["tags"] = self.ecs_backend.list_tags_for_resource(
                    service.arn
                )
        return json.dumps(resp)

    def update_service(self):
        cluster_str = self._get_param("cluster", "default")
        service_name = self._get_param("service")
        task_definition = self._get_param("taskDefinition")
        desired_count = self._get_int_param("desiredCount")
        service = self.ecs_backend.update_service(
            cluster_str, service_name, task_definition, desired_count
        )
        return json.dumps({"service": service.response_object})

    def delete_service(self):
        service_name = self._get_param("service")
        cluster_name = self._get_param("cluster", "default")
        force = self._get_param("force", False)
        service = self.ecs_backend.delete_service(cluster_name, service_name, force)
        return json.dumps({"service": service.response_object})

    def register_container_instance(self):
        cluster_str = self._get_param("cluster", "default")
        instance_identity_document_str = self._get_param("instanceIdentityDocument")
        instance_identity_document = json.loads(instance_identity_document_str)
        ec2_instance_id = instance_identity_document["instanceId"]
        container_instance = self.ecs_backend.register_container_instance(
            cluster_str, ec2_instance_id
        )
        return json.dumps({"containerInstance": container_instance.response_object})

    def deregister_container_instance(self):
        cluster_str = self._get_param("cluster", "default")
        container_instance_str = self._get_param("containerInstance")
        force = self._get_param("force")
        container_instance, failures = self.ecs_backend.deregister_container_instance(
            cluster_str, container_instance_str, force
        )
        return json.dumps({"containerInstance": container_instance.response_object})

    def list_container_instances(self):
        cluster_str = self._get_param("cluster", "default")
        container_instance_arns = self.ecs_backend.list_container_instances(cluster_str)
        return json.dumps({"containerInstanceArns": container_instance_arns})

    def describe_container_instances(self):
        cluster_str = self._get_param("cluster", "default")
        list_container_instance_arns = self._get_param("containerInstances")
        container_instances, failures = self.ecs_backend.describe_container_instances(
            cluster_str, list_container_instance_arns
        )
        return json.dumps(
            {
                "failures": [ci.response_object for ci in failures],
                "containerInstances": [
                    ci.response_object for ci in container_instances
                ],
            }
        )

    def update_container_instances_state(self):
        cluster_str = self._get_param("cluster", "default")
        list_container_instance_arns = self._get_param("containerInstances")
        status_str = self._get_param("status")
        (
            container_instances,
            failures,
        ) = self.ecs_backend.update_container_instances_state(
            cluster_str, list_container_instance_arns, status_str
        )
        return json.dumps(
            {
                "failures": [ci.response_object for ci in failures],
                "containerInstances": [
                    ci.response_object for ci in container_instances
                ],
            }
        )

    def put_attributes(self):
        cluster_name = self._get_param("cluster")
        attributes = self._get_param("attributes")

        self.ecs_backend.put_attributes(cluster_name, attributes)

        return json.dumps({"attributes": attributes})

    def list_attributes(self):
        cluster_name = self._get_param("cluster")
        attr_name = self._get_param("attributeName")
        attr_value = self._get_param("attributeValue")
        target_type = self._get_param("targetType")
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")

        results = self.ecs_backend.list_attributes(
            target_type, cluster_name, attr_name, attr_value, max_results, next_token
        )
        # Result will be [item will be {0 cluster_name, 1 arn, 2 name, 3 value}]

        formatted_results = []
        for _, arn, name, value in results:
            tmp_result = {"name": name, "targetId": arn}
            if value is not None:
                tmp_result["value"] = value
            formatted_results.append(tmp_result)

        return json.dumps({"attributes": formatted_results})

    def delete_attributes(self):
        cluster_name = self._get_param("cluster", "default")
        attributes = self._get_param("attributes")

        self.ecs_backend.delete_attributes(cluster_name, attributes)

        return json.dumps({"attributes": attributes})

    def discover_poll_endpoint(self):
        # Here are the arguments, this api is used by the ecs client so obviously no decent
        # documentation. Hence I've responded with valid but useless data
        # cluster_name = self._get_param('cluster')
        # instance = self._get_param('containerInstance')
        return json.dumps(
            {"endpoint": "http://localhost", "telemetryEndpoint": "http://localhost"}
        )

    def list_task_definition_families(self):
        family_prefix = self._get_param("familyPrefix")
        status = self._get_param("status")
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")

        results = self.ecs_backend.list_task_definition_families(
            family_prefix, status, max_results, next_token
        )

        return json.dumps({"families": list(results)})

    def list_tags_for_resource(self):
        resource_arn = self._get_param("resourceArn")
        tags = self.ecs_backend.list_tags_for_resource(resource_arn)
        return json.dumps({"tags": tags})

    def tag_resource(self):
        resource_arn = self._get_param("resourceArn")
        tags = self._get_param("tags")
        results = self.ecs_backend.tag_resource(resource_arn, tags)
        return json.dumps(results)

    def untag_resource(self):
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys")
        results = self.ecs_backend.untag_resource(resource_arn, tag_keys)
        return json.dumps(results)

    def create_task_set(self):
        service_str = self._get_param("service")
        cluster_str = self._get_param("cluster", "default")
        task_definition = self._get_param("taskDefinition")
        external_id = self._get_param("externalId")
        network_configuration = self._get_param("networkConfiguration")
        load_balancers = self._get_param("loadBalancers")
        service_registries = self._get_param("serviceRegistries")
        launch_type = self._get_param("launchType")
        capacity_provider_strategy = self._get_param("capacityProviderStrategy")
        platform_version = self._get_param("platformVersion")
        scale = self._get_param("scale")
        client_token = self._get_param("clientToken")
        tags = self._get_param("tags")
        task_set = self.ecs_backend.create_task_set(
            service_str,
            cluster_str,
            task_definition,
            external_id=external_id,
            network_configuration=network_configuration,
            load_balancers=load_balancers,
            service_registries=service_registries,
            launch_type=launch_type,
            capacity_provider_strategy=capacity_provider_strategy,
            platform_version=platform_version,
            scale=scale,
            client_token=client_token,
            tags=tags,
        )
        return json.dumps({"taskSet": task_set.response_object})

    def describe_task_sets(self):
        cluster_str = self._get_param("cluster", "default")
        service_str = self._get_param("service")
        task_sets = self._get_param("taskSets")
        include = self._get_param("include", [])
        task_set_objs = self.ecs_backend.describe_task_sets(
            cluster_str, service_str, task_sets, include
        )

        response_objs = [t.response_object for t in task_set_objs]
        if "TAGS" not in include:
            for ro in response_objs:
                del ro["tags"]
        return json.dumps({"taskSets": response_objs})

    def delete_task_set(self):
        cluster_str = self._get_param("cluster")
        service_str = self._get_param("service")
        task_set = self._get_param("taskSet")
        force = self._get_param("force")
        task_set = self.ecs_backend.delete_task_set(
            cluster_str, service_str, task_set, force
        )
        return json.dumps({"taskSet": task_set.response_object})

    def update_task_set(self):
        cluster_str = self._get_param("cluster", "default")
        service_str = self._get_param("service")
        task_set = self._get_param("taskSet")
        scale = self._get_param("scale")

        task_set = self.ecs_backend.update_task_set(
            cluster_str, service_str, task_set, scale
        )
        return json.dumps({"taskSet": task_set.response_object})

    def update_service_primary_task_set(self):
        cluster_str = self._get_param("cluster", "default")
        service_str = self._get_param("service")
        primary_task_set = self._get_param("primaryTaskSet")

        task_set = self.ecs_backend.update_service_primary_task_set(
            cluster_str, service_str, primary_task_set
        )
        return json.dumps({"taskSet": task_set.response_object})
