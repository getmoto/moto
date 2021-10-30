"""DirectoryServiceBackend class with methods for supported APIs."""
from datetime import datetime, timezone
import re

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core.utils import get_random_hex
from moto.ds.exceptions import (
    ClientException,
    DirectoryLimitExceededException,
    EntityDoesNotExistException,
    DsValidationException,
    InvalidParameterException,
    TagLimitExceededException,
    ValidationException,
)
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService
from .utils import PAGINATION_MODEL


class Directory(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Representation of a Simple AD Directory."""

    # The assumption here is that the limits are the same for all regions.
    CLOUDONLY_DIRECTORIES_LIMIT = 10
    CLOUDONLY_MICROSOFT_AD_LIMIT = 20
    CONNECTED_DIRECTORIES_LIMIT = 10

    MAX_TAGS_PER_DIRECTORY = 50

    def __init__(
        self,
        name,
        password,
        size,
        vpc_settings,
        directory_type,
        short_name=None,
        description=None,
    ):  # pylint: disable=too-many-arguments
        self.name = name
        self.password = password
        self.size = size
        self.vpc_settings = vpc_settings
        self.directory_type = directory_type
        self.short_name = short_name
        self.description = description

        # Calculated or default values for the directory attributes.
        self.directory_id = f"d-{get_random_hex(10)}"
        self.access_url = f"{self.directory_id}.awsapps.com"
        self.alias = self.directory_id
        self.desired_number_of_domain_controllers = 0
        self.sso_enabled = False
        self.stage = "Active"
        self.launch_time = datetime.now(timezone.utc).isoformat()
        self.stage_last_updated_date_time = datetime.now(timezone.utc).isoformat()

    def to_json(self):
        """Convert the attributes into json with CamelCase tags."""
        replacement_keys = {"directory_type": "Type"}
        exclude_items = ["password"]

        json_result = {}
        for item, value in self.__dict__.items():
            # Discard empty strings, but allow values set to False or zero.
            if value == "" or item in exclude_items:
                continue

            if item in replacement_keys:
                json_result[replacement_keys[item]] = value
            else:
                parts = item.split("_")
                new_tag = "".join(x.title() for x in parts)
                json_result[new_tag] = value
        return json_result


class DirectoryServiceBackend(BaseBackend):
    """Implementation of DirectoryService APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.directories = {}
        self.tagger = TaggingService()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """List of dicts representing default VPC endpoints for this service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ds"
        )

    @staticmethod
    def _validate_create_directory_args(
        name, passwd, size, vpc_settings, description, short_name,
    ):  # pylint: disable=too-many-arguments
        """Raise exception if create_directory() args don't meet constraints.

        The error messages are accumulated before the exception is raised.
        """
        error_tuples = []
        passwd_pattern = (
            r"(?=^.{8,64}$)((?=.*\d)(?=.*[A-Z])(?=.*[a-z])|"
            r"(?=.*\d)(?=.*[^A-Za-z0-9\s])(?=.*[a-z])|"
            r"(?=.*[^A-Za-z0-9\s])(?=.*[A-Z])(?=.*[a-z])|"
            r"(?=.*\d)(?=.*[A-Z])(?=.*[^A-Za-z0-9\s]))^.*"
        )
        if not re.match(passwd_pattern, passwd):
            # Can't have an odd number of backslashes in a literal.
            json_pattern = passwd_pattern.replace("\\", r"\\")
            error_tuples.append(
                (
                    "password",
                    passwd,
                    fr"satisfy regular expression pattern: {json_pattern}",
                )
            )

        if size.lower() not in ["small", "large"]:
            error_tuples.append(
                ("size", size, "satisfy enum value set: [Small, Large]")
            )

        name_pattern = r"^([a-zA-Z0-9]+[\\.-])+([a-zA-Z0-9])+$"
        if not re.match(name_pattern, name):
            error_tuples.append(
                ("name", name, fr"satisfy regular expression pattern: {name_pattern}")
            )

        subnet_id_pattern = r"^(subnet-[0-9a-f]{8}|subnet-[0-9a-f]{17})$"
        for subnet in vpc_settings["SubnetIds"]:
            if not re.match(subnet_id_pattern, subnet):
                error_tuples.append(
                    (
                        "vpcSettings.subnetIds",
                        subnet,
                        fr"satisfy regular expression pattern: {subnet_id_pattern}",
                    )
                )

        if description and len(description) > 128:
            error_tuples.append(
                ("description", description, "have length less than or equal to 128")
            )

        short_name_pattern = r'^[^\/:*?"<>|.]+[^\/:*?"<>|]*$'
        if short_name and not re.match(short_name_pattern, short_name):
            json_pattern = short_name_pattern.replace("\\", r"\\").replace('"', r"\"")
            error_tuples.append(
                (
                    "shortName",
                    short_name,
                    fr"satisfy regular expression pattern: {json_pattern}",
                )
            )

        if error_tuples:
            raise DsValidationException(error_tuples)

    @staticmethod
    def _validate_vpc_setting_values(region, vpc_settings):
        """Raise exception if vpc_settings are invalid.

        If settings are valid, add AvailabilityZones to vpc_settings.
        """
        if len(vpc_settings["SubnetIds"]) != 2:
            raise InvalidParameterException(
                "Invalid subnet ID(s). They must correspond to two subnets "
                "in different Availability Zones."
            )

        from moto.ec2 import ec2_backends  # pylint: disable=import-outside-toplevel

        # Subnet IDs are checked before the VPC ID.  The Subnet IDs must
        # be valid and in different availability zones.
        try:
            subnets = ec2_backends[region].get_all_subnets(
                subnet_ids=vpc_settings["SubnetIds"]
            )
        except InvalidSubnetIdError as exc:
            raise InvalidParameterException(
                "Invalid subnet ID(s). They must correspond to two subnets "
                "in different Availability Zones."
            ) from exc

        regions = [subnet.availability_zone for subnet in subnets]
        if regions[0] == regions[1]:
            raise ClientException(
                "Invalid subnet ID(s). The two subnets must be in "
                "different Availability Zones."
            )

        vpcs = ec2_backends[region].describe_vpcs()
        if vpc_settings["VpcId"] not in [x.id for x in vpcs]:
            raise ClientException("Invalid VPC ID.")

        vpc_settings["AvailabilityZones"] = regions

    def create_directory(
        self, region, name, short_name, password, description, size, vpc_settings, tags
    ):  # pylint: disable=too-many-arguments
        """Create a fake Simple Ad Directory."""
        if len(self.directories) > Directory.CLOUDONLY_DIRECTORIES_LIMIT:
            raise DirectoryLimitExceededException(
                f"Directory limit exceeded. A maximum of "
                f"{Directory.CLOUDONLY_DIRECTORIES_LIMIT} directories may be created"
            )

        # botocore doesn't look for missing vpc_settings, but boto3 does.
        if not vpc_settings:
            raise InvalidParameterException("VpcSettings must be specified.")

        self._validate_create_directory_args(
            name, password, size, vpc_settings, description, short_name,
        )
        self._validate_vpc_setting_values(region, vpc_settings)

        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)

        if len(tags) > Directory.MAX_TAGS_PER_DIRECTORY:
            raise DirectoryLimitExceededException("Tag Limit is exceeding")

        directory = Directory(
            name,
            password,
            size,
            vpc_settings,
            directory_type="SimpleAD",
            short_name=short_name,
            description=description,
        )
        self.directories[directory.directory_id] = directory
        self.tagger.tag_resource(directory.directory_id, tags or [])
        return directory.directory_id

    def _validate_directory_id(self, directory_id):
        """Raise an exception if the directory id is invalid or unknown."""
        # Validation of ID takes precedence over a check for its existence.
        id_pattern = r"^d-[0-9a-f]{10}$"
        if not re.match(id_pattern, directory_id):
            raise DsValidationException(
                [
                    (
                        "directoryId",
                        directory_id,
                        fr"satisfy regular expression pattern: {id_pattern}",
                    )
                ]
            )

        if directory_id not in self.directories:
            raise EntityDoesNotExistException(
                f"Directory {directory_id} does not exist"
            )

    def delete_directory(self, directory_id):
        """Delete directory with the matching ID."""
        self._validate_directory_id(directory_id)
        self.tagger.delete_all_tags_for_resource(directory_id)
        self.directories.pop(directory_id)
        return directory_id

    @paginate(pagination_model=PAGINATION_MODEL)
    def describe_directories(
        self, directory_ids=None, next_token=None, limit=0
    ):  # pylint: disable=unused-argument
        """Return info on all directories or directories with matching IDs."""
        for directory_id in directory_ids or self.directories:
            self._validate_directory_id(directory_id)

        directories = list(self.directories.values())
        if directory_ids:
            directories = [x for x in directories if x.directory_id in directory_ids]
        return sorted(directories, key=lambda x: x.launch_time)

    def get_directory_limits(self):
        """Return hard-coded limits for the directories."""
        counts = {"SimpleAD": 0, "MicrosoftAD": 0, "ConnectedAD": 0}
        for directory in self.directories.values():
            if directory.directory_type == "SimpleAD":
                counts["SimpleAD"] += 1
            elif directory.directory_type in ["MicrosoftAD", "SharedMicrosoftAD"]:
                counts["MicrosoftAD"] += 1
            elif directory.directory_type == "ADConnector":
                counts["ConnectedAD"] += 1

        return {
            "CloudOnlyDirectoriesLimit": Directory.CLOUDONLY_DIRECTORIES_LIMIT,
            "CloudOnlyDirectoriesCurrentCount": counts["SimpleAD"],
            "CloudOnlyDirectoriesLimitReached": counts["SimpleAD"]
            == Directory.CLOUDONLY_DIRECTORIES_LIMIT,
            "CloudOnlyMicrosoftADLimit": Directory.CLOUDONLY_MICROSOFT_AD_LIMIT,
            "CloudOnlyMicrosoftADCurrentCount": counts["MicrosoftAD"],
            "CloudOnlyMicrosoftADLimitReached": counts["MicrosoftAD"]
            == Directory.CLOUDONLY_MICROSOFT_AD_LIMIT,
            "ConnectedDirectoriesLimit": Directory.CONNECTED_DIRECTORIES_LIMIT,
            "ConnectedDirectoriesCurrentCount": counts["ConnectedAD"],
            "ConnectedDirectoriesLimitReached": counts["ConnectedAD"]
            == Directory.CONNECTED_DIRECTORIES_LIMIT,
        }

    def add_tags_to_resource(self, resource_id, tags):
        """Add or overwrite one or more tags for specified directory."""
        self._validate_directory_id(resource_id)
        errmsg = self.tagger.validate_tags(tags)
        if errmsg:
            raise ValidationException(errmsg)
        if len(tags) > Directory.MAX_TAGS_PER_DIRECTORY:
            raise TagLimitExceededException("Tag limit exceeded")
        self.tagger.tag_resource(resource_id, tags)

    def remove_tags_from_resource(self, resource_id, tag_keys):
        """Removes tags from a directory."""
        self._validate_directory_id(resource_id)
        self.tagger.untag_resource_using_names(resource_id, tag_keys)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_tags_for_resource(
        self, resource_id, next_token=None, limit=None,
    ):  # pylint: disable=unused-argument
        """List all tags on a directory."""
        self._validate_directory_id(resource_id)
        return self.tagger.list_tags_for_resource(resource_id).get("Tags")


ds_backends = {}
for available_region in Session().get_available_regions("ds"):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
for available_region in Session().get_available_regions(
    "ds", partition_name="aws-us-gov"
):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
for available_region in Session().get_available_regions("ds", partition_name="aws-cn"):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
