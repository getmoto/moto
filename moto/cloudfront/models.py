import string

from datetime import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, iso_8601_datetime_with_milliseconds
from moto.moto_api import state_manager
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.moto_api._internal import mock_random as random
from moto.utilities.tagging_service import TaggingService

from .exceptions import (
    OriginDoesNotExist,
    InvalidOriginServer,
    DomainNameNotAnS3Bucket,
    DistributionAlreadyExists,
    InvalidIfMatchVersion,
    NoSuchDistribution,
)


class ActiveTrustedSigners:
    def __init__(self):
        self.enabled = False
        self.quantity = 0
        self.signers = []


class ActiveTrustedKeyGroups:
    def __init__(self):
        self.enabled = False
        self.quantity = 0
        self.kg_key_pair_ids = []


class LambdaFunctionAssociation:
    def __init__(self):
        self.arn = ""
        self.event_type = ""
        self.include_body = False


class ForwardedValues:
    def __init__(self, config):
        self.query_string = config.get("QueryString", "false")
        self.cookie_forward = config.get("Cookies", {}).get("Forward") or "none"
        self.whitelisted_names = (
            config.get("Cookies", {}).get("WhitelistedNames", {}).get("Items") or {}
        )
        self.whitelisted_names = self.whitelisted_names.get("Name") or []
        if isinstance(self.whitelisted_names, str):
            self.whitelisted_names = [self.whitelisted_names]
        self.headers = []
        self.query_string_cache_keys = []


class DefaultCacheBehaviour:
    def __init__(self, config):
        self.target_origin_id = config["TargetOriginId"]
        self.trusted_signers_enabled = False
        self.trusted_signers = []
        self.trusted_key_groups_enabled = False
        self.trusted_key_groups = []
        self.viewer_protocol_policy = config["ViewerProtocolPolicy"]
        methods = config.get("AllowedMethods", {})
        self.allowed_methods = methods.get("Items", {}).get("Method", ["HEAD", "GET"])
        self.cached_methods = (
            methods.get("CachedMethods", {})
            .get("Items", {})
            .get("Method", ["GET", "HEAD"])
        )
        self.smooth_streaming = config.get("SmoothStreaming") or True
        self.compress = config.get("Compress", "true").lower() == "true"
        self.lambda_function_associations = []
        self.function_associations = []
        self.field_level_encryption_id = ""
        self.forwarded_values = ForwardedValues(config.get("ForwardedValues", {}))
        self.min_ttl = config.get("MinTTL") or 0
        self.default_ttl = config.get("DefaultTTL") or 0
        self.max_ttl = config.get("MaxTTL") or 0


class Logging:
    def __init__(self):
        self.enabled = False
        self.include_cookies = False


class ViewerCertificate:
    def __init__(self):
        self.cloud_front_default_certificate = True
        self.min_protocol_version = "TLSv1"
        self.certificate_source = "cloudfront"


class CustomOriginConfig:
    def __init__(self, config):
        self.http_port = config.get("HTTPPort")
        self.https_port = config.get("HTTPSPort")
        self.keep_alive = config.get("OriginKeepaliveTimeout")
        self.protocol_policy = config.get("OriginProtocolPolicy")
        self.read_timeout = config.get("OriginReadTimeout")
        self.ssl_protocols = (
            config.get("OriginSslProtocols", {}).get("Items", {}).get("SslProtocol")
            or []
        )


class Origin:
    def __init__(self, origin):
        self.id = origin["Id"]
        self.domain_name = origin["DomainName"]
        self.custom_headers = []
        self.s3_access_identity = ""
        self.custom_origin = None
        self.origin_shield = origin.get("OriginShield")
        self.connection_attempts = origin.get("ConnectionAttempts") or 3
        self.connection_timeout = origin.get("ConnectionTimeout") or 10

        if "S3OriginConfig" not in origin and "CustomOriginConfig" not in origin:
            raise InvalidOriginServer

        if "S3OriginConfig" in origin:
            # Very rough validation
            if not self.domain_name.endswith("amazonaws.com"):
                raise DomainNameNotAnS3Bucket
            self.s3_access_identity = origin["S3OriginConfig"]["OriginAccessIdentity"]

        if "CustomOriginConfig" in origin:
            self.custom_origin = CustomOriginConfig(origin["CustomOriginConfig"])


class GeoRestrictions:
    def __init__(self, config):
        config = config.get("GeoRestriction") or {}
        self._type = config.get("RestrictionType", "none")
        self.restrictions = (config.get("Items") or {}).get("Location") or []


class DistributionConfig:
    def __init__(self, config):
        self.config = config
        self.aliases = ((config.get("Aliases") or {}).get("Items") or {}).get(
            "CNAME"
        ) or []
        self.comment = config.get("Comment") or ""
        self.default_cache_behavior = DefaultCacheBehaviour(
            config["DefaultCacheBehavior"]
        )
        self.cache_behaviors = []
        self.custom_error_responses = []
        self.logging = Logging()
        self.enabled = config.get("Enabled") or False
        self.viewer_certificate = ViewerCertificate()
        self.geo_restriction = GeoRestrictions(config.get("Restrictions") or {})
        self.caller_reference = config.get("CallerReference", str(random.uuid4()))
        self.origins = config["Origins"]["Items"]["Origin"]
        if not isinstance(self.origins, list):
            self.origins = [self.origins]

        # This check happens before any other Origins-validation
        if self.default_cache_behavior.target_origin_id not in [
            o["Id"] for o in self.origins
        ]:
            raise OriginDoesNotExist

        self.origins = [Origin(o) for o in self.origins]
        self.price_class = config.get("PriceClass", "PriceClass_All")
        self.http_version = config.get("HttpVersion", "http2")
        self.is_ipv6_enabled = config.get("IsIPV6Enabled", "true").lower() == "true"
        self.default_root_object = config.get("DefaultRootObject") or ""


