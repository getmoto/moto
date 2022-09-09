from moto.core import get_account_id
from moto.core import CloudFormationModel
from ..exceptions import (
    IncorrectStateIamProfileAssociationError,
    InvalidAssociationIDIamProfileAssociationError,
)
from ..utils import (
    random_iam_instance_profile_association_id,
    filter_iam_instance_profile_associations,
    filter_iam_instance_profiles,
)

OWNER_ID = get_account_id()


class IamInstanceProfileAssociation(CloudFormationModel):
    def __init__(self, ec2_backend, association_id, instance, iam_instance_profile):
        self.ec2_backend = ec2_backend
        self.id = association_id
        self.instance = instance
        self.iam_instance_profile = iam_instance_profile
        self.state = "associated"


class IamInstanceProfileAssociationBackend:
    def __init__(self):
        self.iam_instance_profile_associations = {}

    def associate_iam_instance_profile(
        self, instance_id, iam_instance_profile_name=None, iam_instance_profile_arn=None
    ):
        iam_association_id = random_iam_instance_profile_association_id()

        instance_profile = filter_iam_instance_profiles(
            iam_instance_profile_arn, iam_instance_profile_name
        )

        if instance_id in self.iam_instance_profile_associations.keys():
            raise IncorrectStateIamProfileAssociationError(instance_id)

        iam_instance_profile_associations = IamInstanceProfileAssociation(
            self,
            iam_association_id,
            self.get_instance(instance_id) if instance_id else None,
            instance_profile,
        )
        # Regarding to AWS there can be only one association with ec2.
        self.iam_instance_profile_associations[
            instance_id
        ] = iam_instance_profile_associations
        return iam_instance_profile_associations

    def describe_iam_instance_profile_associations(
        self, association_ids, filters=None, max_results=100, next_token=None
    ):
        associations_list = []
        if association_ids:
            for association in self.iam_instance_profile_associations.values():
                if association.id in association_ids:
                    associations_list.append(association)
        else:
            # That's mean that no association id were given. Showing all.
            associations_list.extend(self.iam_instance_profile_associations.values())

        associations_list = filter_iam_instance_profile_associations(
            associations_list, filters
        )

        starting_point = int(next_token or 0)
        ending_point = starting_point + int(max_results or 100)
        associations_page = associations_list[starting_point:ending_point]
        new_next_token = (
            str(ending_point) if ending_point < len(associations_list) else None
        )

        return associations_page, new_next_token

    def disassociate_iam_instance_profile(self, association_id):
        iam_instance_profile_associations = None
        for association_key in self.iam_instance_profile_associations.keys():
            if (
                self.iam_instance_profile_associations[association_key].id
                == association_id
            ):
                iam_instance_profile_associations = (
                    self.iam_instance_profile_associations[association_key]
                )
                del self.iam_instance_profile_associations[association_key]
                # Deleting once and avoiding `RuntimeError: dictionary changed size during iteration`
                break

        if not iam_instance_profile_associations:
            raise InvalidAssociationIDIamProfileAssociationError(association_id)

        return iam_instance_profile_associations

    def replace_iam_instance_profile_association(
        self,
        association_id,
        iam_instance_profile_name=None,
        iam_instance_profile_arn=None,
    ):
        instance_profile = filter_iam_instance_profiles(
            iam_instance_profile_arn, iam_instance_profile_name
        )

        iam_instance_profile_association = None
        for association_key in self.iam_instance_profile_associations.keys():
            if (
                self.iam_instance_profile_associations[association_key].id
                == association_id
            ):
                self.iam_instance_profile_associations[
                    association_key
                ].iam_instance_profile = instance_profile
                iam_instance_profile_association = (
                    self.iam_instance_profile_associations[association_key]
                )
                break

        if not iam_instance_profile_association:
            raise InvalidAssociationIDIamProfileAssociationError(association_id)

        return iam_instance_profile_association
