import datetime
import json
import time

from boto3 import Session

from moto.core.exceptions import InvalidNextTokenException
from moto.core.models import ConfigQueryModel
from moto.s3 import s3_backends
from moto.s3.models import get_moto_s3_account_id


class S3ConfigQuery(ConfigQueryModel):
    def list_config_service_resources(
        self,
        resource_ids,
        resource_name,
        limit,
        next_token,
        backend_region=None,
        resource_region=None,
    ):
        # The resource_region only matters for aggregated queries as you can filter on bucket regions for them.
        # For other resource types, you would need to iterate appropriately for the backend_region.

        # Resource IDs are the same as S3 bucket names
        # For aggregation -- did we get both a resource ID and a resource name?
        if resource_ids and resource_name:
            # If the values are different, then return an empty list:
            if resource_name not in resource_ids:
                return [], None

        # If no filter was passed in for resource names/ids then return them all:
        if not resource_ids and not resource_name:
            bucket_list = list(self.backends["global"].buckets.keys())

        else:
            # Match the resource name / ID:
            bucket_list = []
            filter_buckets = [resource_name] if resource_name else resource_ids

            for bucket in self.backends["global"].buckets.keys():
                if bucket in filter_buckets:
                    bucket_list.append(bucket)

        # Filter on the proper region if supplied:
        region_filter = backend_region or resource_region
        if region_filter:
            region_buckets = []

            for bucket in bucket_list:
                if self.backends["global"].buckets[bucket].region_name == region_filter:
                    region_buckets.append(bucket)

            bucket_list = region_buckets

        if not bucket_list:
            return [], None

        # Pagination logic:
        sorted_buckets = sorted(bucket_list)
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            # Tokens for this moto feature is just the bucket name:
            # For OTHER non-global resource types, it's the region concatenated with the resource ID.
            if next_token not in sorted_buckets:
                raise InvalidNextTokenException()

            start = sorted_buckets.index(next_token)

        # Get the list of items to collect:
        bucket_list = sorted_buckets[start : (start + limit)]

        if len(sorted_buckets) > (start + limit):
            new_token = sorted_buckets[start + limit]

        return (
            [
                {
                    "type": "AWS::S3::Bucket",
                    "id": bucket,
                    "name": bucket,
                    "region": self.backends["global"].buckets[bucket].region_name,
                }
                for bucket in bucket_list
            ],
            new_token,
        )

    def get_config_resource(
        self, resource_id, resource_name=None, backend_region=None, resource_region=None
    ):
        # Get the bucket:
        bucket = self.backends["global"].buckets.get(resource_id, {})

        if not bucket:
            return

        # Are we filtering based on region?
        region_filter = backend_region or resource_region
        if region_filter and bucket.region_name != region_filter:
            return

        # Are we also filtering on bucket name?
        if resource_name and bucket.name != resource_name:
            return

        # Format the bucket to the AWS Config format:
        config_data = bucket.to_config_dict()

        # The 'configuration' field is also a JSON string:
        config_data["configuration"] = json.dumps(config_data["configuration"])

        # Supplementary config need all values converted to JSON strings if they are not strings already:
        for field, value in config_data["supplementaryConfiguration"].items():
            if not isinstance(value, str):
                config_data["supplementaryConfiguration"][field] = json.dumps(value)

        return config_data


class S3AccountPublicAccessBlockConfigQuery(ConfigQueryModel):
    def list_config_service_resources(
        self,
        resource_ids,
        resource_name,
        limit,
        next_token,
        backend_region=None,
        resource_region=None,
    ):
        # For the Account Public Access Block, they are the same for all regions. The resource ID is the AWS account ID
        # There is no resource name -- it should be a blank string "" if provided.

        # The resource name can only ever be None or an empty string:
        if resource_name is not None and resource_name != "":
            return [], None

        pab = None
        account_id = get_moto_s3_account_id()
        regions = [region for region in Session().get_available_regions("config")]

        # If a resource ID was passed in, then filter accordingly:
        if resource_ids:
            for id in resource_ids:
                if account_id == id:
                    pab = self.backends["global"].account_public_access_block
                    break

        # Otherwise, just grab the one from the backend:
        if not resource_ids:
            pab = self.backends["global"].account_public_access_block

        # If it's not present, then return nothing
        if not pab:
            return [], None

        # Filter on regions (and paginate on them as well):
        if backend_region:
            pab_list = [backend_region]
        elif resource_region:
            # Invalid region?
            if resource_region not in regions:
                return [], None

            pab_list = [resource_region]

        # Aggregated query where no regions were supplied so return them all:
        else:
            pab_list = regions

        # Pagination logic:
        sorted_regions = sorted(pab_list)
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            # Tokens for this moto feature is just the region-name:
            # For OTHER non-global resource types, it's the region concatenated with the resource ID.
            if next_token not in sorted_regions:
                raise InvalidNextTokenException()

            start = sorted_regions.index(next_token)

        # Get the list of items to collect:
        pab_list = sorted_regions[start : (start + limit)]

        if len(sorted_regions) > (start + limit):
            new_token = sorted_regions[start + limit]

        return (
            [
                {
                    "type": "AWS::S3::AccountPublicAccessBlock",
                    "id": account_id,
                    "region": region,
                }
                for region in pab_list
            ],
            new_token,
        )

    def get_config_resource(
        self, resource_id, resource_name=None, backend_region=None, resource_region=None
    ):
        # Do we even have this defined?
        if not self.backends["global"].account_public_access_block:
            return None

        # Resource name can only ever be "" if it's supplied:
        if resource_name is not None and resource_name != "":
            return None

        # Are we filtering based on region?
        account_id = get_moto_s3_account_id()
        regions = [region for region in Session().get_available_regions("config")]

        # Is the resource ID correct?:
        if account_id == resource_id:
            if backend_region:
                pab_region = backend_region

            # Invalid region?
            elif resource_region not in regions:
                return None

            else:
                pab_region = resource_region

        else:
            return None

        # Format the PAB to the AWS Config format:
        creation_time = datetime.datetime.utcnow()
        config_data = {
            "version": "1.3",
            "accountId": account_id,
            "configurationItemCaptureTime": str(creation_time),
            "configurationItemStatus": "OK",
            "configurationStateId": str(
                int(time.mktime(creation_time.timetuple()))
            ),  # PY2 and 3 compatible
            "resourceType": "AWS::S3::AccountPublicAccessBlock",
            "resourceId": account_id,
            "awsRegion": pab_region,
            "availabilityZone": "Not Applicable",
            "configuration": self.backends[
                "global"
            ].account_public_access_block.to_config_dict(),
            "supplementaryConfiguration": {},
        }

        # The 'configuration' field is also a JSON string:
        config_data["configuration"] = json.dumps(config_data["configuration"])

        return config_data


s3_config_query = S3ConfigQuery(s3_backends)
s3_account_public_access_block_query = S3AccountPublicAccessBlockConfigQuery(
    s3_backends
)
