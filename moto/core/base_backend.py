import re
import string
from collections import defaultdict
from typing import List, Dict
from .utils import convert_regex_to_flask_path


model_data = defaultdict(dict)


class InstanceTrackerMeta(type):
    def __new__(meta, name, bases, dct):
        cls = super(InstanceTrackerMeta, meta).__new__(meta, name, bases, dct)
        if name == "BaseModel":
            return cls

        service = cls.__module__.split(".")[1]
        if name not in model_data[service]:
            model_data[service][name] = cls
        cls.instances = []
        return cls


class BaseBackend:
    def __init__(self, region_name, account_id=None) -> None:
        self.region_name = region_name
        self.account_id = account_id

    def _reset_model_refs(self):
        # Remove all references to the models stored
        for models in model_data.values():
            for model in models.values():
                model.instances = []

    def reset(self):
        region_name = self.region_name
        account_id = self.account_id
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name, account_id)

    @property
    def _url_module(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(
            backend_urls_module_name, fromlist=["url_bases", "url_paths"]
        )
        return backend_urls_module

    @property
    def urls(self):
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
    def url_paths(self):
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
    def url_bases(self):
        """
        A list containing the url_bases extracted from urls.py
        """
        return self._url_module.url_bases

    @property
    def flask_paths(self):
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
        service_region, zones
    ):  # pylint: disable=unused-argument
        """Invoke the factory method for any VPC endpoint(s) services."""
        return None

    @staticmethod
    def vpce_random_number():
        from moto.moto_api._internal import mock_random as random

        """Return random number for a VPC endpoint service ID."""
        return "".join([random.choice(string.hexdigits.lower()) for i in range(17)])

    @staticmethod
    def default_vpc_endpoint_service_factory(
        service_region,
        zones,
        service="",
        service_type="Interface",
        private_dns_names=True,
        special_service_name="",
        policy_supported=True,
        base_endpoint_dns_names=None,
    ) -> List[Dict[str, str]]:  # pylint: disable=too-many-arguments
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
