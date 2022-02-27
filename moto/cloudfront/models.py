import random
import string

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from uuid import uuid4

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
    def __init__(self):
        self.query_string = ""
        self.whitelisted_names = []
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
        self.allowed_methods = ["HEAD", "GET"]
        self.cached_methods = ["GET", "HEAD"]
        self.smooth_streaming = True
        self.compress = True
        self.lambda_function_associations = []
        self.function_associations = []
        self.field_level_encryption_id = ""
        self.forwarded_values = ForwardedValues()
        self.min_ttl = 0
        self.default_ttl = 0
        self.max_ttl = 0


class Logging:
    def __init__(self):
        self.enabled = False


class ViewerCertificate:
    def __init__(self):
        self.cloud_front_default_certificate = True
        self.min_protocol_version = "TLSv1"
        self.certificate_source = "cloudfront"


class Origin:
    def __init__(self, origin):
        self.id = origin["Id"]
        self.domain_name = origin["DomainName"]
        self.custom_headers = []
        self.s3_access_identity = ""
        self.custom_origin = None
        self.origin_shield = None
        self.connection_attempts = 3
        self.connection_timeout = 10

        if "S3OriginConfig" not in origin and "CustomOriginConfig" not in origin:
            raise InvalidOriginServer

        if "S3OriginConfig" in origin:
            # Very rough validation
            if not self.domain_name.endswith("amazonaws.com"):
                raise DomainNameNotAnS3Bucket
            self.s3_access_identity = origin["S3OriginConfig"]["OriginAccessIdentity"]


class DistributionConfig:
    def __init__(self, config):
        self.config = config
        self.aliases = config.get("Aliases", {}).get("Items", {}).get("CNAME", [])
        self.comment = config.get("Comment", "")
        self.default_cache_behavior = DefaultCacheBehaviour(
            config["DefaultCacheBehavior"]
        )
        self.cache_behaviors = []
        self.custom_error_responses = []
        self.logging = Logging()
        self.enabled = False
        self.viewer_certificate = ViewerCertificate()
        self.geo_restriction_type = "none"
        self.geo_restrictions = []
        self.caller_reference = config.get("CallerReference", str(uuid4()))
        self.origins = config["Origins"]["Items"]["Origin"]
        if not isinstance(self.origins, list):
            self.origins = [self.origins]

        # This check happens before any other Origins-validation
        if self.default_cache_behavior.target_origin_id not in [
            o["Id"] for o in self.origins
        ]:
            raise OriginDoesNotExist

        self.origins = [Origin(o) for o in self.origins]
        self.price_class = "PriceClass_All"
        self.http_version = "http2"
        self.is_ipv6_enabled = True


class Distribution(BaseModel):
    @staticmethod
    def random_id(uppercase=True):
        ascii_set = string.ascii_uppercase if uppercase else string.ascii_lowercase
        chars = list(range(10)) + list(ascii_set)
        resource_id = random.choice(ascii_set) + "".join(
            str(random.choice(chars)) for _ in range(12)
        )
        return resource_id

    def __init__(self, config):
        self.distribution_id = Distribution.random_id()
        self.arn = (
            f"arn:aws:cloudfront:{ACCOUNT_ID}:distribution/{self.distribution_id}"
        )
        self.distribution_config = DistributionConfig(config)
        self.active_trusted_signers = ActiveTrustedSigners()
        self.active_trusted_key_groups = ActiveTrustedKeyGroups()
        self.origin_groups = []
        self.alias_icp_recordals = []
        self.last_modified_time = "2021-11-27T10:34:26.802Z"
        self.in_progress_invalidation_batches = 0
        self.has_active_trusted_key_groups = False
        self.status = "InProgress"
        self.domain_name = f"{Distribution.random_id(uppercase=False)}.cloudfront.net"

    def advance(self):
        """
        Advance the status of this Distribution, to mimick AWS' behaviour
        """
        if self.status == "InProgress":
            self.status = "Deployed"

    @property
    def location(self):
        return f"https://cloudfront.amazonaws.com/2020-05-31/distribution/{self.distribution_id}"

    @property
    def etag(self):
        return Distribution.random_id()


class CloudFrontBackend(BaseBackend):
    def __init__(self):
        self.distributions = dict()

    def create_distribution(self, distribution_config):
        """
        This has been tested against an S3-distribution with the simplest possible configuration.
        Please raise an issue if we're not persisting/returning the correct attributes for your use-case.
        """
        dist = Distribution(distribution_config)
        caller_reference = dist.distribution_config.caller_reference
        existing_dist = self._distribution_with_caller_reference(caller_reference)
        if existing_dist:
            raise DistributionAlreadyExists(existing_dist.distribution_id)
        self.distributions[dist.distribution_id] = dist
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


cloudfront_backend = CloudFrontBackend()
