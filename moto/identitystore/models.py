from typing import Dict, Tuple, List, Any, NamedTuple, Optional
from typing_extensions import Self
from uuid import UUID

from botocore.exceptions import ParamValidationError

from moto.moto_api._internal import mock_random
from moto.core import BaseBackend, BackendDict
from .exceptions import (
    ResourceNotFoundException,
    ValidationException,
    ConflictException,
)


next_token_prefix = "cmgcRYIxlu3fx4F2EDMscv+davRdDC7qLmR87pgwgopNDNl7H+zQzsc7VrHK2nBBHaHaVYZOZwE5ZduPr0tAg2QW7s3t4KWK2sdd/s0Gw49M66wh+uCptmtei0HYmTVQ7KT87yETbeEn+9l+Q7STmuyKbtljY2HKW1sCoQd57q/3hBhtC1Jw7qzVhUME1mGrktbXdUqnHUyuFRqi24fsiisZLszMuUTR41c6sIoPH9zEK1H8lhtfL7GIOJbOsRwdTZnmdxarpXZYmYSkwdIuILzrG/NuLbyvQS7aC4VfJcxACPNS63nPmgwHRqzUI0TBfQ==:"


class Name(NamedTuple):
    Formatted: Optional[str]
    FamilyName: Optional[str]
    GivenName: Optional[str]
    MiddleName: Optional[str]
    HonorificPrefix: Optional[str]
    HonorificSuffix: Optional[str]

    @classmethod
    def from_dict(cls, name_dict: Dict[str, str]) -> Optional[Self]:
        if not name_dict:
            return None
        return cls(
            name_dict["Formatted"] if "Formatted" in name_dict else None,
            name_dict["FamilyName"] if "FamilyName" in name_dict else None,
            name_dict["GivenName"] if "GivenName" in name_dict else None,
            name_dict["MiddleName"] if "MiddleName" in name_dict else None,
            name_dict["HonorificPrefix"] if "HonorificPrefix" in name_dict else None,
            name_dict["HonorificSuffix"] if "HonorificSuffix" in name_dict else None,
        )


class User(NamedTuple):
    UserId: str
    IdentityStoreId: str
    UserName: str
    Name: Name
    DisplayName: str
    NickName: str
    ProfileUrl: str
    Emails: List[Dict[str, str]]
    Addresses: List[Dict[str, str]]
    PhoneNumbers: List[Dict[str, str]]
    UserType: str
    Title: str
    PreferredLanguage: str
    Locale: str
    Timezone: str


class IdentityStoreData:
    def __init__(self) -> None:
        self.groups: Dict[str, Dict[str, str]] = {}
        self.users: Dict[str, User] = {}
        self.group_memberships: Dict[str, Any] = {}


