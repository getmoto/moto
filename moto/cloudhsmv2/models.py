"""CloudHSMV2Backend class with methods for supported APIs."""


from moto.core.base_backend import BackendDict, BaseBackend
from moto.utilities.paginator import Paginator


class CloudHSMV2Backend(BaseBackend):
    """Implementation of CloudHSMV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.tags = {}

    def list_tags(self, resource_id, next_token, max_results):
        """List tags for a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to list tags for
            next_token (str): Token for pagination
            max_results (int): Maximum number of results to return

        Returns:
            tuple: (list of tags, next token)
        """
        if resource_id not in self.tags:
            return [], None

        tags = sorted(self.tags.get(resource_id, []), key=lambda x: x["Key"])

        if not max_results:
            return tags, None

        # Add padding to the token if it exists
        if next_token:
            padding = 4 - (len(next_token) % 4)
            if padding != 4:
                next_token = next_token + ("=" * padding)

        paginator = Paginator(
            max_results=max_results,
            unique_attribute="Key",
            starting_token=next_token,
            fail_on_invalid_token=False,
        )

        results, token = paginator.paginate(tags)

        # Remove padding from the token before returning
        if token:
            token = token.rstrip("=")

        return results, token

    def tag_resource(self, resource_id, tag_list):
        """Add or update tags for a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to tag
            tag_list (list): List of tag dictionaries with 'Key' and 'Value' pairs

        Returns:
            dict: Empty dictionary per AWS spec

        Raises:
            ValueError: If resource_id or tag_list is None
        """
        if resource_id is None:
            raise ValueError("ResourceId must not be None")
        if tag_list is None:
            raise ValueError("TagList must not be None")

        if resource_id not in self.tags:
            self.tags[resource_id] = []

        # Update existing tags and add new ones
        for new_tag in tag_list:
            tag_exists = False
            for existing_tag in self.tags[resource_id]:
                if existing_tag["Key"] == new_tag["Key"]:
                    existing_tag["Value"] = new_tag["Value"]
                    tag_exists = True
                    break
            if not tag_exists:
                self.tags[resource_id].append(new_tag)

        return {}

    def untag_resource(self, resource_id, tag_key_list):
        """Remove tags from a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to untag
            tag_key_list (list): List of tag keys to remove

        Returns:
            dict: Empty dictionary per AWS spec

        Raises:
            ValueError: If resource_id or tag_key_list is None
        """
        if resource_id is None:
            raise ValueError("ResourceId must not be None")
        if tag_key_list is None:
            raise ValueError("TagKeyList must not be None")

        if resource_id in self.tags:
            self.tags[resource_id] = [
                tag for tag in self.tags[resource_id] if tag["Key"] not in tag_key_list
            ]

        return {}


cloudhsmv2_backends = BackendDict(CloudHSMV2Backend, "cloudhsmv2")
