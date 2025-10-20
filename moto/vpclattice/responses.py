import json
from urllib.parse import unquote

from moto.core.responses import BaseResponse

from .models import VPCLatticeBackend, vpclattice_backends


class VPCLatticeResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="vpc-lattice")

    @property
    def backend(self) -> VPCLatticeBackend:
        return vpclattice_backends[self.current_account][self.region]

    def create_service(self) -> str:
        service = self.backend.create_service(
            auth_type=self._get_param("authType"),
            certificate_arn=self._get_param("certificateArn"),
            client_token=self._get_param("clientToken"),
            custom_domain_name=self._get_param("customDomainName"),
            name=self._get_param("name"),
            tags=self._get_param("tags"),
        )
        return json.dumps(service.to_dict())

    def create_service_network(self) -> str:
        sn = self.backend.create_service_network(
            auth_type=self._get_param("authType"),
            client_token=self._get_param("clientToken"),
            name=self._get_param("name"),
            sharing_config=self._get_param("sharingConfig"),
            tags=self._get_param("tags"),
        )
        return json.dumps(sn.to_dict())

    def create_service_network_vpc_association(self) -> str:
        assoc = self.backend.create_service_network_vpc_association(
            client_token=self._get_param("clientToken"),
            security_group_ids=self._get_param("securityGroupIds"),
            service_network_identifier=self._get_param("serviceNetworkIdentifier"),
            tags=self._get_param("tags"),
            vpc_identifier=self._get_param("vpcIdentifier"),
        )
        return json.dumps(assoc.to_dict())

    def create_rule(self) -> str:
        rule = self.backend.create_rule(
            action=self._get_param("action"),
            client_token=self._get_param("clientToken"),
            listener_identifier=self._get_param("listenerIdentifier"),
            match=self._get_param("match"),
            name=self._get_param("name"),
            priority=self._get_param("priority"),
            service_identifier=self._get_param("serviceIdentifier"),
            tags=self._get_param("tags"),
        )
        return json.dumps(rule.to_dict())

    def create_access_log_subscription(self) -> str:
        sub = self.backend.create_access_log_subscription(
            resourceIdentifier=self._get_param("resourceIdentifier"),
            destinationArn=self._get_param("destinationArn"),
            client_token=self._get_param("clientToken"),
            serviceNetworkLogType=self._get_param("serviceNetworkLogType"),
            tags=self._get_param("tags"),
        )

        return json.dumps(sub.to_dict())

    def get_access_log_subscription(self) -> str:
        path = unquote(self.path)

        sub = self.backend.get_access_log_subscription(
            accessLogSubscriptionIdentifier=path.split("/")[-1]
        )

        return json.dumps(sub.to_dict())

    def list_access_log_subscriptions(self) -> str:
        subs = self.backend.list_access_log_subscriptions(
            resourceIdentifier=self._get_param("resourceIdentifier"),
            maxResults=self._get_int_param("maxResults"),
            nextToken=self._get_param("nextToken"),
        )

        return json.dumps({"items": [s.to_dict() for s in subs], "nextToken": ""})

    def update_access_log_subscription(self) -> str:
        path = unquote(self.path)

        sub = self.backend.update_access_log_subscription(
            accessLogSubscriptionIdentifier=path.split("/")[-1],
            destinationArn=self._get_param("destinationArn"),
        )

        return json.dumps(sub.to_dict())

    def delete_access_log_subscription(self) -> str:
        path = unquote(self.path)

        self.backend.delete_access_log_subscription(
            accessLogSubscriptionIdentifier=path.split("/")[-1]
        )

        return json.dumps({})
