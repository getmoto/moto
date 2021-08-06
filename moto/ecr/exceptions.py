from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class RepositoryAlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super().__init__(
            error_type=__class__.__name__,
            message=(
                f"The repository with name '{repository_name}' already exists "
                f"in the registry with id '{registry_id}'"
            ),
        )


class RepositoryNotEmptyException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super().__init__(
            error_type=__class__.__name__,
            message=(
                f"The repository with name '{repository_name}' "
                f"in registry with id '{registry_id}' "
                "cannot be deleted because it still contains images"
            ),
        )


class RepositoryNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super().__init__(
            error_type=__class__.__name__,
            message=(
                f"The repository with name '{repository_name}' does not exist "
                f"in the registry with id '{registry_id}'"
            ),
        )


class RepositoryPolicyNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super().__init__(
            error_type=__class__.__name__,
            message=(
                "Repository policy does not exist "
                f"for the repository with name '{repository_name}' "
                f"in the registry with id '{registry_id}'"
            ),
        )


class ImageNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, image_id, repository_name, registry_id):
        super().__init__(
            error_type=__class__.__name__,
            message=(
                f"The image with imageId {image_id} does not exist "
                f"within the repository with name '{repository_name}' "
                f"in the registry with id '{registry_id}'"
            ),
        )


class InvalidParameterException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__(error_type=__class__.__name__, message=message)
