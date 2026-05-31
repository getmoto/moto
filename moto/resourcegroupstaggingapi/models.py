from collections.abc import Iterator
from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.resource_tagging import (
    TaggableResourcesMixin,
    iter_taggable_backends,
    make_tag_matcher,
    match_resource_type,
)
from moto.emr.models import ElasticMapReduceBackend, emr_backends
from moto.glacier.models import GlacierBackend, glacier_backends
from moto.kinesis.models import KinesisBackend, kinesis_backends
from moto.moto_api._internal import mock_random
from moto.redshift.models import RedshiftBackend, redshift_backends
from moto.resourcegroupstaggingapi.exceptions import (
    ResourceGroupsTaggingAPIError as RESTError,
)
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition
from moto.vpclattice.models import VPCLatticeBackend, vpclattice_backends
from moto.workspaces.models import WorkSpacesBackend, workspaces_backends
from moto.workspacesweb.models import WorkSpacesWebBackend, workspacesweb_backends

# Left: EC2 RDS ELB Lambda EMR Glacier Kinesis Redshift Route53
# StorageGateway MachineLearning ACM DirectoryService CloudHSM
# Inspector Elasticsearch


class ResourceGroupsTaggingAPIBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)

        self._pages: dict[str, Any] = {}
        # Like 'someuuid': {'gen': <generator>, 'misc': None}
        # Misc is there for peeking from a generator and it cant
        # fit in the current request. As we only store generators
        # there is really no point cleaning up

    @property
    def kinesis_backend(self) -> KinesisBackend:
        return kinesis_backends[self.account_id][self.region_name]

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
    def workspaces_backend(self) -> WorkSpacesBackend | None:
        # Workspaces service has limited region availability
        if self.region_name in workspaces_backends[self.account_id].regions:
            return workspaces_backends[self.account_id][self.region_name]
        return None

    @property
    def workspacesweb_backends(self) -> WorkSpacesWebBackend | None:
        # WorkspacesWeb service has limited region availability
        if self.region_name in workspacesweb_backends[self.account_id].regions:
            return workspacesweb_backends[self.account_id][self.region_name]
        return None

    @property
    def vpclattice_backend(self) -> VPCLatticeBackend:
        return vpclattice_backends[self.account_id][self.region_name]

    def _get_backend_for_resource(
        self, resource_arn: str
    ) -> TaggableResourcesMixin | None:
        backend = next(
            (
                b
                for b in iter_taggable_backends(self.account_id, self.region_name)
                if b.owns_arn(resource_arn)
            ),
            None,
        )
        return backend

    def _get_resources_generator(
        self,
        tag_filters: list[dict[str, Any]] | None = None,
        resource_type_filters: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
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

        def tag_filter(tag_list: list[dict[str, Any]]) -> bool:
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

        def format_tags(tags: dict[str, Any]) -> list[dict[str, Any]]:
            result = []
            for key, value in tags.items():
                result.append({"Key": key, "Value": value})
            return result

        def format_tag_keys(
            tags: list[dict[str, Any]], keys: list[str]
        ) -> list[dict[str, Any]]:
            result = []
            for tag in tags:
                result.append({"Key": tag[keys[0]], "Value": tag[keys[1]]})
            return result

        # Services opted in via TaggableResourcesMixin
        tag_matcher = make_tag_matcher(tag_filters)
        for backend in iter_taggable_backends(self.account_id, self.region_name):
            for resource in backend.iter_tagged_resources():
                if not resource.tags and not resource.extra.get("include_untagged"):
                    continue
                if not match_resource_type(
                    resource.resource_type, resource_type_filters
                ):
                    continue
                if not tag_matcher(resource.tags):
                    continue
                yield {
                    "ResourceARN": resource.arn,
                    "Tags": [{"Key": k, "Value": v} for k, v in resource.tags.items()],
                }

        # EMR Cluster

        # Glacier Vault

        # Kinesis

        # RedShift Cluster
        # RedShift Hardware security module (HSM) client certificate
        # RedShift HSM connection
        # RedShift Parameter group
        # RedShift Snapshot
        # RedShift Subnet group

        # VPC Lattice
        if not resource_type_filters or "vpc-lattice" in resource_type_filters:
            # Service
            for service in self.vpclattice_backend.services.values():  # type: ignore[assignment]
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    service.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{service.arn}", "Tags": tags}

            # Service Networks
            for service_network in self.vpclattice_backend.service_networks.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    service_network.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{service_network.arn}", "Tags": tags}

            # Service Network VPC Associations
            for (
                assoc
            ) in self.vpclattice_backend.service_network_vpc_associations.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(assoc.arn)[
                    "Tags"
                ]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{assoc.arn}", "Tags": tags}

            # Rules
            for rule in self.vpclattice_backend.rules.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(rule.arn)[
                    "Tags"
                ]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{rule.arn}", "Tags": tags}

            # Access Log Subscriptions
            for sub in self.vpclattice_backend.access_log_subscriptions.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(sub.arn)[
                    "Tags"
                ]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{sub.arn}", "Tags": tags}

            # Listener
            for listener in self.vpclattice_backend.listeners.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    listener.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{listener.arn}", "Tags": tags}

            # Target Group
            for vpc_target_group in self.vpclattice_backend.target_groups.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    vpc_target_group.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{vpc_target_group.arn}", "Tags": tags}

            # Service Network Resource Association
            for (
                service_network_resource_association
            ) in self.vpclattice_backend.service_network_resource_associations.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    service_network_resource_association.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {
                    "ResourceARN": f"{service_network_resource_association.arn}",
                    "Tags": tags,
                }

            # Service Network Service Association
            for (
                service_network_service_association
            ) in self.vpclattice_backend.service_network_service_associations.values():
                tags = self.vpclattice_backend.tagger.list_tags_for_resource(
                    service_network_service_association.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {
                    "ResourceARN": f"{service_network_service_association.arn}",
                    "Tags": tags,
                }

        # Workspaces
        if self.workspaces_backend and (
            not resource_type_filters or "workspaces" in resource_type_filters
        ):
            for ws in self.workspaces_backend.workspaces.values():
                tags = format_tag_keys(ws.tags, ["Key", "Value"])
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue

                yield {
                    "ResourceARN": f"arn:{get_partition(self.region_name)}:workspaces:{self.region_name}:{self.account_id}:workspace/{ws.workspace_id}",
                    "Tags": tags,
                }

        # Workspace Directories
        if self.workspaces_backend and (
            not resource_type_filters or "workspaces-directory" in resource_type_filters
        ):
            for wd in self.workspaces_backend.workspace_directories.values():
                tags = format_tag_keys(wd.tags, ["Key", "Value"])
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue

                yield {
                    "ResourceARN": f"arn:{get_partition(self.region_name)}:workspaces:{self.region_name}:{self.account_id}:directory/{wd.directory_id}",
                    "Tags": tags,
                }

        # Workspace Images
        if self.workspaces_backend and (
            not resource_type_filters or "workspaces-image" in resource_type_filters
        ):
            for wi in self.workspaces_backend.workspace_images.values():
                tags = format_tag_keys(wi.tags, ["Key", "Value"])
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue

                yield {
                    "ResourceARN": f"arn:{get_partition(self.region_name)}:workspaces:{self.region_name}:{self.account_id}:workspaceimage/{wi.image_id}",
                    "Tags": tags,
                }

        # Workspaces Web
        if self.workspacesweb_backends and (
            not resource_type_filters or "workspaces-web" in resource_type_filters
        ):
            for portal in self.workspacesweb_backends.portals.values():
                tags = self.workspacesweb_backends.tagger.list_tags_for_resource(
                    portal.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {
                    "ResourceARN": f"arn:{get_partition(self.region_name)}:workspaces-web:{self.region_name}:{self.account_id}:portal/{portal.portal_id}",
                    "Tags": tags,
                }

    def _get_tag_keys_generator(self) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Services opted in via TaggableResourcesMixin
        for backend in iter_taggable_backends(self.account_id, self.region_name):
            for resource in backend.iter_tagged_resources():
                yield from resource.tags.keys()

    def _get_tag_values_generator(self, tag_key: str) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Services opted in via TaggableResourcesMixin
        for backend in iter_taggable_backends(self.account_id, self.region_name):
            for resource in backend.iter_tagged_resources():
                for key, value in resource.tags.items():
                    if key == tag_key:
                        yield value

    def get_resources(
        self,
        pagination_token: str | None = None,
        resources_per_page: int = 50,
        tags_per_page: int = 100,
        tag_filters: list[dict[str, Any]] | None = None,
        resource_type_filters: list[str] | None = None,
    ) -> tuple[str | None, list[dict[str, Any]]]:
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

        # Token used up, might as well bin now, if you call it again you're an idiot
        if pagination_token:
            del self._pages[pagination_token]
        return new_token, result

    def get_tag_keys(
        self, pagination_token: str | None = None
    ) -> tuple[str | None, list[str]]:
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
        self, pagination_token: str | None, key: str
    ) -> tuple[str | None, list[str]]:
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
        self, resource_arns: list[str], tags: dict[str, str]
    ) -> dict[str, dict[str, Any]]:
        """
        Only EFS, Elasticache, Lambda, Logs, Quicksight, RDS, SageMaker, SES, and SWF resources are currently supported
        """
        missing_resources = []
        missing_error: dict[str, Any] = {
            "StatusCode": 404,
            "ErrorCode": "InternalServiceException",
            "ErrorMessage": "Service not yet supported",
        }

        for arn in resource_arns:
            backend_for_arn = self._get_backend_for_resource(arn)
            if backend_for_arn is not None:
                try:
                    backend_for_arn.tag_resource(arn, tags)
                except NotImplementedError:
                    missing_resources.append(arn)
                continue
            if arn.startswith(f"arn:{get_partition(self.region_name)}:workspaces-web:"):
                resource_id = arn.split("/")[-1]
                self.workspacesweb_backends.create_tags(  # type: ignore[union-attr]
                    resource_id, TaggingService.convert_dict_to_tags_input(tags)
                )
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:workspaces:"):
                resource_id = arn.split("/")[-1]
                self.workspaces_backend.create_tags(  # type: ignore[union-attr]
                    resource_id, TaggingService.convert_dict_to_tags_input(tags)
                )
            else:
                missing_resources.append(arn)
        return dict.fromkeys(missing_resources, missing_error)

    def untag_resources(
        self, resource_arn_list: list[str], tag_keys: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Only EFS, Elasticache, Lambda, Quicksight, SES, and SWF resources are currently supported
        """
        missing_resources = []
        missing_error: dict[str, Any] = {
            "StatusCode": 404,
            "ErrorCode": "InternalServiceException",
            "ErrorMessage": "Service not yet supported",
        }

        for arn in resource_arn_list:
            backend_for_arn = self._get_backend_for_resource(arn)
            if backend_for_arn is not None:
                try:
                    backend_for_arn.untag_resource(arn, tag_keys)
                except NotImplementedError:
                    missing_resources.append(arn)
                continue

        return dict.fromkeys(missing_resources, missing_error)


resourcegroupstaggingapi_backends = BackendDict(
    ResourceGroupsTaggingAPIBackend, "resourcegroupstaggingapi"
)
