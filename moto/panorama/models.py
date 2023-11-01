import base64
import json
from datetime import datetime, timedelta
from dateutil.tz import tzutc
from typing import Dict, Any, Optional, Union, List
from typing_extensions import Literal, cast

from moto.core import BackendDict, BaseBackend, BaseModel
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.panorama.type import DEVICE_AGGREGATED_STATUS_TYPE, PROVISIONING_STATUS_TYPE
from moto.panorama.utils import deep_convert_datetime_to_isoformat, hash_device_name
from moto.utilities.paginator import paginate

PAGINATION_MODEL = {
    "list_devices": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 123,
        "unique_attribute": "device_id",
    },
}


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

    def response_object(self) -> Dict[str, Any]:  # type: ignore[misc]
        return self.gen_response_object()


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
        self.__device_aggregated_status_manager = ManagedState(
            model_name=f"panorama::device_{name}_aggregated_status",
            transitions=[
                ("AWAITING_PROVISIONING", "PENDING"),
                ("PENDING", "ONLINE")
            ],
        )
        self.__device_provisioning_status_manager = ManagedState(
            model_name=f"panorama::device_{name}_provisioning_status",
            transitions=[
                ("AWAITING_PROVISIONING", "PENDING"),
                ("PENDING", "SUCCEEDED")
            ],
        )
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
        self.last_updated_time = datetime.now(tzutc())
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
    def device_aggregated_status(self) -> DEVICE_AGGREGATED_STATUS_TYPE:
        _device_aggregated_status = cast(DEVICE_AGGREGATED_STATUS_TYPE, self.__device_aggregated_status_manager.status)
        self.__device_aggregated_status_manager.advance()
        return _device_aggregated_status

    @property
    def provisioning_status(self) -> PROVISIONING_STATUS_TYPE:
        _provisioning_status = cast(PROVISIONING_STATUS_TYPE, self.__device_provisioning_status_manager.status)
        self.__device_provisioning_status_manager.advance()
        return _provisioning_status

    def response_object(self) -> Dict[str, Any]:
        response_object = super().gen_response_object()
        response_object = deep_convert_datetime_to_isoformat(response_object)
        static_response_fields = [
            "AlternateSoftwares",
            "Arn",
            "Brand",
            "CreatedTime",
            "CurrentNetworkingStatus",
            "CurrentSoftware",
            "Description",
            "DeviceConnectionStatus",
            "DeviceId",
            "LatestAlternateSoftware",
            "LatestDeviceJob",
            "LatestSoftware",
            "LeaseExpirationTime",
            "Name",
            "NetworkConfiguration",
            "SerialNumber",
            "Tags",
            "Type",
        ]
        return {
            **{k: v for k, v in response_object.items() if v is not None and k in static_response_fields},
            **{
                "DeviceAggregatedStatus": self.device_aggregated_status,
                "ProvisioningStatus": self.provisioning_status,
            }
        }

    @property
    def response_listed(self) -> Dict[str, Any]:
        response_object = super().gen_response_object()
        response_object = deep_convert_datetime_to_isoformat(response_object)
        static_response_fields = [
            "Brand",
            "CreatedTime",
            "CurrentSoftware",
            "Description",
            "DeviceId",
            "LastUpdatedTime",
            "LatestDeviceJob",
            "LeaseExpirationTime",
            "Name",
            "Tags",
            "Type"
        ]
        return {
            **{k: v for k, v in response_object.items() if v is not None and k in static_response_fields},
            **{
                "DeviceAggregatedStatus": self.device_aggregated_status,
                "ProvisioningStatus": self.provisioning_status,
            }
        }

    @property
    def response_provision(self) -> Dict[str, Union[str, bytes]]:
        return {
            "Arn": self.arn,
            "Certificates": base64.b64encode("certificate".encode("utf-8")).decode(
                "utf-8"
            ),
            "DeviceId": self.device_id,
            "IotThingName": self.iot_thing_name,
            "Status": "AWAITING_PROVISIONING",
        }

    @property
    def response_updated(self) -> Dict[str, str]:
        return {"DeviceId": self.device_id}


class PanoramaBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.devices_memory: Dict[str, Device] = {}

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

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def list_devices(
            self,
            device_aggregated_status_filter: DEVICE_AGGREGATED_STATUS_TYPE,
            name_filter: str,
            sort_by: Literal["DEVICE_ID", "CREATED_TIME", "NAME", "DEVICE_AGGREGATED_STATUS"],
            sort_order: Literal["ASCENDING", "DESCENDING"],
    ) -> List[Device]:
        devices_list = list(
            filter(
                lambda x: (
                                  name_filter is None
                                  or x.name.startswith(name_filter)
                          )
                          and (
                                  device_aggregated_status_filter is None
                                  or x.device_aggregated_status == device_aggregated_status_filter
                          ),
                self.devices_memory.values(),
            )
        )
        devices_list = list(
            sorted(
                devices_list,
                key={
                    "DEVICE_ID": lambda x: x.device_id,
                    "CREATED_TIME": lambda x: x.created_time,
                    "NAME": lambda x: x.name,
                    "DEVICE_AGGREGATED_STATUS": lambda x: x.device_aggregated_status,
                    None: lambda x: x.created_time,
                }[sort_by],
                reverse=sort_order == "DESCENDING",
            )
        )
        return devices_list

    def update_device_metadata(self, device_id: str, description: str) -> Device:
        self.devices_memory[device_id].description = description
        return self.devices_memory[device_id]


panorama_backends = BackendDict(
    PanoramaBackend,
    "panorama",
    False,
    additional_regions=[
        "us-east-1",
        "us-west-2",
        "ca-central-1",
        "eu-west-1",
        "ap-southeast-2",
        "ap-southeast-1",
    ],
)
