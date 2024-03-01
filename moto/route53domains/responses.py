import json
from typing import Dict, List, Optional

from moto.core.responses import BaseResponse
from moto.route53domains.models import Route53DomainsBackend, route53domains_backends


class Route53DomainsResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="route53-domains")

    @property
    def route53domains_backend(self) -> Route53DomainsBackend:
        """Return backend instance"""
        return route53domains_backends[self.current_account]["global"]

    def register_domain(self) -> str:
        """Register a domain"""
        domain_name: Optional[str] = self._get_param("DomainName")
        duration_in_years: Optional[int] = self._get_int_param("DurationInYears")
        auto_renew: bool = self._get_bool_param("AutoRenew", if_none=True)
        admin_contact: Optional[Dict] = self._get_param("AdminContact")
        registrant_contact: Optional[Dict] = self._get_param("RegistrantContact")
        tech_contact: Optional[Dict] = self._get_param("TechContact")
        privacy_protection_admin_contact: bool = self._get_bool_param(
            "PrivacyProtectAdminContact", if_none=True
        )
        privacy_protection_registrant_contact: bool = self._get_bool_param(
            "PrivacyProtectRegistrantContact", if_none=True
        )
        privacy_protection_tech_contact: bool = self._get_bool_param(
            "PrivacyProtectTechContact", if_none=True
        )
        extra_params: Optional[List[Dict]] = self._get_param("ExtraParams")

        operation = self.route53domains_backend.register_domain(
            domain_name=domain_name,
            duration_in_years=duration_in_years,
            auto_renew=auto_renew,
            admin_contact=admin_contact,
            registrant_contact=registrant_contact,
            tech_contact=tech_contact,
            private_protect_admin_contact=privacy_protection_admin_contact,
            private_protect_registrant_contact=privacy_protection_registrant_contact,
            private_protect_tech_contact=privacy_protection_tech_contact,
            extra_params=extra_params,
        )

        return json.dumps({"OperationId": operation.id})

    def get_domain_detail(self) -> str:
        """Get detailed information about a specified domain"""
        domain_name: Optional[str] = self._get_param("DomainName")

        return json.dumps(self.route53domains_backend.get_domain(domain_name=domain_name).to_json())

    def list_operations(self):
        submitted_since_timestamp: Optional[int] = self._get_int_param("SubmittedSince")
        max_items: Optional[int] = self._get_int_param("MaxItems")
        statuses: Optional[List[str]] = self._get_param("Status")
        marker: Optional[str] = self._get_param("Marker")
        types: Optional[List[str]] = self._get_param("Type")
        sort_by: Optional[str] = self._get_param("sort_by")
        sort_order: Optional[str] = self._get_param("SortOrder")

        operations, marker = self.route53domains_backend.list_operations(
            submitted_since_timestamp=submitted_since_timestamp,
            max_items=max_items,
            marker=marker,
            statuses=statuses,
            types=types,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        res = {
            "Operations": [operation.to_json() for operation in operations],
        }

        if marker:
            res["NextPageMarker"] = marker

        return json.dumps(res)
