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
from moto.fsx.models import FSxBackend, fsx_backends
from moto.glacier.models import GlacierBackend, glacier_backends
from moto.glue.models import GlueBackend, glue_backends
from moto.kafka.models import KafkaBackend, kafka_backends
from moto.kinesis.models import KinesisBackend, kinesis_backends
from moto.kinesisanalyticsv2.models import (
    KinesisAnalyticsV2Backend,
    kinesisanalyticsv2_backends,
)
from moto.kms.models import KmsBackend, kms_backends
from moto.lexv2models.models import LexModelsV2Backend, lexv2models_backends
from moto.logs.models import LogsBackend, logs_backends
from moto.moto_api._internal import mock_random
from moto.quicksight.models import QuickSightBackend, quicksight_backends
from moto.redshift.models import RedshiftBackend, redshift_backends
from moto.resourcegroupstaggingapi.exceptions import (
    ResourceGroupsTaggingAPIError as RESTError,
)
from moto.sagemaker.models import SageMakerModelBackend, sagemaker_backends
from moto.secretsmanager import secretsmanager_backends
from moto.secretsmanager.models import ReplicaSecret, SecretsManagerBackend
from moto.servicecatalog.models import ServiceCatalogBackend, servicecatalog_backends
from moto.sesv2.models import SESV2Backend, sesv2_backends
from moto.sns.models import SNSBackend, sns_backends
from moto.sqs.models import SQSBackend, sqs_backends
from moto.ssm.models import SimpleSystemManagerBackend, ssm_backends
from moto.ssm.utils import parameter_arn
from moto.stepfunctions.models import StepFunctionBackend, stepfunctions_backends
from moto.swf.models import SWFBackend, swf_backends
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
    def glue_backend(self) -> GlueBackend:
        return glue_backends[self.account_id][self.region_name]

    @property
    def kinesis_backend(self) -> KinesisBackend:
        return kinesis_backends[self.account_id][self.region_name]

    @property
    def kinesisanalyticsv2_backend(self) -> KinesisAnalyticsV2Backend:
        return kinesisanalyticsv2_backends[self.account_id][self.region_name]

    @property
    def kms_backend(self) -> KmsBackend:
        return kms_backends[self.account_id][self.region_name]

    @property
    def logs_backend(self) -> LogsBackend:
        return logs_backends[self.account_id][self.region_name]

    @property
    def fsx_backends(self) -> FSxBackend:
        return fsx_backends[self.account_id][self.region_name]

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
    def secretsmanager_backend(self) -> SecretsManagerBackend:
        return secretsmanager_backends[self.account_id][self.region_name]

    @property
    def sns_backend(self) -> SNSBackend:
        return sns_backends[self.account_id][self.region_name]

    @property
    def ssm_backend(self) -> SimpleSystemManagerBackend:
        return ssm_backends[self.account_id][self.region_name]

    @property
    def sqs_backend(self) -> SQSBackend:
        return sqs_backends[self.account_id][self.region_name]

    @property
    def servicecatalog_backend(self) -> ServiceCatalogBackend:
        return servicecatalog_backends[self.account_id][self.region_name]

    @property
    def stepfunctions_backend(self) -> StepFunctionBackend:
        return stepfunctions_backends[self.account_id][self.region_name]

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
    def kafka_backend(self) -> KafkaBackend:
        return kafka_backends[self.account_id][self.region_name]

    @property
    def sagemaker_backend(self) -> SageMakerModelBackend:
        return sagemaker_backends[self.account_id][self.region_name]

    @property
    def lexv2_backend(self) -> LexModelsV2Backend | None:
        if self.region_name in lexv2models_backends[self.account_id].regions:
            return lexv2models_backends[self.account_id][self.region_name]
        return None

    @property
    def swf_backend(self) -> SWFBackend:
        return swf_backends[self.account_id][self.region_name]

    @property
    def quicksight_backend(self) -> QuickSightBackend | None:
        if self.region_name in quicksight_backends[self.account_id].regions:
            return quicksight_backends[self.account_id][self.region_name]
        return None

    @property
    def vpclattice_backend(self) -> VPCLatticeBackend:
        return vpclattice_backends[self.account_id][self.region_name]

    @property
    def sesv2_backend(self) -> SESV2Backend:
        return sesv2_backends[self.account_id][self.region_name]

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

        # FSx
        if not resource_type_filters or "fsx" in resource_type_filters:
            # File system
            for file_system in self.fsx_backends.file_systems.values():
                tags = self.fsx_backends.tagger.list_tags_for_resource(
                    file_system.resource_arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{file_system.resource_arn}", "Tags": tags}

            # Backup
            for backup in self.fsx_backends.backups.values():
                tags = self.fsx_backends.tagger.list_tags_for_resource(
                    backup.resource_arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{backup.resource_arn}", "Tags": tags}

        # Glacier Vault

        # Glue
        if not resource_type_filters or any(
            ("glue" in _type) for _type in resource_type_filters
        ):
            if not resource_type_filters or "glue" in resource_type_filters:
                arns_starting_with = [
                    f"arn:{get_partition(self.region_name)}:glue:{self.region_name}:{self.account_id}:"
                ]
            else:
                arns_starting_with = []
                for resource_type in resource_type_filters:
                    if resource_type.startswith("glue:"):
                        glue_type = resource_type.split(":")[-1]
                        arns_starting_with.append(
                            f"arn:{get_partition(self.region_name)}:glue:{self.region_name}:{self.account_id}:{glue_type}"
                        )
            for glue_arn in self.glue_backend.tagger.tags.keys():
                if any(glue_arn.startswith(arn) for arn in arns_starting_with):
                    tags = self.glue_backend.tagger.list_tags_for_resource(glue_arn)[
                        "Tags"
                    ]
                    yield {"ResourceARN": glue_arn, "Tags": tags}

        # Kinesis

        # KinesisAnalyticsV2
        if self.kinesisanalyticsv2_backend and (
            not resource_type_filters or "kinesisanalyticsv2" in resource_type_filters
        ):
            for application in self.kinesisanalyticsv2_backend.applications.values():
                tags = self.kinesisanalyticsv2_backend.tagger.list_tags_for_resource(
                    application.application_arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {
                    "ResourceARN": application.application_arn,
                    "Tags": tags,
                }

        # KMS
        if (
            not resource_type_filters
            or "kms" in resource_type_filters
            or "kms:key" in resource_type_filters
        ):
            for kms_key in self.kms_backend.list_keys():
                tags = format_tag_keys(
                    self.kms_backend.list_resource_tags(kms_key.id).get("Tags", []),
                    ["TagKey", "TagValue"],
                )
                if not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue

                yield {"ResourceARN": f"{kms_key.arn}", "Tags": tags}

        # LexV2
        if self.lexv2_backend:
            lex_v2_resource_map: dict[str, dict[str, Any]] = {
                "lexv2:bot": self.lexv2_backend.bots,
                "lexv2:bot-alias": self.lexv2_backend.bot_aliases,
            }
            for resource_type, resource_source in lex_v2_resource_map.items():
                if (
                    not resource_type_filters
                    or "lexv2" in resource_type_filters
                    or resource_type in resource_type_filters
                ):
                    for resource in resource_source.values():
                        bot_tags = self.lexv2_backend.list_tags_for_resource(
                            resource.arn
                        )

                        tags = format_tags(bot_tags)
                        if not tags or not tag_filter(tags):
                            continue
                        yield {
                            "ResourceARN": resource.arn,
                            "Tags": tags,
                        }

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

        # Quicksight
        if self.quicksight_backend:
            quicksight_resource_map: dict[str, dict[str, Any]] = {
                "quicksight:dashboards": dict(self.quicksight_backend.dashboards),
                "quicksight:data_sources": dict(self.quicksight_backend.data_sources),
                "quicksight:data_sets": dict(self.quicksight_backend.data_sets),
                "quicksight:users": dict(self.quicksight_backend.users),
            }

            for resource_type, resource_source in quicksight_resource_map.items():
                if (
                    not resource_type_filters
                    or "quicksight" in resource_type_filters
                    or resource_type in resource_type_filters
                ):
                    for resource in resource_source.values():
                        tags = self.quicksight_backend.tagger.list_tags_for_resource(
                            resource.arn
                        )["Tags"]

                        if not tags or not tag_filter(tags):
                            continue

                        yield {
                            "ResourceARN": resource.arn,
                            "Tags": tags,
                        }

        # RedShift Cluster
        # RedShift Hardware security module (HSM) client certificate
        # RedShift HSM connection
        # RedShift Parameter group
        # RedShift Snapshot
        # RedShift Subnet group

        # Secrets Manager
        if (
            not resource_type_filters
            or "secretsmanager" in resource_type_filters
            or "secretsmanager:secret" in resource_type_filters
        ):
            for secret in self.secretsmanager_backend.secrets.values():
                if isinstance(secret, ReplicaSecret):
                    secret_tags = secret.source.tags
                else:
                    secret_tags = secret.tags

                if secret_tags:
                    formated_tags = format_tag_keys(secret_tags, ["Key", "Value"])
                    if not formated_tags or not tag_filter(formated_tags):
                        continue
                    yield {"ResourceARN": f"{secret.arn}", "Tags": formated_tags}

        # SQS
        if (
            not resource_type_filters
            or "sqs" in resource_type_filters
            or "sqs:queue" in resource_type_filters
        ):
            for queue in self.sqs_backend.queues.values():
                tags = format_tags(queue.tags)
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue

                yield {"ResourceARN": f"{queue.queue_arn}", "Tags": tags}

        # Service Catalog
        if not resource_type_filters or "servicecatalog" in resource_type_filters:
            # Portfolio
            for portfolio in self.servicecatalog_backend.portfolios.values():
                tags = self.servicecatalog_backend.tagger.list_tags_for_resource(
                    portfolio.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{portfolio.arn}", "Tags": tags}

            # Product
            for product in self.servicecatalog_backend.products.values():
                tags = self.servicecatalog_backend.tagger.list_tags_for_resource(
                    product.arn
                )["Tags"]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": f"{product.arn}", "Tags": tags}

        if self.sesv2_backend:
            sesv2_resource_map: dict[str, dict[str, Any]] = {
                "ses:configuration-set": self.sesv2_backend.core_backend.config_sets,
                "ses:contact-list": self.sesv2_backend.core_backend.contacts_lists,
                "ses:dedicated-ip-pool": self.sesv2_backend.core_backend.dedicated_ip_pools,
                "ses:email-identity": self.sesv2_backend.core_backend.email_identities,
            }

            resource_id_attr_map: dict[str, str] = {
                "ses:configuration-set": "configuration_set_name",
                "ses:contact-list": "contact_list_name",
                "ses:dedicated-ip-pool": "pool_name",
                "ses:email-identity": "email_identity",
            }

            for resource_type, resource_source in sesv2_resource_map.items():
                if (
                    not resource_type_filters
                    or "ses" in resource_type_filters
                    or resource_type in resource_type_filters
                ):
                    for resource in resource_source.values():
                        resource_id_attr = resource_id_attr_map[resource_type]
                        resource_id = getattr(resource, resource_id_attr)

                        arn = f"arn:{get_partition(self.region_name)}:ses:{self.region_name}:{self.account_id}:{resource_type.split(':')[-1]}/{resource_id}"

                        tags = self.sesv2_backend.core_backend.tagger.list_tags_for_resource(
                            arn
                        )["Tags"]

                        if not tags or not tag_filter(tags):
                            continue

                        yield {
                            "ResourceARN": arn,
                            "Tags": tags,
                        }
        # SNS
        if not resource_type_filters or "sns" in resource_type_filters:
            for topic in self.sns_backend.topics.values():
                tags = format_tags(topic._tags)
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {"ResourceARN": f"{topic.arn}", "Tags": tags}

        # SSM Documents
        if (
            not resource_type_filters
            or "ssm" in resource_type_filters
            or "ssm:document" in resource_type_filters
        ):
            for document in self.ssm_backend._documents.values():
                doc_name = document.describe()["Name"]
                tags = self.ssm_backend._get_documents_tags(doc_name)
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": f"arn:{get_partition(self.region_name)}:ssm:{self.region_name}:{self.account_id}:document/{doc_name}",
                    "Tags": tags,
                }

        # SSM Parameters
        if (
            not resource_type_filters
            or "ssm" in resource_type_filters
            or "ssm:parameter" in resource_type_filters
        ):
            for param_name in self.ssm_backend._parameters:
                tags = format_tags(
                    self.ssm_backend.list_tags_for_resource("Parameter", param_name)
                )
                if not tags or not tag_filter(
                    tags
                ):  # Skip if no tags, or invalid filter
                    continue
                yield {
                    "ResourceARN": parameter_arn(
                        self.account_id, self.region_name, param_name
                    ),
                    "Tags": tags,
                }

        # Step Functions
        if not resource_type_filters or "states:stateMachine" in resource_type_filters:
            for state_machine in self.stepfunctions_backend.state_machines:
                tags = format_tag_keys(
                    state_machine.backend.get_tags_list_for_state_machine(
                        state_machine.arn
                    ),
                    [
                        state_machine.backend.tagger.key_name,
                        state_machine.backend.tagger.value_name,
                    ],
                )
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": state_machine.arn, "Tags": tags}

        # SWF
        if (
            not resource_type_filters
            or "swf" in resource_type_filters
            or "swf:domain" in resource_type_filters
        ):
            for domain in self.swf_backend.domains:
                domain_arn = domain.to_short_dict()["arn"]
                tags = self.swf_backend.tagger.list_tags_for_resource(domain_arn)[
                    "Tags"
                ]
                if not tags or not tag_filter(tags):
                    continue
                yield {"ResourceARN": domain_arn, "Tags": tags}

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

        # Kafka (MSK)
        if self.kafka_backend and (
            not resource_type_filters or "kafka" in resource_type_filters
        ):
            for msk_cluster in self.kafka_backend.clusters.values():
                tag_dict = self.kafka_backend.list_tags_for_resource(msk_cluster.arn)
                tags = [{"Key": key, "Value": value} for key, value in tag_dict.items()]

                if not tags or not tag_filter(tags):
                    continue

                yield {
                    "ResourceARN": msk_cluster.arn,
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

        # sagemaker cluster, automljob, compilation-job, domain, model-explainability-job-definition, model-quality-job-definition, and hyper-parameter-tuning-job currently supported
        sagemaker_resource_map: dict[str, dict[str, Any]] = {
            "sagemaker:cluster": self.sagemaker_backend.clusters,
            "sagemaker:automl-job": self.sagemaker_backend.auto_ml_jobs,
            "sagemaker:compilation-job": self.sagemaker_backend.compilation_jobs,
            "sagemaker:domain": self.sagemaker_backend.domains,
            "sagemaker:model-explainability-job-definition": self.sagemaker_backend.model_explainability_job_definitions,
            "sagemaker:model-quality-job-definition": self.sagemaker_backend.model_quality_job_definitions,
            "sagemaker:hyper-parameter-tuning-job": self.sagemaker_backend.hyper_parameter_tuning_jobs,
            "sagemaker:model-bias-job-definition": self.sagemaker_backend.model_bias_job_definitions,
            "sagemaker:data-quality-job-definition": self.sagemaker_backend.data_quality_job_definitions,
            "sagemaker:model": self.sagemaker_backend._models,
            "sagemaker:notebook-instance": self.sagemaker_backend.notebook_instances,
            "sagemaker:endpoint-config": self.sagemaker_backend.endpoint_configs,
            "sagemaker:endpoint": self.sagemaker_backend.endpoints,
            "sagemaker:experiment": self.sagemaker_backend.experiments,
            "sagemaker:pipeline": self.sagemaker_backend.pipelines,
            "sagemaker:pipeline-execution": self.sagemaker_backend.pipeline_executions,
            "sagemaker:processing-job": self.sagemaker_backend.processing_jobs,
            "sagemaker:trial": self.sagemaker_backend.trials,
            "sagemaker:trial-component": self.sagemaker_backend.trial_components,
            "sagemaker:training-job": self.sagemaker_backend.training_jobs,
            "sagemaker:transform-job": self.sagemaker_backend.transform_jobs,
            "sagemaker:notebook-instance-lifecycle-config": self.sagemaker_backend.notebook_instance_lifecycle_configurations,
            "sagemaker:model-card": self.sagemaker_backend.model_cards,
            "sagemaker:model-package-group": self.sagemaker_backend.model_package_groups,
            "sagemaker:model-package": self.sagemaker_backend.model_packages,
            "sagemaker:feature-group": self.sagemaker_backend.feature_groups,
        }
        for resource_type, resource_source in sagemaker_resource_map.items():
            if (
                not resource_type_filters
                or "sagemaker" in resource_type_filters
                or resource_type in resource_type_filters
            ):
                for resource in resource_source.values():
                    tags = self.sagemaker_backend.list_tags(resource.arn)[0]
                    if not tags or not tag_filter(tags):
                        continue
                    yield {
                        "ResourceARN": resource.arn,
                        "Tags": tags,
                    }

    def _get_tag_keys_generator(self) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Services opted in via TaggableResourcesMixin
        for backend in iter_taggable_backends(self.account_id, self.region_name):
            for resource in backend.iter_tagged_resources():
                yield from resource.tags.keys()

        # Glue
        for tag_dict in self.glue_backend.tagger.tags.values():
            yield from tag_dict.keys()

    def _get_tag_values_generator(self, tag_key: str) -> Iterator[str]:
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Services opted in via TaggableResourcesMixin
        for backend in iter_taggable_backends(self.account_id, self.region_name):
            for resource in backend.iter_tagged_resources():
                for key, value in resource.tags.items():
                    if key == tag_key:
                        yield value

        # Glue
        for tag_dict in self.glue_backend.tagger.tags.values():
            for key, tag_value in tag_dict.items():
                if key == tag_key and tag_value is not None:
                    yield tag_value

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
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:logs:"):
                self.logs_backend.tag_resource(arn, tags)
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:sagemaker:"):
                self.sagemaker_backend.add_tags(
                    arn, TaggingService.convert_dict_to_tags_input(tags)
                )

            elif arn.startswith(f"arn:{get_partition(self.region_name)}:quicksight:"):
                assert self.quicksight_backend is not None
                self.quicksight_backend.tag_resource(
                    arn, TaggingService.convert_dict_to_tags_input(tags)
                )
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:ses:"):
                self.sesv2_backend.tag_resource(
                    arn, TaggingService.convert_dict_to_tags_input(tags)
                )
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:swf:"):
                self.swf_backend.tagger.tag_resource(
                    arn, TaggingService.convert_dict_to_tags_input(tags)
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
            if arn.startswith(f"arn:{get_partition(self.region_name)}:quicksight:"):
                assert self.quicksight_backend is not None
                self.quicksight_backend.untag_resource(arn, tag_keys)
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:ses:"):
                self.sesv2_backend.untag_resource(arn, tag_keys)
            elif arn.startswith(f"arn:{get_partition(self.region_name)}:swf:"):
                self.swf_backend.tagger.untag_resource_using_names(arn, tag_keys)
            else:
                missing_resources.append(arn)

        return dict.fromkeys(missing_resources, missing_error)


resourcegroupstaggingapi_backends = BackendDict(
    ResourceGroupsTaggingAPIBackend, "resourcegroupstaggingapi"
)
