from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.route53 import route53_backends
from moto.route53.models import Route53Backend

from .exceptions import DuplicateRequestException, InvalidInputException, DomainLimitExceededException
from .validators import (
    DOMAIN_OPERATION_STATUSES,
    DOMAIN_OPERATION_TYPES,
    Route53Domain,
    Route53DomainsContactDetail,
    Route53DomainsOperation,
    ValidationException,
)


class Route53DomainsBackend(BaseBackend):
    """Implementation of Route53Domains APIs."""
    DEFAULT_MAX_DOMAINS_COUNT = 20

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.__route53_backend: Route53Backend = route53_backends[account_id]["global"]
        self.__domains: Dict[str, Route53Domain] = {}
        self.__operations: Dict[str, Route53DomainsOperation] = {}

    def register_domain(
        self,
        domain_name: str,
        duration_in_years: int,
        auto_renew: bool,
        admin_contact: Dict,
        registrant_contact: Dict,
        tech_contact: Dict,
        private_protect_admin_contact: bool,
        private_protect_registrant_contact: bool,
        private_protect_tech_contact: bool,
        extra_params: List[Dict],
    ) -> Route53DomainsOperation:
        """Register a domain"""

        if len(self.__domains) == self.DEFAULT_MAX_DOMAINS_COUNT:
            raise DomainLimitExceededException()

        requested_operation = Route53DomainsOperation.validate(
            domain_name=domain_name, status="SUCCESSFUL", type_="REGISTER_DOMAIN"
        )

        self.__validate_duplicate_requests(requested_operation)

        expiration_date = datetime.now(timezone.utc) + timedelta(
            days=365 * duration_in_years
        )

        try:

            domain = Route53Domain.validate(
                domain_name=domain_name,
                auto_renew=auto_renew,
                admin_contact=Route53DomainsContactDetail.validate_dict(admin_contact),
                registrant_contact=Route53DomainsContactDetail.validate_dict(
                    registrant_contact
                ),
                tech_contact=Route53DomainsContactDetail.validate_dict(tech_contact),
                admin_privacy=private_protect_admin_contact,
                registrant_privacy=private_protect_registrant_contact,
                tech_privacy=private_protect_tech_contact,
                expiration_date=expiration_date,
                extra_params=extra_params,
            )

        except ValidationException as e:
            raise InvalidInputException(e.errors)

        self.__operations[requested_operation.id] = requested_operation

        self.__route53_backend.create_hosted_zone(
            name=domain.domain_name, private_zone=False
        )

        self.__domains[domain_name] = domain
        return requested_operation

    def __validate_duplicate_requests(
        self, requested_operation: Route53DomainsOperation
    ):
        for operation in self.__operations.values():
            if (
                operation.domain_name == requested_operation.domain_name
                and operation.type == requested_operation.type
            ):
                raise DuplicateRequestException()

    def list_operations(
        self,
        submitted_since_timestamp: Optional[int] = None,
        marker: Optional[str] = None,
        max_items: Optional[int] = None,
        statuses: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Route53DomainsOperation], Optional[str]]:

        errors = []
        statuses = statuses or []
        types = types or []
        max_items = max_items or 20  # AWS default is 20

        if any(status not in DOMAIN_OPERATION_STATUSES for status in statuses):
            errors.append("Status is invalid")
        if any(type_ not in DOMAIN_OPERATION_TYPES for type_ in types):
            errors.append("Type is invalid")

        if errors:
            raise InvalidInputException(errors)

        submitted_since = (
            datetime.fromtimestamp(submitted_since_timestamp, timezone.utc)
            if submitted_since_timestamp
            else None
        )

        operations_to_return: List[Route53DomainsOperation] = []

        for operation in self.__operations.values():
            if len(operations_to_return) == max_items:
                break

            if statuses and operation.status not in statuses:
                continue

            if types and operation.type not in types:
                continue

            if submitted_since and operation.submitted_date < submitted_since:
                continue

            operations_to_return.append(operation)

        if sort_by == "SubmittedDate":
            operations_to_return.sort(
                key=lambda op: op.submitted_date, reverse=sort_order == "ASC"
            )

        start_idx = 0 if marker is None else int(marker)
        marker = (
            None
            if len(operations_to_return) < start_idx + max_items
            else str(start_idx + max_items)
        )
        return operations_to_return[start_idx : start_idx + max_items], marker

    @staticmethod
    def __sort_by_submitted_date(operation: Route53DomainsOperation):
        return operation.submitted_date


route53domains_backends = BackendDict(
    Route53DomainsBackend,
    "route53domains",
    use_boto3_regions=False,
    additional_regions=["global"],
)