class Distribution(BaseModel, ManagedState):
    @staticmethod
    def random_id(uppercase=True):
        ascii_set = string.ascii_uppercase if uppercase else string.ascii_lowercase
        chars = list(range(10)) + list(ascii_set)
        resource_id = random.choice(ascii_set) + "".join(
            str(random.choice(chars)) for _ in range(12)
        )
        return resource_id

    def __init__(self, account_id, config):
        # Configured ManagedState
        super().__init__(
            "cloudfront::distribution", transitions=[("InProgress", "Deployed")]
        )
        # Configure internal properties
        self.distribution_id = Distribution.random_id()
        self.arn = (
            f"arn:aws:cloudfront:{account_id}:distribution/{self.distribution_id}"
        )
        self.distribution_config = DistributionConfig(config)
        self.active_trusted_signers = ActiveTrustedSigners()
        self.active_trusted_key_groups = ActiveTrustedKeyGroups()
        self.origin_groups = []
        self.alias_icp_recordals = []
        self.last_modified_time = "2021-11-27T10:34:26.802Z"
        self.in_progress_invalidation_batches = 0
        self.has_active_trusted_key_groups = False
        self.domain_name = f"{Distribution.random_id(uppercase=False)}.cloudfront.net"
        self.etag = Distribution.random_id()

    @property
    def location(self):
        return f"https://cloudfront.amazonaws.com/2020-05-31/distribution/{self.distribution_id}"


class Invalidation(BaseModel):
    @staticmethod
    def random_id(uppercase=True):
        ascii_set = string.ascii_uppercase if uppercase else string.ascii_lowercase
        chars = list(range(10)) + list(ascii_set)
        resource_id = random.choice(ascii_set) + "".join(
            str(random.choice(chars)) for _ in range(12)
        )
        return resource_id

    def __init__(self, distribution, paths, caller_ref):
        self.invalidation_id = Invalidation.random_id()
        self.create_time = iso_8601_datetime_with_milliseconds(datetime.now())
        self.distribution = distribution
        self.status = "COMPLETED"

        self.paths = paths
        self.caller_ref = caller_ref

    @property
    def location(self):
        return self.distribution.location + f"/invalidation/{self.invalidation_id}"


class CloudFrontBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.distributions = dict()
        self.tagger = TaggingService()

        state_manager.register_default_transition(
            "cloudfront::distribution", transition={"progression": "manual", "times": 1}
        )

    def create_distribution(self, distribution_config, tags):
        """
        Not all configuration options are supported yet.  Please raise an issue if
        we're not persisting/returning the correct attributes for your
        use-case.
        """
        # We'll always call dist_with_tags, as the incoming request is the same
        return self.create_distribution_with_tags(distribution_config, tags)

    def create_distribution_with_tags(self, distribution_config, tags):
        dist = Distribution(self.account_id, distribution_config)
        caller_reference = dist.distribution_config.caller_reference
        existing_dist = self._distribution_with_caller_reference(caller_reference)
        if existing_dist:
            raise DistributionAlreadyExists(existing_dist.distribution_id)
        self.distributions[dist.distribution_id] = dist
        self.tagger.tag_resource(dist.arn, tags)
        return dist, dist.location, dist.etag

    def get_distribution(self, distribution_id):
        if distribution_id not in self.distributions:
            raise NoSuchDistribution
        dist = self.distributions[distribution_id]
        dist.advance()
        return dist, dist.etag

    def delete_distribution(self, distribution_id, if_match):
        """
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        """
        if not if_match:
            raise InvalidIfMatchVersion
        if distribution_id not in self.distributions:
            raise NoSuchDistribution
        del self.distributions[distribution_id]

    def list_distributions(self):
        """
        Pagination is not supported yet.
        """
        for dist in self.distributions.values():
            dist.advance()
        return self.distributions.values()

    def _distribution_with_caller_reference(self, reference):
        for dist in self.distributions.values():
            config = dist.distribution_config
            if config.caller_reference == reference:
                return dist
        return False

    def update_distribution(self, dist_config, _id, if_match):
        """
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        """
        if _id not in self.distributions or _id is None:
            raise NoSuchDistribution
        if not if_match:
            raise InvalidIfMatchVersion
        if not dist_config:
            raise NoSuchDistribution
        dist = self.distributions[_id]

        aliases = dist_config["Aliases"]["Items"]["CNAME"]
        dist.distribution_config.config = dist_config
        dist.distribution_config.aliases = aliases
        self.distributions[_id] = dist
        dist.advance()
        return dist, dist.location, dist.etag

    def create_invalidation(self, dist_id, paths, caller_ref):
        dist, _ = self.get_distribution(dist_id)
        invalidation = Invalidation(dist, paths, caller_ref)

        return invalidation

    def list_tags_for_resource(self, resource):
        return self.tagger.list_tags_for_resource(resource)


cloudfront_backends = BackendDict(
    CloudFrontBackend,
    "cloudfront",
    use_boto3_regions=False,
    additional_regions=["global"],
)
