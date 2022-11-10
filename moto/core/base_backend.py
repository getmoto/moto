from boto3 import Session
import re
import string
from collections import defaultdict
from functools import lru_cache
from threading import RLock
from typing import Any, List, Dict, Optional, ClassVar, TypeVar, Iterator
from uuid import uuid4
from moto.settings import allow_unknown_region
from .utils import convert_regex_to_flask_path


model_data: Dict[str, Dict[str, object]] = defaultdict(dict)


class InstanceTrackerMeta(type):
    def __new__(meta, name: str, bases: Any, dct: Dict[str, Any]) -> type:
        cls = super(InstanceTrackerMeta, meta).__new__(meta, name, bases, dct)
        if name == "BaseModel":
            return cls

        service = cls.__module__.split(".")[1]
        if name not in model_data[service]:
            model_data[service][name] = cls
        cls.instances: ClassVar[List[Any]] = []  # type: ignore
        return cls


class BaseBackend:
    def __init__(self, region_name: str, account_id: str):
        self.region_name = region_name
        self.account_id = account_id

    def _reset_model_refs(self) -> None:
        # Remove all references to the models stored
        for models in model_data.values():
            for model in models.values():
                model.instances = []  # type: ignore[attr-defined]

    def reset(self) -> None:
        region_name = self.region_name
        account_id = self.account_id
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name, account_id)  # type: ignore[misc]

    @property
    def _url_module(self) -> Any:  # type: ignore[misc]
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(
            backend_urls_module_name, fromlist=["url_bases", "url_paths"]
        )
        return backend_urls_module

    @property
    def urls(self) -> Dict[str, str]:
        """
        A dictionary of the urls to be mocked with this service and the handlers
        that should be called in their place
        """
        url_bases = self.url_bases
        unformatted_paths = self._url_module.url_paths

        urls = {}
        for url_base in url_bases:
            # The default URL_base will look like: http://service.[..].amazonaws.com/...
            # This extension ensures support for the China regions
            cn_url_base = re.sub(r"amazonaws\\?.com$", "amazonaws.com.cn", url_base)
            for url_path, handler in unformatted_paths.items():
                url = url_path.format(url_base)
                urls[url] = handler
                cn_url = url_path.format(cn_url_base)
                urls[cn_url] = handler

        return urls

    @property
    def url_paths(self) -> Dict[str, str]:
        """
        A dictionary of the paths of the urls to be mocked with this service and
        the handlers that should be called in their place
        """
        unformatted_paths = self._url_module.url_paths

        paths = {}
        for unformatted_path, handler in unformatted_paths.items():
            path = unformatted_path.format("")
            paths[path] = handler

        return paths

    @property
    def url_bases(self) -> List[str]:
        """
        A list containing the url_bases extracted from urls.py
        """
        return self._url_module.url_bases

    @property
    def flask_paths(self) -> Dict[str, str]:
        """
        The url paths that will be used for the flask server
        """
        paths = {}
        for url_path, handler in self.url_paths.items():
            url_path = convert_regex_to_flask_path(url_path)
            paths[url_path] = handler

        return paths

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: List[str]  # pylint: disable=unused-argument
    ) -> List[Dict[str, str]]:
        """Invoke the factory method for any VPC endpoint(s) services."""
        return []

    @staticmethod
    def vpce_random_number() -> str:
        from moto.moto_api._internal import mock_random as random

        """Return random number for a VPC endpoint service ID."""
        return "".join([random.choice(string.hexdigits.lower()) for i in range(17)])

    @staticmethod
    def default_vpc_endpoint_service_factory(  # type: ignore[misc]
        service_region: str,
        zones: List[str],
        service: str = "",
        service_type: str = "Interface",
        private_dns_names: bool = True,
        special_service_name: str = "",
        policy_supported: bool = True,
        base_endpoint_dns_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:  # pylint: disable=too-many-arguments
        """List of dicts representing default VPC endpoints for this service."""
        if special_service_name:
            service_name = f"com.amazonaws.{service_region}.{special_service_name}"
        else:
            service_name = f"com.amazonaws.{service_region}.{service}"

        if not base_endpoint_dns_names:
            base_endpoint_dns_names = [f"{service}.{service_region}.vpce.amazonaws.com"]

        endpoint_service = {
            "AcceptanceRequired": False,
            "AvailabilityZones": zones,
            "BaseEndpointDnsNames": base_endpoint_dns_names,
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "ServiceId": f"vpce-svc-{BaseBackend.vpce_random_number()}",
            "ServiceName": service_name,
            "ServiceType": [{"ServiceType": service_type}],
            "Tags": [],
            "VpcEndpointPolicySupported": policy_supported,
        }

        # Don't know how private DNS names are different, so for now just
        # one will be added.
        if private_dns_names:
            endpoint_service[
                "PrivateDnsName"
            ] = f"{service}.{service_region}.amazonaws.com"
            endpoint_service["PrivateDnsNameVerificationState"] = "verified"
            endpoint_service["PrivateDnsNames"] = [
                {"PrivateDnsName": f"{service}.{service_region}.amazonaws.com"}
            ]
        return [endpoint_service]

    # def list_config_service_resources(self, resource_ids, resource_name, limit, next_token):
    #     """For AWS Config. This will list all of the resources of the given type and optional resource name and region"""
    #     raise NotImplementedError()


backend_lock = RLock()
SERVICE_BACKEND = TypeVar("SERVICE_BACKEND", bound=BaseBackend)


class AccountSpecificBackend(Dict[str, SERVICE_BACKEND]):
    """
    Dictionary storing the data for a service in a specific account.
    Data access pattern:
      account_specific_backend[region: str] = backend: BaseBackend
    """

    def __init__(
        self,
        service_name: str,
        account_id: str,
        backend: type,
        use_boto3_regions: bool,
        additional_regions: Optional[List[str]],
    ):
        self.service_name = service_name
        self.account_id = account_id
        self.backend = backend
        self.regions = []
        if use_boto3_regions:
            sess = Session()
            self.regions.extend(sess.get_available_regions(service_name))
            self.regions.extend(
                sess.get_available_regions(service_name, partition_name="aws-us-gov")
            )
            self.regions.extend(
                sess.get_available_regions(service_name, partition_name="aws-cn")
            )
        self.regions.extend(additional_regions or [])
        self._id = str(uuid4())

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(self._id)

    def __eq__(self, other: Any) -> bool:
        return (
            other
            and isinstance(other, AccountSpecificBackend)
            and other._id == self._id
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def reset(self) -> None:
        for region_specific_backend in self.values():
            region_specific_backend.reset()

    def __contains__(self, region: str) -> bool:  # type: ignore[override]
        return region in self.regions or region in self.keys()

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)

    def __iter__(self) -> Iterator[str]:
        return super().__iter__()

    def __len__(self) -> int:
        return super().__len__()

    def __setitem__(self, key: str, value: SERVICE_BACKEND) -> None:
        super().__setitem__(key, value)

    @lru_cache()
    def __getitem__(self, region_name: str) -> SERVICE_BACKEND:  # type: ignore[override]
        if region_name in self.keys():
            return super().__getitem__(region_name)
        # Create the backend for a specific region
        with backend_lock:
            if region_name in self.regions and region_name not in self.keys():
                super().__setitem__(
                    region_name, self.backend(region_name, account_id=self.account_id)
                )
            if region_name not in self.regions and allow_unknown_region():
                super().__setitem__(
                    region_name, self.backend(region_name, account_id=self.account_id)
                )
        return super().__getitem__(region_name)


class BackendDict(Dict[str, AccountSpecificBackend]):  # type: ignore[type-arg]
    """
    Data Structure to store everything related to a specific service.
    Format:
      [account_id: str]: AccountSpecificBackend
      [account_id: str][region: str] = BaseBackend
    """

    def __init__(
        self,
        backend: Any,
        service_name: str,
        use_boto3_regions: bool = True,
        additional_regions: Optional[List[str]] = None,
    ):
        self.backend = backend
        self.service_name = service_name
        self._use_boto3_regions = use_boto3_regions
        self._additional_regions = additional_regions
        self._id = str(uuid4())

    def __hash__(self) -> int:  # type: ignore[override]
        # Required for the LRUcache to work.
        # service_name is enough to determine uniqueness - other properties are dependent
        return hash(self._id)

    def __eq__(self, other: Any) -> bool:
        return other and isinstance(other, BackendDict) and other._id == self._id

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    @lru_cache()
    def __getitem__(self, account_id: str) -> AccountSpecificBackend:  # type: ignore
        self._create_account_specific_backend(account_id)
        return super().__getitem__(account_id)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)

    def __iter__(self) -> Iterator[str]:
        return super().__iter__()

    def __len__(self) -> int:
        return super().__len__()

    def __setitem__(self, key: str, value: AccountSpecificBackend) -> None:  # type: ignore[type-arg]
        super().__setitem__(key, value)

    def _create_account_specific_backend(self, account_id: str) -> None:
        with backend_lock:
            if account_id not in list(self.keys()):
                self[account_id] = AccountSpecificBackend(
                    service_name=self.service_name,
                    account_id=account_id,
                    backend=self.backend,
                    use_boto3_regions=self._use_boto3_regions,
                    additional_regions=self._additional_regions,
                )
