import base64
import hashlib
import json
from datetime import datetime, timedelta
from dateutil.tz import tzutc
from typing import Dict, Any, Optional, Union
from typing_extensions import Literal

from moto.core import BackendDict, BaseBackend, BaseModel


class BaseObject(BaseModel):
    def camelCase(self, key: str) -> str:
        words = []
        for word in key.split("_"):
            words.append(word.title())
        return "".join(words)

    def update(self, details_json: str) -> None:
        details = json.loads(details_json)
        for k in details.keys():
            setattr(self, k, details[k])

    def gen_response_object(self) -> Dict[str, Any]:
        response_object: Dict[str, Any] = dict()
        for key, value in self.__dict__.items():
            if "_" in key:
                response_object[self.camelCase(key)] = value
            else:
                response_object[key[0].upper() + key[1:]] = value
        return response_object

    @property
    def response_object(self) -> Dict[str, Any]:  # type: ignore[misc]
        return self.gen_response_object()


def hash_device_name(name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8")).digest()
    token = base64.b64encode(digest)
    return str(token)


class Device(BaseObject):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        description: Optional[str],
        name: str,
        network_configuration: Optional[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
    ) -> None:
        self.account_id = account_id
        self.region_name = region_name
        self.description = description
        self.name = name
        self.network_configuration = network_configuration
        self.tags = tags

        self.arn = (
            f"arn:aws:panorama:{self.region_name}:{self.account_id}:device/{self.name}"
        )
        self.device_id = f"device-{hash_device_name(name)}"
        self.iot_thing_name = ""

        self.alternate_softwares = [
            {"Version": "0.2.1"},
        ]
        self.brand: Literal["AWS_PANORAMA", "LENOVO"] = "AWS_PANORAMA"
        self.created_time = datetime.now(tzutc())
        self.current_networking_status = {
            "Ethernet0Status": {
                "ConnectionStatus": "CONNECTED",
                "HwAddress": "8C:0F:5F:60:F5:C4",
                "IpAddress": "192.168.1.300/24",
            },
            "Ethernet1Status": {
                "ConnectionStatus": "NOT_CONNECTED",
                "HwAddress": "8C:0F:6F:60:F4:F1",
                "IpAddress": "--",
            },
            "LastUpdatedTime": datetime.now(tzutc()),
            "NtpStatus": {
                "ConnectionStatus": "CONNECTED",
                "IpAddress": "91.224.149.41:123",
                "NtpServerName": "0.pool.ntp.org",
            },
        }
        self.current_software = "6.2.1"
        self.device_aggregated_status: Literal[
            "ERROR",
            "AWAITING_PROVISIONING",
            "PENDING",
            "FAILED",
            "DELETING",
            "ONLINE",
            "OFFLINE",
            "LEASE_EXPIRED",
            "UPDATE_NEEDED",
            "REBOOTING",
        ] = "ONLINE"
        self.device_connection_status: Literal[
            "ONLINE", "OFFLINE", "AWAITING_CREDENTIALS", "NOT_AVAILABLE", "ERROR"
        ] = "ONLINE"
        self.latest_device_job = {"JobType": "REBOOT", "Status": "COMPLETED"}
        self.latest_software = "6.2.1"
        self.lease_expiration_time = datetime.now(tzutc()) + timedelta(days=5)
        self.serial_number = "GAD81E29013274749"
        self.type: Literal[
            "PANORAMA_APPLIANCE_DEVELOPER_KIT", "PANORAMA_APPLIANCE"
        ] = "PANORAMA_APPLIANCE"

    @property
    def response_provision(self) -> Dict[str, Union[str, bytes]]:
        return {
            "Arn": self.arn,
            "Certificates": b"bytes",
            "DeviceId": self.device_id,
            "IotThingName": self.iot_thing_name,
            "Status": "AWAITING_PROVISIONING",
        }


class ApplicationInstance(BaseObject):
    pass


class PanoramaBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.devices_memory: Dict[str, Device] = {}
        self.application_instances: Dict[str, ApplicationInstance] = {}

    def provision_device(
        self,
        description: Optional[str],
        name: str,
        networking_configuration: Optional[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
    ) -> Device:
        device_obj = Device(
            account_id=self.account_id,
            region_name=self.region_name,
            description=description,
            name=name,
            network_configuration=networking_configuration,
            tags=tags,
        )

        self.devices_memory[device_obj.device_id] = device_obj
        return device_obj

    def describe_device(self, device_id: str) -> Device:
        return self.devices_memory[device_id]


# panorama_backends = BackendDict(PanoramaBackend, "panorama", False, additional_regions=["us-east-1", "us-west-2", "ca-central-1", "eu-west-1", "ap-southeast-2", "ap-southeast-1"])
panorama_backends = BackendDict(PanoramaBackend, "panorama")
