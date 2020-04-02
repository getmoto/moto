from __future__ import unicode_literals
from moto.core.exceptions import RESTError, JsonRESTError


class RepositoryNotFoundException(RESTError):
    code = 400

    def __init__(self, repository_name, registry_id):
        super(RepositoryNotFoundException, self).__init__(
            error_type="RepositoryNotFoundException",
            message="The repository with name '{0}' does not exist in the registry "
            "with id '{1}'".format(repository_name, registry_id),
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