class IdentityStoreBackend(BaseBackend):
    """Implementation of IdentityStore APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.identity_stores: Dict[str, IdentityStoreData] = {}

    def create_group(
        self, identity_store_id: str, display_name: str, description: str
    ) -> Tuple[str, str]:
        identity_store = self.__get_identity_store(identity_store_id)

        matching = [
            g
            for g in identity_store.groups.values()
            if g["DisplayName"] == display_name
        ]
        if len(matching) > 0:
            raise ConflictException(
                message="Duplicate GroupDisplayName",
                reason="UNIQUENESS_CONSTRAINT_VIOLATION",
            )

        group_id = str(mock_random.uuid4())
        group_dict = {
            "GroupId": group_id,
            "IdentityStoreId": identity_store_id,
            "DisplayName": display_name,
            "Description": description,
        }
        identity_store.groups[group_id] = group_dict
        return group_id, identity_store_id

    def get_group_id(
        self, identity_store_id: str, alternate_identifier: Dict[str, Any]
    ) -> Tuple[str, str]:
        identity_store = self.__get_identity_store(identity_store_id)
        if "UniqueAttribute" in alternate_identifier:
            if (
                "AttributeValue" in alternate_identifier["UniqueAttribute"]
                and alternate_identifier["UniqueAttribute"]["AttributePath"].lower()
                == "displayname"
            ):
                for g in identity_store.groups.values():
                    if (
                        g["DisplayName"]
                        == alternate_identifier["UniqueAttribute"]["AttributeValue"]
                    ):
                        return g["GroupId"], identity_store_id
        elif "ExternalId" in alternate_identifier:
            raise Exception("NotYetImplemented")

        raise ResourceNotFoundException(
            message="GROUP not found.", resource_type="GROUP"
        )

    def delete_group(self, identity_store_id: str, group_id: str) -> None:
        identity_store = self.__get_identity_store(identity_store_id)
        if group_id in identity_store.groups:
            del identity_store.groups[group_id]

    def create_user(
        self,
        user_tuple: Tuple[
            str, str, Any, str, str, str, Any, Any, Any, str, str, str, str, str
        ],
    ) -> Tuple[str, str]:
        identity_store = self.__get_identity_store(user_tuple[0])
        user_values = list(user_tuple)

        user_id = str(mock_random.uuid4())

        user_values[2] = Name.from_dict(user_tuple[2])

        new_user = User(user_id, *user_values)
        self.__validate_create_user(new_user, identity_store)

        identity_store.users[user_id] = new_user

        return user_id, user_tuple[0]

    def describe_user(self, identity_store_id: str, user_id: str) -> User:
        identity_store = self.__get_identity_store(identity_store_id)

        if user_id in identity_store.users:
            return identity_store.users[user_id]

        raise ResourceNotFoundException(message="USER not found.", resource_type="USER")

    def delete_user(self, identity_store_id: str, user_id: str) -> None:
        identity_store = self.__get_identity_store(identity_store_id)

        if user_id in identity_store.users:
            del identity_store.users[user_id]

    def create_group_membership(
        self, identity_store_id: str, group_id: str, member_id: Dict[str, str]
    ) -> Tuple[str, str]:
        identity_store = self.__get_identity_store(identity_store_id)
        user_id = member_id["UserId"]
        if user_id not in identity_store.users:
            raise ResourceNotFoundException(
                message="Member does not exist", resource_type="USER"
            )

        if group_id not in identity_store.groups:
            raise ResourceNotFoundException(
                message="Group does not exist", resource_type="GROUP"
            )

        membership_id = str(mock_random.uuid4())
        identity_store.group_memberships[membership_id] = {
            "IdentityStoreId": identity_store_id,
            "MembershipId": membership_id,
            "GroupId": group_id,
            "MemberId": {"UserId": user_id},
        }

        return membership_id, identity_store_id

    def list_group_memberships(
        self, identity_store_id: str, group_id: str, max_results: int, next_token: str
    ) -> Tuple[List[Any], Optional[str]]:
        identity_store = self.__get_identity_store(identity_store_id)

        members = [
            m
            for m in identity_store.group_memberships.values()
            if m["GroupId"] == group_id
        ]

        if not max_results:
            max_results = len(members)

        results = NextBatch(next_token)
        return results.next(members, max_results)

    def delete_group_membership(
        self, identity_store_id: str, membership_id: str
    ) -> None:
        identity_store = self.__get_identity_store(identity_store_id)
        if membership_id in identity_store.group_memberships:
            del identity_store.group_memberships[membership_id]

    def __get_identity_store(self, store_id: str) -> IdentityStoreData:
        if len(store_id) < 1:
            raise ParamValidationError(
                msg="Invalid length for parameter IdentityStoreId, value: 0, valid min length: 1"
            )
        if store_id not in self.identity_stores:
            self.identity_stores[store_id] = IdentityStoreData()
        return self.identity_stores[store_id]

    def __validate_create_user(
        self, new_user: User, identity_store: IdentityStoreData
    ) -> None:
        if not new_user.UserName:
            raise ValidationException(message="userName is a required attribute")

        missing = []

        if not new_user.DisplayName:
            missing.append("displayname")
        if not new_user.Name:
            missing.append("name")
        else:
            if not new_user.Name.GivenName:
                missing.append("givenname")
            if not new_user.Name.FamilyName:
                missing.append("familyname")

        if len(missing) > 0:
            message = ", ".join(
                [f"{att}: The attribute {att} is required" for att in missing]
            )
            raise ValidationException(message=message)

        matching = [
            u for u in identity_store.users.values() if u.UserName == new_user.UserName
        ]
        if len(matching) > 0:
            raise ConflictException(
                message="Duplicate UserName", reason="UNIQUENESS_CONSTRAINT_VIOLATION"
            )


class NextBatch:

    current = None

    def __init__(self, current_token: str) -> None:
        if current_token:
            try:
                # Get the UUID from the end of the string
                id_reversed = current_token.split("==:")[1]
                self.current = NextBatch.__reverse_uuid(id_reversed)

            except Exception:
                raise ValidationException(message="Unexpected format of next token")

    def next(
        self, all_items: List[Any], max_allowed: int
    ) -> Tuple[List[Any], Optional[str]]:
        start = 0
        if self.current:
            for i in range(len(all_items)):
                if all_items[i]["MemberId"]["UserId"] == self.current:
                    start = i
                    break

        end = start + max_allowed
        if end >= len(all_items):
            return all_items[start:], None
        else:
            next_token = NextBatch.__reverse_uuid(all_items[end]["MemberId"]["UserId"])
            return all_items[start:end], f"{next_token_prefix}{next_token}"

    @staticmethod
    def __reverse_uuid(id_str: str) -> str:
        id_str = id_str[::-1]  # reverse it
        id_str = id_str.replace("-", "")  # remove dashes
        return str(UUID(id_str))  # form back into a UUID


identitystore_backends = BackendDict(IdentityStoreBackend, "identitystore")
