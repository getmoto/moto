from typing import Any, Dict, List, Iterator, Optional, Tuple
from moto.core import BaseBackend, BackendDict
from moto.core.exceptions import RESTError
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService

from moto.s3.models import s3_backends, S3Backend
from moto.ec2 import ec2_backends
from moto.elb.models import elb_backends, ELBBackend
from moto.elbv2.models import elbv2_backends, ELBv2Backend
from moto.glue.models import glue_backends, GlueBackend
from moto.kinesis.models import kinesis_backends, KinesisBackend
from moto.logs.models import logs_backends, LogsBackend
from moto.kms.models import kms_backends, KmsBackend
from moto.rds.models import rds_backends, RDSBackend
from moto.glacier.models import glacier_backends, GlacierBackend
from moto.redshift.models import redshift_backends, RedshiftBackend
from moto.emr.models import emr_backends, ElasticMapReduceBackend
from moto.awslambda.models import lambda_backends, LambdaBackend
from moto.ecs.models import ecs_backends, EC2ContainerServiceBackend

# Left: EC2 ElastiCache RDS ELB CloudFront WorkSpaces Lambda EMR Glacier Kinesis Redshift Route53
# StorageGateway DynamoDB MachineLearning ACM DirectConnect DirectoryService CloudHSM
# Inspector Elasticsearch


class ResourceGroupsTaggingAPIBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)

        self._pages: Dict[str, Any] = {}
        # Like 'someuuid': {'gen': <generator>, 'misc': None}
        # Misc is there for peeking from a generator and it cant
        # fit in the current request. As we only store generators
        # there is really no point cleaning up

    @property
    def s3_backend(self) -> S3Backend:
        return s3_backends[self.account_id]["global"]

    @property
    def ec2_backend(self) -> Any:  # type: ignore[misc]
        return ec2_backends[self.account_id][self.region_name]

    @property
    def elb_backend(self) -> ELBBackend:
        return elb_backends[self.account_id][self.region_name]

    @property
    def elbv2_backend(self) -> ELBv2Backend:
        return elbv2_backends[self.account_id][self.region_name]

    @property
    def glue_backend(self) -> GlueBackend:
        return glue_backends[self.account_id][self.region_name]

    @property
    def kinesis_backend(self) -> KinesisBackend:
        return kinesis_backends[self.account_id][self.region_name]

    @property
    def kms_backend(self) -> KmsBackend:
        return kms_backends[self.account_id][self.region_name]

    @property
    def logs_backend(self) -> LogsBackend:
        return logs_backends[self.account_id][self.region_name]

    @property
    def rds_backend(self) -> RDSBackend:
        return rds_backends[self.account_id][self.region_name]

    @property
    def glacier_backend(self) -> GlacierBackend:
        return glacier_backends[self.account_id][self.region_name]

    @property
    def emr_backend(self) -> ElasticMapReduceBackend:
        return emr_backends[self.account_id][self.region_name]

    @property
    def redshift_backend(self) -> RedshiftBackend:
        return redshift_backends[self.account_id][self.region_name]

    @property
    def lambda_backend(self) -> LambdaBackend:
        return lambda_backends[self.account_id][self.region_name]

    @property
    def ecs_backend(self) -> EC2ContainerServiceBackend:
        return ecs_backends[self.account_id][self.region_name]

    def _get_resources_generator(
        self,
        tag_filters: Optional[List[Dict[str, Any]]] = None,
        resource_type_filters: Optional[List[str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # TODO move these to their respective backends
        filters = []
        for tag_filter_dict in tag_filters:  # type: ignore
            values = tag_filter_dict.get("Values", [])
            if len(values) == 0:
                # Check key matches
                filters.append(lambda t, v, key=tag_filter_dict["Key"]: t == key)
            elif len(values) == 1:
                # Check it's exactly the same as key, value
                filters.append(
                    lambda t, v, key=tag_filter_dict["Key"], value=values[0]: t == key  # type: ignore
                    and v == value
                )
            else:
                # Check key matches and value is one of the provided values
                filters.append(
                    lambda t, v, key=tag_filter_dict["Key"], vl=values: t == key  # type: ignore
                    and v in vl
                )

        def tag_filter(tag_list: List[Dict[str, str]]) -> bool:
            result = []
            if tag_filters:
                for f in filters:
                    temp_result = []
                    for tag in tag_list:
                        f_result = f(tag["Key"], tag["Value"])  # type: ignore
                        temp_result.append(f_result)
                    result.append(any(temp_result))
                return all(result)
            else:
                return True

        def format_tags(tags: Dict[str, str]) -> List[Dict[str, str]]:
            result = []
            for key, value in tags.items():
                result.append({"Key": key, "Value": value})
            return result

        def format_tag_keys(
            tags: List[Dict[str, str]], keys: List[str]
        ) -> List[Dict[str, str]]:
            result = []
            for tag in tags:
                result.append({"Key": tag[keys[0]], "Value": tag[keys[1]]})
            return result

        # S3
        if not resource_type_filters or "s3" in resource_type_filters:
            for bucket in self.s3_backend.buckets.values():
                tags = self.s3_backend.tagger.list_tags_for_resource(bucket.arn)["Tags"]
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {"ResourceARN": "arn:aws:s3:::" + bucket.name, "Tags": tags}

        # CloudFormation
        if not resource_type_filters or "cloudformation:stack" in resource_type_filters:

            try:
                from moto.cloudformation import cloudformation_backends

                backend = cloudformation_backends[self.account_id][self.region_name]

                for stack in backend.stacks.values():
                    tags = format_tags(stack.tags)
                    if not tag_filter(tags):
                        continue
                    yield {"ResourceARN": f"{stack.stack_id}", "Tags": tags}

            except Exception:
                pass

        # ECS
        if not resource_type_filters or "ecs:service" in resource_type_filters:
            for service in self.ecs_backend.services.values():
                tags = format_tag_keys(service.tags, ["key", "value"])
                if not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{service.physical_resource_id}", "Tags": tags}

        if not resource_type_filters or "ecs:cluster" in resource_type_filters:
            for cluster in self.ecs_backend.clusters.values():
                tags = format_tag_keys(cluster.tags, ["key", "value"])  # type: ignore[arg-type]
                if not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{cluster.arn}", "Tags": tags}

        if not resource_type_filters or "ecs:task" in resource_type_filters:
            for task_dict in self.ecs_backend.tasks.values():
                for task in task_dict.values():
                    tags = format_tag_keys(task.tags, ["key", "value"])
                    if not tag_filter(tags):
                        continue
                    yield {"ResourceARN": f"{task.task_arn}", "Tags": tags}

        # EC2 AMI, resource type ec2:image
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:image" in resource_type_filters
        ):
            for ami in self.ec2_backend.amis.values():
                tags = format_tags(self.ec2_backend.tags.get(ami.id, {}))

                if not tags or not tag_filter(tags):
                    # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:aws:ec2:{self.region_name}::image/{ami.id}",
                    "Tags": tags,
                }

        # EC2 Instance, resource type ec2:instance
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:instance" in resource_type_filters
        ):
            for reservation in self.ec2_backend.reservations.values():
                for instance in reservation.instances:
                    tags = format_tags(self.ec2_backend.tags.get(instance.id, {}))

                    if not tags or not tag_filter(tags):
                        # Skip if no tags, or invalid filter
                        continue
                    yield {
                        "ResourceARN": f"arn:aws:ec2:{self.region_name}::instance/{instance.id}",
                        "Tags": tags,
                    }

        # EC2 NetworkInterface, resource type ec2:network-interface
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:network-interface" in resource_type_filters
        ):
            for eni in self.ec2_backend.enis.values():
                tags = format_tags(self.ec2_backend.tags.get(eni.id, {}))

                if not tags or not tag_filter(tags):
                    # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:aws:ec2:{self.region_name}::network-interface/{eni.id}",
                    "Tags": tags,
                }

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:security-group" in resource_type_filters
        ):
            for vpc in self.ec2_backend.groups.values():
                for sg in vpc.values():
                    tags = format_tags(self.ec2_backend.tags.get(sg.id, {}))

                    if not tags or not tag_filter(tags):
                        # Skip if no tags, or invalid filter
                        continue
                    yield {
                        "ResourceARN": f"arn:aws:ec2:{self.region_name}::security-group/{sg.id}",
                        "Tags": tags,
                    }

        # EC2 Snapshot, resource type ec2:snapshot
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:snapshot" in resource_type_filters
        ):
            for snapshot in self.ec2_backend.snapshots.values():
                tags = format_tags(self.ec2_backend.tags.get(snapshot.id, {}))

                if not tags or not tag_filter(tags):
                    # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:aws:ec2:{self.region_name}::snapshot/{snapshot.id}",
                    "Tags": tags,
                }

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:volume" in resource_type_filters
        ):
            for volume in self.ec2_backend.volumes.values():
                tags = format_tags(self.ec2_backend.tags.get(volume.id, {}))

                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:aws:ec2:{self.region_name}::volume/{volume.id}",
                    "Tags": tags,
                }

        # TODO add these to the keys and values functions / combine functions
        # ELB, resource type elasticloadbalancing:loadbalancer
        if (
            not resource_type_filters
            or "elasticloadbalancing" in resource_type_filters
            or "elasticloadbalancing:loadbalancer" in resource_type_filters
        ):
            for elb in self.elbv2_backend.load_balancers.values():
                tags = self.elbv2_backend.tagging_service.list_tags_for_resource(
                    elb.arn
                )["Tags"]
                if not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue

                yield {"ResourceARN": f"{elb.arn}", "Tags": tags}

        # ELB Target Group, resource type elasticloadbalancing:targetgroup
        if (
            not resource_type_filters
            or "elasticloadbalancing" in resource_type_filters
            or "elasticloadbalancing:targetgroup" in resource_type_filters
        ):
            for target_group in self.elbv2_backend.target_groups.values():
                tags = self.elbv2_backend.tagging_service.list_tags_for_resource(
                    target_group.arn
                )["Tags"]
                if not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue

                yield {"ResourceARN": f"{target_group.arn}", "Tags": tags}

        # EMR Cluster

        # Glacier Vault

        # Glue
        if not resource_type_filters or any(
            ("glue" in _type) for _type in resource_type_filters
        ):
            if not resource_type_filters or "glue" in resource_type_filters:
                arns_starting_with = [
                    f"arn:aws:glue:{self.region_name}:{self.account_id}:"
                ]
            else:
                arns_starting_with = []
                for resource_type in resource_type_filters:
                    if resource_type.startswith("glue:"):
                        glue_type = resource_type.split(":")[-1]
                        arns_starting_with.append(
                            f"arn:aws:glue:{self.region_name}:{self.account_id}:{glue_type}"
                        )
            for glue_arn in self.glue_backend.tagger.tags.keys():
                if any(glue_arn.startswith(arn) for arn in arns_starting_with):
                    tags = self.glue_backend.tagger.list_tags_for_resource(glue_arn)[
                        "Tags"
                    ]
                    yield {"ResourceARN": glue_arn, "Tags": tags}

        # Kinesis

        # KMS
        if not resource_type_filters or "kms" in resource_type_filters:
            for kms_key in self.kms_backend.list_keys():
                tags = format_tag_keys(
                    self.kms_backend.list_resource_tags(kms_key.id).get("Tags", []),
                    ["TagKey", "TagValue"],
                )
                if not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue

                yield {"ResourceARN": f"{kms_key.arn}", "Tags": tags}

        # LOGS
        if (
            not resource_type_filters
            or "logs" in resource_type_filters
            or "logs:loggroup" in resource_type_filters
        ):
            for group in self.logs_backend.groups.values():
                log_tags = self.logs_backend.list_tags_for_resource(group.arn)
                tags = format_tags(log_tags)

                if not log_tags or not tag_filter(tags):
                    # Skip if no tags, or invalid filter
                    continue
                yield {"ResourceARN": group.arn, "Tags": tags}

        # RDS resources
        resource_map: Dict[str, Dict[str, Any]] = {
            "rds:cluster": self.rds_backend.clusters,
            "rds:db": self.rds_backend.databases,
            "rds:snapshot": self.rds_backend.database_snapshots,
            "rds:cluster-snapshot": self.rds_backend.cluster_snapshots,
        }
        for resource_type, resource_source in resource_map.items():
            if (
                not resource_type_filters
                or "rds" in resource_type_filters
                or resource_type in resource_type_filters
            ):
                for resource in resource_source.values():
                    tags = resource.get_tags()
                    if not tags or not tag_filter(tags):
                        continue
                    yield {
                        "ResourceARN": resource.arn,
                        "Tags": tags,
                    }

        # RDS Reserved Database Instance
        # RDS Option Group
        # RDS Parameter Group
        # RDS Security Group
        # RDS Subnet Group
        # RDS Event Subscription

        # RedShift Cluster
        # RedShift Hardware security module (HSM) client certificate
        # RedShift HSM connection
        # RedShift Parameter group
        # RedShift Snapshot
        # RedShift Subnet group

        # VPC
        if (
            not resource_type_filters
            or "ec2" in resource_type_filters
            or "ec2:vpc" in resource_type_filters
        ):
            for vpc in self.ec2_backend.vpcs.values():
                tags = format_tags(self.ec2_backend.tags.get(vpc.id, {}))
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:aws:ec2:{self.region_name}:{self.account_id}:vpc/{vpc.id}",
                    "Tags": tags,
                }
        # VPC Customer Gateway
        # VPC DHCP Option Set
        # VPC Internet Gateway
        # VPC Network ACL
        # VPC Route Table
        # VPC Subnet
        # VPC Virtual Private Gateway
        # VPC VPN Connection

        # Lambda Instance
        if not resource_type_filters or "lambda" in resource_type_filters:
            for f in self.lambda_backend.list_functions():
                tags = format_tags(f.tags)
                if not tags or not tag_filter(tags):
                    continue
                yield {
                    "ResourceARN": f.function_arn,
                    "Tags": tags,
                }

    def _get_tag_keys_generator(self) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # S3
        for bucket in self.s3_backend.buckets.values():
            tags = self.s3_backend.tagger.get_tag_dict_for_resource(bucket.arn)
            for key, _ in tags.items():
                yield key

        # EC2 tags
        def get_ec2_keys(res_id: str) -> List[Dict[str, str]]:
            result = []
            for key in self.ec2_backend.tags.get(res_id, {}):
                result.append(key)
            return result

        # EC2 AMI, resource type ec2:image
        for ami in self.ec2_backend.amis.values():
            for key in get_ec2_keys(ami.id):  # type: ignore[assignment]
                yield key

        # EC2 Instance, resource type ec2:instance
        for reservation in self.ec2_backend.reservations.values():
            for instance in reservation.instances:
                for key in get_ec2_keys(instance.id):  # type: ignore[assignment]
                    yield key

        # EC2 NetworkInterface, resource type ec2:network-interface
        for eni in self.ec2_backend.enis.values():
            for key in get_ec2_keys(eni.id):  # type: ignore[assignment]
                yield key

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        for vpc in self.ec2_backend.groups.values():
            for sg in vpc.values():
                for key in get_ec2_keys(sg.id):  # type: ignore[assignment]
                    yield key

        # EC2 Snapshot, resource type ec2:snapshot
        for snapshot in self.ec2_backend.snapshots.values():
            for key in get_ec2_keys(snapshot.id):  # type: ignore[assignment]
                yield key

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        for volume in self.ec2_backend.volumes.values():
            for key in get_ec2_keys(volume.id):  # type: ignore[assignment]
                yield key

        # Glue
        for tag_dict in self.glue_backend.tagger.tags.values():
            for tag_key in tag_dict.keys():
                yield tag_key

    def _get_tag_values_generator(self, tag_key: str) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Do S3, resource type s3
        for bucket in self.s3_backend.buckets.values():
            tags = self.s3_backend.tagger.get_tag_dict_for_resource(bucket.arn)
            for key, value in tags.items():
                if key == tag_key:
                    yield value

        # EC2 tags
        def get_ec2_values(res_id: str) -> List[Dict[str, str]]:
            result = []
            for key, value in self.ec2_backend.tags.get(res_id, {}).items():
                if key == tag_key:
                    result.append(value)
            return result

        # EC2 AMI, resource type ec2:image
        for ami in self.ec2_backend.amis.values():
            for value in get_ec2_values(ami.id):  # type: ignore[assignment]
                yield value

        # EC2 Instance, resource type ec2:instance
        for reservation in self.ec2_backend.reservations.values():
            for instance in reservation.instances:
                for value in get_ec2_values(instance.id):  # type: ignore[assignment]
                    yield value

        # EC2 NetworkInterface, resource type ec2:network-interface
        for eni in self.ec2_backend.enis.values():
            for value in get_ec2_values(eni.id):  # type: ignore[assignment]
                yield value

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        for vpc in self.ec2_backend.groups.values():
            for sg in vpc.values():
                for value in get_ec2_values(sg.id):  # type: ignore[assignment]
                    yield value

        # EC2 Snapshot, resource type ec2:snapshot
        for snapshot in self.ec2_backend.snapshots.values():
            for value in get_ec2_values(snapshot.id):  # type: ignore[assignment]
                yield value

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        for volume in self.ec2_backend.volumes.values():
            for value in get_ec2_values(volume.id):  # type: ignore[assignment]
                yield value

        # Glue
        for tag_dict in self.glue_backend.tagger.tags.values():
            for key, tag_value in tag_dict.items():
                if key == tag_key and tag_value is not None:
                    yield tag_value

    def get_resources(
        self,
        pagination_token: Optional[str] = None,
        resources_per_page: int = 50,
        tags_per_page: int = 100,
        tag_filters: Optional[List[Dict[str, Any]]] = None,
        resource_type_filters: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        # Simple range checking
        if 100 >= tags_per_page >= 500:
            raise RESTError(
                "InvalidParameterException", "TagsPerPage must be between 100 and 500"
            )
        if 1 >= resources_per_page >= 50:
            raise RESTError(
                "InvalidParameterException", "ResourcesPerPage must be between 1 and 50"
            )

        # If we have a token, go and find the respective generator, or error
        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError(
                    "PaginationTokenExpiredException", "Token does not exist"
                )

            generator = self._pages[pagination_token]["gen"]
            left_over = self._pages[pagination_token]["misc"]
        else:
            generator = self._get_resources_generator(
                tag_filters=tag_filters, resource_type_filters=resource_type_filters
            )
            left_over = None

        result = []
        current_tags = 0
        current_resources = 0
        if left_over:
            result.append(left_over)
            current_resources += 1
            current_tags += len(left_over["Tags"])

        try:
            while True:
                # Generator format: [{'ResourceARN': str, 'Tags': [{'Key': str, 'Value': str]}, ...]
                next_item = next(generator)
                resource_tags = len(next_item["Tags"])

                if current_resources >= resources_per_page:
                    break
                if current_tags + resource_tags >= tags_per_page:
                    break

                current_resources += 1
                current_tags += resource_tags

                result.append(next_item)

        except StopIteration:
            # Finished generator before invalidating page limiting constraints
            return None, result

        # Didn't hit StopIteration so there's stuff left in generator
        new_token = str(mock_random.uuid4())
        self._pages[new_token] = {"gen": generator, "misc": next_item}

        # Token used up, might as well bin now, if you call it again your an idiot
        if pagination_token:
            del self._pages[pagination_token]

        return new_token, result

    def get_tag_keys(
        self, pagination_token: Optional[str] = None
    ) -> Tuple[Optional[str], List[str]]:

        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError(
                    "PaginationTokenExpiredException", "Token does not exist"
                )

            generator = self._pages[pagination_token]["gen"]
            left_over = self._pages[pagination_token]["misc"]
        else:
            generator = self._get_tag_keys_generator()
            left_over = None

        result = []
        current_tags = 0
        if left_over:
            result.append(left_over)
            current_tags += 1

        try:
            while True:
                # Generator format: ['tag', 'tag', 'tag', ...]
                next_item = next(generator)

                if current_tags + 1 >= 128:
                    break

                current_tags += 1

                result.append(next_item)

        except StopIteration:
            # Finished generator before invalidating page limiting constraints
            return None, result

        # Didn't hit StopIteration so there's stuff left in generator
        new_token = str(mock_random.uuid4())
        self._pages[new_token] = {"gen": generator, "misc": next_item}

        # Token used up, might as well bin now, if you call it again your an idiot
        if pagination_token:
            del self._pages[pagination_token]

        return new_token, result

    def get_tag_values(
        self, pagination_token: Optional[str], key: str
    ) -> Tuple[Optional[str], List[str]]:

        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError(
                    "PaginationTokenExpiredException", "Token does not exist"
                )

            generator = self._pages[pagination_token]["gen"]
            left_over = self._pages[pagination_token]["misc"]
        else:
            generator = self._get_tag_values_generator(key)
            left_over = None

        result = []
        current_tags = 0
        if left_over:
            result.append(left_over)
            current_tags += 1

        try:
            while True:
                # Generator format: ['value', 'value', 'value', ...]
                next_item = next(generator)

                if current_tags + 1 >= 128:
                    break

                current_tags += 1

                result.append(next_item)

        except StopIteration:
            # Finished generator before invalidating page limiting constraints
            return None, result

        # Didn't hit StopIteration so there's stuff left in generator
        new_token = str(mock_random.uuid4())
        self._pages[new_token] = {"gen": generator, "misc": next_item}

        # Token used up, might as well bin now, if you call it again your an idiot
        if pagination_token:
            del self._pages[pagination_token]

        return new_token, result

    def tag_resources(
        self, resource_arns: List[str], tags: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Only Logs and RDS resources are currently supported
        """
        missing_resources = []
        missing_error: Dict[str, Any] = {
            "StatusCode": 404,
            "ErrorCode": "InternalServiceException",
            "ErrorMessage": "Service not yet supported",
        }
        for arn in resource_arns:
            if arn.startswith("arn:aws:rds:"):
                self.rds_backend.add_tags_to_resource(
                    arn, TaggingService.convert_dict_to_tags_input(tags)
                )
            if arn.startswith("arn:aws:logs:"):
                self.logs_backend.tag_resource(arn, tags)
            else:
                missing_resources.append(arn)
        return {arn: missing_error for arn in missing_resources}

    # def untag_resources(self, resource_arn_list, tag_keys):
    #     return failed_resources_map


resourcegroupstaggingapi_backends = BackendDict(
    ResourceGroupsTaggingAPIBackend, "resourcegroupstaggingapi"
)
