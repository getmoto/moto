"""Handles incoming networkmanager requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import (
    CoreNetwork,
    Device,
    GlobalNetwork,
    Link,
    NetworkManagerBackend,
    Site,
    networkmanager_backends,
)


def _global_network(global_network: GlobalNetwork) -> dict[str, Any]:
    return {
        "GlobalNetworkId": global_network.global_network_id,
        "GlobalNetworkArn": global_network.global_network_arn,
        "Description": global_network.description,
        "Tags": global_network.tags,
        "State": global_network.state,
        "CreatedAt": global_network.created_at,
    }


def _core_network(core_network: CoreNetwork) -> dict[str, Any]:
    # Serves both the CoreNetwork and CoreNetworkSummary shapes.
    return {
        "CoreNetworkId": core_network.core_network_id,
        "CoreNetworkArn": core_network.core_network_arn,
        "GlobalNetworkId": core_network.global_network_id,
        "OwnerAccountId": core_network.owner_account_id,
        "Description": core_network.description,
        "Tags": core_network.tags,
        "State": core_network.state,
        "CreatedAt": core_network.created_at,
    }


def _site(site: Site) -> dict[str, Any]:
    return {
        "SiteId": site.site_id,
        "SiteArn": site.site_arn,
        "GlobalNetworkId": site.global_network_id,
        "Description": site.description,
        "Location": site.location,
        "Tags": site.tags,
        "State": site.state,
        "CreatedAt": site.created_at,
    }


def _link(link: Link) -> dict[str, Any]:
    return {
        "LinkId": link.link_id,
        "LinkArn": link.link_arn,
        "GlobalNetworkId": link.global_network_id,
        "Description": link.description,
        "Type": link.type,
        "Bandwidth": link.bandwidth,
        "Provider": link.provider,
        "SiteId": link.site_id,
        "Tags": link.tags,
        "State": link.state,
        "CreatedAt": link.created_at,
    }


def _device(device: Device) -> dict[str, Any]:
    return {
        "DeviceId": device.device_id,
        "DeviceArn": device.device_arn,
        "GlobalNetworkId": device.global_network_id,
        "AWSLocation": device.aws_location,
        "Description": device.description,
        "Type": device.type,
        "Vendor": device.vendor,
        "Model": device.model,
        "SerialNumber": device.serial_number,
        "Location": device.location,
        "SiteId": device.site_id,
        "Tags": device.tags,
        "State": device.state,
        "CreatedAt": device.created_at,
    }


class NetworkManagerResponse(BaseResponse):
    """Handler for NetworkManager requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="networkmanager")
        self.automated_parameter_parsing = True

    @property
    def networkmanager_backend(self) -> NetworkManagerBackend:
        return networkmanager_backends[self.current_account][self.partition]

    def create_global_network(self) -> ActionResult:
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        global_network = self.networkmanager_backend.create_global_network(
            description=description,
            tags=tags,
        )
        result = {"GlobalNetwork": _global_network(global_network)}
        self.networkmanager_backend.update_resource_state(
            global_network.global_network_arn, "AVAILABLE"
        )
        return ActionResult(result)

    def create_core_network(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        policy_document = self._get_param("PolicyDocument")
        client_token = self._get_param("ClientToken")
        core_network = self.networkmanager_backend.create_core_network(
            global_network_id=global_network_id,
            description=description,
            tags=tags,
            policy_document=policy_document,
            client_token=client_token,
        )
        result = {"CoreNetwork": _core_network(core_network)}
        self.networkmanager_backend.update_resource_state(
            core_network.core_network_arn, "AVAILABLE"
        )
        return ActionResult(result)

    def delete_core_network(self) -> ActionResult:
        core_network_id = self._get_param("CoreNetworkId")
        core_network = self.networkmanager_backend.delete_core_network(
            core_network_id=core_network_id,
        )
        return ActionResult({"CoreNetwork": _core_network(core_network)})

    def tag_resource(self) -> EmptyResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.networkmanager_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return EmptyResult()

    def untag_resource(self) -> EmptyResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.networkmanager_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return EmptyResult()

    def list_core_networks(self) -> ActionResult:
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        core_networks, next_token = self.networkmanager_backend.list_core_networks(
            max_results=max_results,
            next_token=next_token,
        )
        result = {
            "CoreNetworks": [_core_network(cn) for cn in core_networks],
            "NextToken": next_token,
        }
        return ActionResult(result)

    def get_core_network(self) -> ActionResult:
        core_network_id = self._get_param("CoreNetworkId")
        core_network = self.networkmanager_backend.get_core_network(
            core_network_id=core_network_id,
        )
        return ActionResult({"CoreNetwork": _core_network(core_network)})

    def describe_global_networks(self) -> ActionResult:
        global_network_ids = self._get_param("GlobalNetworkIds")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        global_networks, next_token = (
            self.networkmanager_backend.describe_global_networks(
                global_network_ids=global_network_ids,
                max_results=max_results,
                next_token=next_token,
            )
        )
        result = {
            "GlobalNetworks": [_global_network(gn) for gn in global_networks],
            "NextToken": next_token,
        }
        return ActionResult(result)

    def create_site(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        description = self._get_param("Description")
        location = self._get_param("Location")
        tags = self._get_param("Tags")
        site = self.networkmanager_backend.create_site(
            global_network_id=global_network_id,
            description=description,
            location=location,
            tags=tags,
        )
        result = {"Site": _site(site)}
        self.networkmanager_backend.update_resource_state(site.site_arn, "AVAILABLE")
        return ActionResult(result)

    def delete_site(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        site_id = self._get_param("SiteId")
        site = self.networkmanager_backend.delete_site(
            global_network_id=global_network_id,
            site_id=site_id,
        )
        return ActionResult({"Site": _site(site)})

    def get_sites(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        site_ids = self._get_param("SiteIds")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        sites, next_token = self.networkmanager_backend.get_sites(
            global_network_id=global_network_id,
            site_ids=site_ids,
            max_results=max_results,
            next_token=next_token,
        )
        result = {"Sites": [_site(site) for site in sites], "NextToken": next_token}
        return ActionResult(result)

    def create_link(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        description = self._get_param("Description")
        type = self._get_param("Type")
        bandwidth = self._get_param("Bandwidth")
        provider = self._get_param("Provider")
        site_id = self._get_param("SiteId")
        tags = self._get_param("Tags")
        link = self.networkmanager_backend.create_link(
            global_network_id=global_network_id,
            description=description,
            type=type,
            bandwidth=bandwidth,
            provider=provider,
            site_id=site_id,
            tags=tags,
        )
        result = {"Link": _link(link)}
        self.networkmanager_backend.update_resource_state(link.link_arn, "AVAILABLE")
        return ActionResult(result)

    def get_links(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        link_ids = self._get_param("LinkIds")
        site_id = self._get_param("SiteId")
        type = self._get_param("Type")
        provider = self._get_param("Provider")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        links, next_token = self.networkmanager_backend.get_links(
            global_network_id=global_network_id,
            link_ids=link_ids,
            site_id=site_id,
            type=type,
            provider=provider,
            max_results=max_results,
            next_token=next_token,
        )
        result = {"Links": [_link(link) for link in links], "NextToken": next_token}
        return ActionResult(result)

    def delete_link(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        link_id = self._get_param("LinkId")
        link = self.networkmanager_backend.delete_link(
            global_network_id=global_network_id,
            link_id=link_id,
        )
        return ActionResult({"Link": _link(link)})

    def create_device(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        aws_location = self._get_param("AWSLocation")
        description = self._get_param("Description")
        type = self._get_param("Type")
        vendor = self._get_param("Vendor")
        model = self._get_param("Model")
        serial_number = self._get_param("SerialNumber")
        location = self._get_param("Location")
        site_id = self._get_param("SiteId")
        tags = self._get_param("Tags")
        device = self.networkmanager_backend.create_device(
            global_network_id=global_network_id,
            aws_location=aws_location,
            description=description,
            type=type,
            vendor=vendor,
            model=model,
            serial_number=serial_number,
            location=location,
            site_id=site_id,
            tags=tags,
        )
        result = {"Device": _device(device)}
        self.networkmanager_backend.update_resource_state(
            device.device_arn, "AVAILABLE"
        )
        return ActionResult(result)

    def get_devices(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        device_ids = self._get_param("DeviceIds")
        site_id = self._get_param("SiteId")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        devices, next_token = self.networkmanager_backend.get_devices(
            global_network_id=global_network_id,
            device_ids=device_ids,
            site_id=site_id,
            max_results=max_results,
            next_token=next_token,
        )
        result = {
            "Devices": [_device(device) for device in devices],
            "NextToken": next_token,
        }
        return ActionResult(result)

    def delete_device(self) -> ActionResult:
        global_network_id = self._get_param("GlobalNetworkId")
        device_id = self._get_param("DeviceId")
        device = self.networkmanager_backend.delete_device(
            global_network_id=global_network_id,
            device_id=device_id,
        )
        return ActionResult({"Device": _device(device)})

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_list = self.networkmanager_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return ActionResult({"TagList": tag_list})
