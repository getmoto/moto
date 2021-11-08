"""DirectoryServiceBackend class with methods for supported APIs."""
from datetime import datetime, timezone
import ipaddress

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core.utils import get_random_hex
from moto.ds.exceptions import (
    ClientException,
    DirectoryLimitExceededException,
    EntityAlreadyExistsException,
    EntityDoesNotExistException,
    InvalidParameterException,
    TagLimitExceededException,
    ValidationException,
)
from moto.ds.utils import PAGINATION_MODEL
from moto.ds.validations import (
    validate_args,
    validate_alias,
    validate_description,
    validate_directory_id,
    validate_dns_ips,
    validate_edition,
    validate_name,
    validate_password,
    validate_short_name,
    validate_size,
    validate_sso_password,
    validate_subnet_ids,
    validate_user_name,
)
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService


class Directory(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Representation of a Simple AD Directory.

    When the "create" API for a Simple AD or a Microsoft AD directory is
    invoked, two domain controllers and a DNS server are supposed to be
    created.  That is NOT done for the fake directories.

    However, the DnsIpAddrs attribute is supposed to contain the IP addresses
    of the DNS servers.  For a AD Connecter, the DnsIpAddrs are provided when
    the directory is created, but the ConnectSettings.ConnectIps values should
    contain the IP addresses of the DNS servers or domain controllers in the
    directory to which the AD connector is connected.

    Instead, the dns_ip_addrs attribute or ConnectIPs attribute for the fake
    directories will contain IPs picked from the subnets' CIDR blocks.
    """

    # The assumption here is that the limits are the same for all regions.
    CLOUDONLY_DIRECTORIES_LIMIT = 10
    CLOUDONLY_MICROSOFT_AD_LIMIT = 20
    CONNECTED_DIRECTORIES_LIMIT = 10

    MAX_TAGS_PER_DIRECTORY = 50

    def __init__(
        self,
        name,
        password,
        directory_type,
        subnets,
        size=None,
        vpc_settings=None,
        connect_settings=None,
        short_name=None,
        description=None,
        edition=None,
    ):  # pylint: disable=too-many-arguments
        self.name = name
        self.password = password
        self.directory_type = directory_type
        self.size = size
        self.vpc_settings = vpc_settings
        self.connect_settings = connect_settings
        self.short_name = short_name
        self.description = description
        self.edition = edition

        # Calculated or default values for the directory attributes.
        self.directory_id = f"d-{get_random_hex(10)}"
        self.access_url = f"{self.directory_id}.awsapps.com"
        self.alias = self.directory_id
        self.desired_number_of_domain_controllers = 0
        self.sso_enabled = False
        self.stage = "Active"
        self.launch_time = datetime.now(timezone.utc).isoformat()
        self.stage_last_updated_date_time = datetime.now(timezone.utc).isoformat()

        if directory_type != "ADConnector":
            self.dns_ip_addrs = self.subnet_ips(subnets)
        else:
            self.dns_ip_addrs = self.connect_settings["CustomerDnsIps"]
            self.connect_settings["ConnectIps"] = self.subnet_ips(subnets)

    @staticmethod
    def subnet_ips(subnets):
        """Return an IP from each of the given subnets.

        This is a bit dodgey and may need to be reworked at a later time.
        """
        ip_addrs = []
        for subnet in subnets:
            ips = ipaddress.ip_network(subnet.cidr_block)
            # Not sure if the following could occur, but if it does,
            # the situation will be ignored.
            if ips:
                ip_addrs.append(str(ips[1]) if ips.num_addresses > 1 else str(ips[0]))
        return ip_addrs

    def update_alias(self, alias):
        """Change default alias to given alias."""
        self.alias = alias
        self.access_url = f"{alias}.awsapps.com"

    def enable_sso(self, new_state):
        """Enable/disable sso based on whether new_state is True or False."""
        self.sso_enabled = new_state

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
                new_tag = "".join(x.title() for x in item.split("_"))
                json_result[new_tag] = value

        if json_result["ConnectSettings"]:
            json_result["ConnectSettings"]["CustomerDnsIps"] = None
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
    def _get_subnets(region, vpc_settings):
        """Return subnets if vpc_settings are invalid, else raise an exception.

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
        return subnets

    def connect_directory(
        self,
        region,
        name,
        short_name,
        password,
        description,
        size,
        connect_settings,
        tags,
    ):  # pylint: disable=too-many-arguments
        """Create a fake AD Connector."""
        if len(self.directories) > Directory.CONNECTED_DIRECTORIES_LIMIT:
            raise DirectoryLimitExceededException(
                f"Directory limit exceeded. A maximum of "
                f"{Directory.CONNECTED_DIRECTORIES_LIMIT} directories may be created"
            )

        validate_args(
            [
                (validate_password, "password", password),
                (validate_size, "size", size),
                (validate_name, "name", name),
                (validate_description, "description", description),
                (validate_short_name, "shortName", short_name),
                (
                    validate_subnet_ids,
                    "connectSettings.vpcSettings.subnetIds",
                    connect_settings["SubnetIds"],
                ),
                (
                    validate_user_name,
                    "connectSettings.customerUserName",
                    connect_settings["CustomerUserName"],
                ),
                (
                    validate_dns_ips,
                    "connectSettings.customerDnsIps",
                    connect_settings["CustomerDnsIps"],
                ),
            ]
        )
        # ConnectSettings and VpcSettings both have a VpcId and Subnets.
        subnets = self._get_subnets(region, connect_settings)

        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)
        if len(tags) > Directory.MAX_TAGS_PER_DIRECTORY:
            raise DirectoryLimitExceededException("Tag Limit is exceeding")

        directory = Directory(
            name,
            password,
            "ADConnector",
            subnets,
            size=size,
            connect_settings=connect_settings,
            short_name=short_name,
            description=description,
        )
        self.directories[directory.directory_id] = directory
        self.tagger.tag_resource(directory.directory_id, tags or [])
        return directory.directory_id

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
        validate_args(
            [
                (validate_password, "password", password),
                (validate_size, "size", size),
                (validate_name, "name", name),
                (validate_description, "description", description),
                (validate_short_name, "shortName", short_name),
                (
                    validate_subnet_ids,
                    "vpcSettings.subnetIds",
                    vpc_settings["SubnetIds"],
                ),
            ]
        )
        subnets = self._get_subnets(region, vpc_settings)

        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)
        if len(tags) > Directory.MAX_TAGS_PER_DIRECTORY:
            raise DirectoryLimitExceededException("Tag Limit is exceeding")

        directory = Directory(
            name,
            password,
            "SimpleAD",
            subnets,
            size=size,
            vpc_settings=vpc_settings,
            short_name=short_name,
            description=description,
        )
        self.directories[directory.directory_id] = directory
        self.tagger.tag_resource(directory.directory_id, tags or [])
        return directory.directory_id

    def _validate_directory_id(self, directory_id):
        """Raise an exception if the directory id is invalid or unknown."""
        # Validation of ID takes precedence over a check for its existence.
        validate_args([(validate_directory_id, "directoryId", directory_id)])
        if directory_id not in self.directories:
            raise EntityDoesNotExistException(
                f"Directory {directory_id} does not exist"
            )

    def create_alias(self, directory_id, alias):
        """Create and assign an alias to a directory."""
        self._validate_directory_id(directory_id)

        # The default alias name is the same as the directory name.  Check
        # whether this directory was already given an alias.
        directory = self.directories[directory_id]
        if directory.alias != directory_id:
            raise InvalidParameterException(
                "The directory in the request already has an alias. That "
                "alias must be deleted before a new alias can be created."
            )

        # Is the alias already in use?
        if alias in [x.alias for x in self.directories.values()]:
            raise EntityAlreadyExistsException(f"Alias '{alias}' already exists.")

        validate_args([(validate_alias, "alias", alias)])

        directory.update_alias(alias)
        return {"DirectoryId": directory_id, "Alias": alias}

    def create_microsoft_ad(
        self,
        region,
        name,
        short_name,
        password,
        description,
        vpc_settings,
        edition,
        tags,
    ):  # pylint: disable=too-many-arguments
        """Create a fake Microsoft Ad Directory."""
        if len(self.directories) > Directory.CLOUDONLY_MICROSOFT_AD_LIMIT:
            raise DirectoryLimitExceededException(
                f"Directory limit exceeded. A maximum of "
                f"{Directory.CLOUDONLY_MICROSOFT_AD_LIMIT} directories may be created"
            )

        # boto3 looks for missing vpc_settings for create_microsoft_ad().
        validate_args(
            [
                (validate_password, "password", password),
                (validate_edition, "edition", edition),
                (validate_name, "name", name),
                (validate_description, "description", description),
                (validate_short_name, "shortName", short_name),
                (
                    validate_subnet_ids,
                    "vpcSettings.subnetIds",
                    vpc_settings["SubnetIds"],
                ),
            ]
        )
        subnets = self._get_subnets(region, vpc_settings)

        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)
        if len(tags) > Directory.MAX_TAGS_PER_DIRECTORY:
            raise DirectoryLimitExceededException("Tag Limit is exceeding")

        directory = Directory(
            name,
            password,
            "MicrosoftAD",
            subnets,
            vpc_settings=vpc_settings,
            short_name=short_name,
            description=description,
            edition=edition,
        )
        self.directories[directory.directory_id] = directory
        self.tagger.tag_resource(directory.directory_id, tags or [])
        return directory.directory_id

    def delete_directory(self, directory_id):
        """Delete directory with the matching ID."""
        self._validate_directory_id(directory_id)
        self.tagger.delete_all_tags_for_resource(directory_id)
        self.directories.pop(directory_id)
        return directory_id

    def disable_sso(self, directory_id, username=None, password=None):
        """Disable single-sign on for a directory."""
        self._validate_directory_id(directory_id)
        validate_args(
            [
                (validate_sso_password, "password", password),
                (validate_user_name, "userName", username),
            ]
        )
        directory = self.directories[directory_id]
        directory.enable_sso(False)

    def enable_sso(self, directory_id, username=None, password=None):
        """Enable single-sign on for a directory."""
        self._validate_directory_id(directory_id)
        validate_args(
            [
                (validate_sso_password, "password", password),
                (validate_user_name, "userName", username),
            ]
        )

        directory = self.directories[directory_id]
        if directory.alias == directory_id:
            raise ClientException(
                f"An alias is required before enabling SSO. DomainId={directory_id}"
            )

        directory = self.directories[directory_id]
        directory.enable_sso(True)

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
