from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse

from .exceptions import (
    InvalidParameterException,
    InvalidRequestException,
    ResourceInUseException,
    ResourceNotFoundException,
)
from .models import eks_backends

DEFAULT_MAX_RESULTS = 100
DEFAULT_NEXT_TOKEN = ""


class EKSResponse(BaseResponse):
    SERVICE_NAME = "eks"

    @property
    def eks_backend(self):
        return eks_backends[self.region]

    def create_cluster(self):
        name = self._get_param("name")
        version = self._get_param("version")
        role_arn = self._get_param("roleArn")
        resources_vpc_config = self._get_param("resourcesVpcConfig")
        kubernetes_network_config = self._get_param("kubernetesNetworkConfig")
        logging = self._get_param("logging")
        client_request_token = self._get_param("clientRequestToken")
        tags = self._get_param("tags")
        encryption_config = self._get_param("encryptionConfig")

        try:
            cluster = self.eks_backend.create_cluster(
                name=name,
                version=version,
                role_arn=role_arn,
                resources_vpc_config=resources_vpc_config,
                kubernetes_network_config=kubernetes_network_config,
                logging=logging,
                client_request_token=client_request_token,
                tags=tags,
                encryption_config=encryption_config,
            )

            return 200, {}, json.dumps({"cluster": dict(cluster)})
        except (
            ResourceInUseException,
            ResourceNotFoundException,
            InvalidParameterException,
        ) as e:
            # Backend will capture this and re-raise it as a ClientError.
            return e.response()

    def create_fargate_profile(self):
        fargate_profile_name = self._get_param("fargateProfileName")
        cluster_name = self._get_param("name")
        pod_execution_role_arn = self._get_param("podExecutionRoleArn")
        subnets = self._get_param("subnets")
        selectors = self._get_param("selectors")
        client_request_token = self._get_param("clientRequestToken")
        tags = self._get_param("tags")

        try:
            fargate_profile = self.eks_backend.create_fargate_profile(
                fargate_profile_name=fargate_profile_name,
                cluster_name=cluster_name,
                pod_execution_role_arn=pod_execution_role_arn,
                subnets=subnets,
                selectors=selectors,
                client_request_token=client_request_token,
                tags=tags,
            )

            return 200, {}, json.dumps({"fargateProfile": dict(fargate_profile)})
        except (
            ResourceNotFoundException,
            ResourceInUseException,
            InvalidParameterException,
            InvalidRequestException,
        ) as e:
            return e.response()

    def create_nodegroup(self):
        cluster_name = self._get_param("name")
        nodegroup_name = self._get_param("nodegroupName")
        scaling_config = self._get_param("scalingConfig")
        disk_size = self._get_int_param("diskSize")
        subnets = self._get_param("subnets")
        instance_types = self._get_param("instanceTypes")
        ami_type = self._get_param("amiType")
        remote_access = self._get_param("remoteAccess")
        node_role = self._get_param("nodeRole")
        labels = self._get_param("labels")
        tags = self._get_param("tags")
        client_request_token = self._get_param("clientRequestToken")
        launch_template = self._get_param("launchTemplate")
        capacity_type = self._get_param("capacityType")
        version = self._get_param("version")
        release_version = self._get_param("releaseVersion")

        try:
            nodegroup = self.eks_backend.create_nodegroup(
                cluster_name=cluster_name,
                nodegroup_name=nodegroup_name,
                scaling_config=scaling_config,
                disk_size=disk_size,
                subnets=subnets,
                instance_types=instance_types,
                ami_type=ami_type,
                remote_access=remote_access,
                node_role=node_role,
                labels=labels,
                tags=tags,
                client_request_token=client_request_token,
                launch_template=launch_template,
                capacity_type=capacity_type,
                version=version,
                release_version=release_version,
            )

            return 200, {}, json.dumps({"nodegroup": dict(nodegroup)})
        except (
            ResourceInUseException,
            ResourceNotFoundException,
            InvalidRequestException,
            InvalidParameterException,
        ) as e:
            return e.response()

    def describe_cluster(self):
        name = self._get_param("name")

        try:
            cluster = self.eks_backend.describe_cluster(name=name)

            return 200, {}, json.dumps({"cluster": dict(cluster)})
        except (ResourceInUseException, ResourceNotFoundException) as e:
            return e.response()

    def describe_fargate_profile(self):
        cluster_name = self._get_param("name")
        fargate_profile_name = self._get_param("fargateProfileName")

        try:
            fargate_profile = self.eks_backend.describe_fargate_profile(
                cluster_name=cluster_name, fargate_profile_name=fargate_profile_name,
            )
            return 200, {}, json.dumps({"fargateProfile": dict(fargate_profile)})
        except (ResourceInUseException, ResourceNotFoundException) as e:
            return e.response()

    def describe_nodegroup(self):
        cluster_name = self._get_param("name")
        nodegroup_name = self._get_param("nodegroupName")

        try:
            nodegroup = self.eks_backend.describe_nodegroup(
                cluster_name=cluster_name, nodegroup_name=nodegroup_name,
            )

            return 200, {}, json.dumps({"nodegroup": dict(nodegroup)})
        except (ResourceInUseException, ResourceNotFoundException) as e:
            return e.response()

    def list_clusters(self):
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)

        clusters, next_token = self.eks_backend.list_clusters(
            max_results=max_results, next_token=next_token,
        )

        return 200, {}, json.dumps(dict(clusters=clusters, nextToken=next_token))

    def list_fargate_profiles(self):
        cluster_name = self._get_param("name")
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)

        fargate_profile_names, next_token = self.eks_backend.list_fargate_profiles(
            cluster_name=cluster_name, max_results=max_results, next_token=next_token,
        )

        return (
            200,
            {},
            json.dumps(
                dict(fargateProfileNames=fargate_profile_names, nextToken=next_token)
            ),
        )

    def list_nodegroups(self):
        cluster_name = self._get_param("name")
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)

        nodegroups, next_token = self.eks_backend.list_nodegroups(
            cluster_name=cluster_name, max_results=max_results, next_token=next_token,
        )

        return (
            200,
            {},
            json.dumps(dict(nodegroups=nodegroups, nextToken=next_token)),
        )

    def delete_cluster(self):
        name = self._get_param("name")

        try:
            cluster = self.eks_backend.delete_cluster(name=name,)

            return 200, {}, json.dumps({"cluster": dict(cluster)})
        except (ResourceInUseException, ResourceNotFoundException) as e:
            return e.response()

    def delete_fargate_profile(self):
        cluster_name = self._get_param("name")
        fargate_profile_name = self._get_param("fargateProfileName")

        try:
            fargate_profile = self.eks_backend.delete_fargate_profile(
                cluster_name=cluster_name, fargate_profile_name=fargate_profile_name,
            )

            return 200, {}, json.dumps({"fargateProfile": dict(fargate_profile)})
        except ResourceNotFoundException as e:
            return e.response()

    def delete_nodegroup(self):
        cluster_name = self._get_param("name")
        nodegroup_name = self._get_param("nodegroupName")

        try:
            nodegroup = self.eks_backend.delete_nodegroup(
                cluster_name=cluster_name, nodegroup_name=nodegroup_name,
            )

            return 200, {}, json.dumps({"nodegroup": dict(nodegroup)})
        except (ResourceInUseException, ResourceNotFoundException) as e:
            return e.response()
