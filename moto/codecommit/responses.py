import json
import re

from moto.core.responses import BaseResponse
from .models import codecommit_backends
from .exceptions import InvalidRepositoryNameException


class CodeCommitResponse(BaseResponse):
    @property
    def codecommit_backend(self):
        return codecommit_backends[self.region]

    def create_repository(self):
        if not self._is_repository_name_valid(self._get_param("repositoryName")):
            raise InvalidRepositoryNameException()

        repository_metadata = self.codecommit_backend.create_repository(
            self.region, self._get_param("repositoryName"), self._get_param("repositoryDescription")
        )

        return json.dumps({"repositoryMetadata": repository_metadata})

    def get_repository(self):
        if not self._is_repository_name_valid(self._get_param("repositoryName")):
            raise InvalidRepositoryNameException()

        repository_metadata = self.codecommit_backend.get_repository(self._get_param("repositoryName"))

        return json.dumps({"repositoryMetadata": repository_metadata})

    def delete_repository(self):
        if not self._is_repository_name_valid(self._get_param("repositoryName")):
            raise InvalidRepositoryNameException()

        repository_id = self.codecommit_backend.delete_repository(self._get_param("repositoryName"))

        if repository_id:
            return json.dumps({"repositoryId": repository_id})

        return json.dumps({})

    def _is_repository_name_valid(self, repository_name):
        name_regex = re.compile(r"[\w\.-]+")
        result = name_regex.fullmatch(repository_name)
        return result
