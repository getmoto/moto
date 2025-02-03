"""CloudHSMV2Backend class with methods for supported APIs."""

from moto.core.base_backend import BackendDict, BaseBackend


class CloudHSMV2Backend(BaseBackend):
    """Implementation of CloudHSMV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.tags = {}  # Dict to store resource tags: {resource_id: [{Key: str, Value: str}]}

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

        tags = self.tags.get(resource_id, [])

        # Handle pagination
        start_idx = 0
        if next_token:
            try:
                start_idx = int(next_token)
            except ValueError:
                start_idx = 0

        if max_results is None:
            max_results = 50  # Default AWS limit

        end_idx = start_idx + max_results
        result_tags = tags[start_idx:end_idx]

        # Generate next token if there are more results
        next_token = str(end_idx) if end_idx < len(tags) else None

        return result_tags, next_token

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
        # implement here
        return


cloudhsmv2_backends = BackendDict(CloudHSMV2Backend, "cloudhsmv2")
