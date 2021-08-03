from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class RepositoryAlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super(RepositoryAlreadyExistsException, self).__init__(
            error_type="RepositoryAlreadyExistsException",
            message=(
                f"The repository with name '{repository_name}' already exists "
                f"in the registry with id '{registry_id}'"
            ),
        )


class RepositoryNotEmptyException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super(RepositoryNotEmptyException, self).__init__(
            error_type="RepositoryNotEmptyException",
            message=(
                f"The repository with name '{repository_name}' "
                f"in registry with id '{registry_id}' "
                "cannot be deleted because it still contains images"
            ),
        )


class RepositoryNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super(RepositoryNotFoundException, self).__init__(
            error_type="RepositoryNotFoundException",
            message=(
                f"The repository with name '{repository_name}' does not exist "
                f"in the registry with id '{registry_id}'"
            ),
        )


class ImageNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, image_id, repository_name, registry_id):
        super(ImageNotFoundException, self).__init__(
            error_type="ImageNotFoundException",
            message="The image with imageId {0} does not exist within the repository with name '{1}' "
            "in the registry with id '{2}'".format(
                image_id, repository_name, registry_id
            ),
        )
