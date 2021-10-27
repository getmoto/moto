"""DirectoryServiceBackend class with methods for supported APIs."""
import re

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core.utils import get_random_hex
from moto.ds.exceptions import (
    ClientException,
    # DirectoryLimitExceededException,
    DsValidationException,
    InvalidParameterException,
)
from moto.utilities.tagging_service import TaggingService


class Directory(BaseModel):
    """Representation of a Simple AD Directory."""

    def __init__(
        self, name, password, size, vpc_settings, short_name=None, description=None
    ):  # pylint: disable=too-many-arguments
        self.name = name
        self.password = password
        self.size = size
        self.vpc_settings = vpc_settings
        self.short_name = short_name
        self.description = description
        self.directory_id = f"d-{get_random_hex(10)}"


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
    def _validate_create_directory_args(name, passwd, size, vpc_settings):
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
                ("password", passwd, fr"regular expression pattern: {json_pattern}")
            )

        if size.lower() not in ["small", "large"]:
            error_tuples.append(("size", size, "enum value set: [Small, Large]"))

        name_pattern = r"^([a-zA-Z0-9]+[\\.-])+([a-zA-Z0-9])+$"
        if not re.match(name_pattern, name):
            error_tuples.append(
                ("name", name, fr"regular expression pattern: {name_pattern}")
            )

        subnet_id_pattern = r"^(subnet-[0-9a-f]{8}|subnet-[0-9a-f]{17})$"
        for subnet in vpc_settings["SubnetIds"]:
            if not re.match(subnet_id_pattern, subnet):
                error_tuples.append(
                    (
                        "vpcSettings.subnetIds",
                        subnet,
                        fr"regular expression pattern: {subnet_id_pattern}",
                    )
                )

        if error_tuples:
            raise DsValidationException(error_tuples)

    @staticmethod
    def _validate_vpc_setting_values(region, vpc_settings):
        """Raise exception if vpc_settings are invalid."""
        if len(vpc_settings["SubnetIds"]) != 2:
            raise InvalidParameterException(
                "Invalid subnet ID(s). They must correspond to two subnets "
                "in different Availability Zones."
            )

        from moto.ec2 import ec2_backends  # pylint: disable=import-outside-toplevel

        vpcs = ec2_backends[region].describe_vpcs()
        # NOTE:  moto currently doesn't suport EC2's describe_subnets().
        # Subnet IDs are checked before the VPC ID.  The Subnet IDs must
        # be valid and in different availability zones.
        # regions = []
        # found_ids = 0
        # for subnet in ec2_backends[region].describe_subnets():
        #    if subnet.subnet_id in vpc_settings["SubnetIds"]:
        #        found_id += 1
        #        regions.append(subnet.availability_zone)
        # if found_ids != len(vpc_settings["SubnetIds"]):
        #     raise ClientException("Invalid subnet ID(s).")
        # if len(regions) != len(vpc_settings["SubnetIds"]):
        #     raise ClientException(
        #         "Invalid subnet ID(s). The two subnets must be in "
        #         "different Availabilty Zones."
        #     )

        if vpc_settings["VpcId"] not in [x.id for x in vpcs]:
            raise ClientException("Invalid VPC ID.")

    def create_directory(
        self, region, name, short_name, password, description, size, vpc_settings, tags
    ):  # pylint: disable=too-many-arguments
        """Create a fake Simple Ad Directory."""
        # botocore doesn't look for missing vpc_settings, but boto3 does.
        if not vpc_settings:
            raise InvalidParameterException("VpcSettings must be specified.")

        self._validate_create_directory_args(name, password, size, vpc_settings)
        self._validate_vpc_setting_values(region, vpc_settings)

        # TODO DirectoryLimitExceededException,

        directory = Directory(
            name,
            password,
            size,
            vpc_settings,
            short_name=short_name,
            description=description,
        )
        self.directories[directory.directory_id] = directory

        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise DsValidationException(errmsg)
        self.tagger.tag_resource(directory.directory_id, tags or [])

        return directory.directory_id

    def delete_directory(self, directory_id):
        """Delete directory with the matching ID."""
        # self.tagger.delete_all_tags_for_resource(directory.directory_id)
        pass

    def describe_directories(self, directory_ids, next_token, limit):
        """Return info on all directories or directories with matching IDs."""
        pass

    def get_directory_limits(self):
        """Return directory limit informatio for current region.

        For moto, this is fixed data.
        """
        pass


ds_backends = {}
for available_region in Session().get_available_regions("ds"):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
for available_region in Session().get_available_regions(
    "ds", partition_name="aws-us-gov"
):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
for available_region in Session().get_available_regions("ds", partition_name="aws-cn"):
    ds_backends[available_region] = DirectoryServiceBackend(available_region)
