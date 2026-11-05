from moto.core.responses import ActionResult, BaseResponse
from moto.route53domains.models import Route53DomainsBackend, route53domains_backends
from moto.route53domains.validators import Route53DomainsOperation


class Route53DomainsResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="route53domains")
        self.automated_parameter_parsing = True

    @property
    def route53domains_backend(self) -> Route53DomainsBackend:
        return route53domains_backends[self.current_account][self.partition]

    def register_domain(self) -> ActionResult:
        domain_name = self._get_param("DomainName")
        duration_in_years = self._get_param("DurationInYears")
        auto_renew = self._get_bool_param("AutoRenew", if_none=True)
        admin_contact = self._get_param("AdminContact")
        registrant_contact = self._get_param("RegistrantContact")
        tech_contact = self._get_param("TechContact")
        privacy_protection_admin_contact = self._get_bool_param(
            "PrivacyProtectAdminContact", if_none=True
        )
        privacy_protection_registrant_contact = self._get_bool_param(
            "PrivacyProtectRegistrantContact", if_none=True
        )
        privacy_protection_tech_contact = self._get_bool_param(
            "PrivacyProtectTechContact", if_none=True
        )
        extra_params = self._get_param("ExtraParams")

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

        return ActionResult({"OperationId": operation.id})

    def delete_domain(self) -> ActionResult:
        domain_name = self._get_param("DomainName")
        operation = self.route53domains_backend.delete_domain(domain_name)

        return ActionResult({"OperationId": operation.id})

    def get_domain_detail(self) -> ActionResult:
        domain_name = self._get_param("DomainName")
        domain = self.route53domains_backend.get_domain(domain_name=domain_name)
        contacts = {
            "AdminContact": domain.admin_contact,
            "RegistrantContact": domain.registrant_contact,
            "TechContact": domain.tech_contact,
            "BillingContact": domain.admin_contact,
        }
        result = {
            "DomainName": domain.domain_name,
            "Nameservers": [
                {"Name": server.name, "GlueIps": server.glue_ips or None}
                for server in domain.nameservers
            ],
            "AutoRenew": domain.auto_renew,
            "AdminPrivacy": domain.admin_privacy,
            "RegistrantPrivacy": domain.registrant_privacy,
            "TechPrivacy": domain.tech_privacy,
            "RegistrarName": domain.registrar_name,
            "WhoIsServer": domain.whois_server,
            "RegistrarUrl": domain.registrar_url,
            "AbuseContactEmail": domain.abuse_contact_email,
            "AbuseContactPhone": domain.abuse_contact_phone,
            "RegistryDomainId": "",
            "CreationDate": domain.creation_date,
            "UpdatedDate": domain.updated_date,
            "ExpirationDate": domain.expiration_date,
            "Reseller": domain.reseller,
            "DnsSec": "",
            "StatusList": domain.status_list,
            "DnssecKeys": domain.dns_sec_keys,
        }
        for key, contact in contacts.items():
            result[key] = {
                "FirstName": contact.first_name,
                "LastName": contact.last_name,
                "ContactType": contact.contact_type,
                "OrganizationName": contact.organization_name,
                "AddressLine1": contact.address_line_1,
                "AddressLine2": contact.address_line_2,
                "City": contact.city,
                "State": contact.state,
                "CountryCode": contact.country_code,
                "ZipCode": contact.zip_code,
                "PhoneNumber": contact.phone_number,
                "Email": contact.email,
                "Fax": contact.fax,
                "ExtraParams": contact.extra_params,
            }
        return ActionResult(result)

    def list_domains(self) -> ActionResult:
        filter_conditions = self._get_param("FilterConditions")
        sort_condition = self._get_param("SortCondition")
        marker = self._get_param("Marker")
        max_items = self._get_param("MaxItems")
        domains, marker = self.route53domains_backend.list_domains(
            filter_conditions=filter_conditions,
            sort_condition=sort_condition,
            marker=marker,
            max_items=max_items,
        )
        result = {
            "Domains": [
                {
                    "DomainName": domain.domain_name,
                    "AutoRenew": domain.auto_renew,
                    "Expiry": domain.expiration_date,
                    "TransferLock": True,
                }
                for domain in domains
            ],
            "NextPageMarker": marker,
        }
        return ActionResult(result)

    def list_operations(self) -> ActionResult:
        submitted_since = self._get_param("SubmittedSince")
        max_items = self._get_param("MaxItems")
        statuses = self._get_param("Status")
        marker = self._get_param("Marker")
        types = self._get_param("Type")
        sort_by = self._get_param("SortBy")
        sort_order = self._get_param("SortOrder")

        operations, marker = self.route53domains_backend.list_operations(
            submitted_since=submitted_since,
            max_items=max_items,
            marker=marker,
            statuses=statuses,
            types=types,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        result = {
            "Operations": [
                {
                    "OperationId": operation.id,
                    "Status": operation.status,
                    "StatusFlag": operation.status_flag,
                    "DomainName": operation.domain_name,
                    "LastUpdatedDate": operation.last_updated_date,
                    "SubmittedDate": operation.submitted_date,
                    "Type": operation.type,
                    "Message": operation.message,
                }
                for operation in operations
            ],
            "NextPageMarker": marker,
        }
        return ActionResult(result)

    def get_operation_detail(self) -> ActionResult:
        operation_id = self._get_param("OperationId")
        operation: Route53DomainsOperation = self.route53domains_backend.get_operation(
            operation_id
        )
        result = {
            "OperationId": operation.id,
            "Status": operation.status,
            "StatusFlag": operation.status_flag,
            "DomainName": operation.domain_name,
            "LastUpdatedDate": operation.last_updated_date,
            "SubmittedDate": operation.submitted_date,
            "Type": operation.type,
            "Message": operation.message,
        }
        return ActionResult(result)

    def update_domain_nameservers(self) -> ActionResult:
        domain_name = self._get_param("DomainName")
        nameservers = self._get_param("Nameservers")

        operation: Route53DomainsOperation = (
            self.route53domains_backend.update_domain_nameservers(
                domain_name=domain_name, nameservers=nameservers
            )
        )

        return ActionResult({"OperationId": operation.id})
