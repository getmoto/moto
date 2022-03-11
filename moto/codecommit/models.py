from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from datetime import datetime
from moto.core import ACCOUNT_ID
from .exceptions import RepositoryDoesNotExistException, RepositoryNameExistsException
import uuid


class CodeCommit(BaseModel):
    def __init__(self, region, repository_description, repository_name):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        self.repository_metadata = dict()
        self.repository_metadata["repositoryName"] = repository_name
        self.repository_metadata[
            "cloneUrlSsh"
        ] = "ssh://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            region, repository_name
        )
        self.repository_metadata[
            "cloneUrlHttp"
        ] = "https://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            region, repository_name
        )
        self.repository_metadata["creationDate"] = current_date
        self.repository_metadata["lastModifiedDate"] = current_date
        self.repository_metadata["repositoryDescription"] = repository_description
        self.repository_metadata["repositoryId"] = str(uuid.uuid4())
        self.repository_metadata["Arn"] = "arn:aws:codecommit:{0}:{1}:{2}".format(
            region, ACCOUNT_ID, repository_name
        )
        self.repository_metadata["accountId"] = ACCOUNT_ID


class CodeCommitBackend(BaseBackend):
    def __init__(self, region=None):
        self.repositories = {}
        self.region = region

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "codecommit"
        )

    def create_repository(self, repository_name, repository_description):
        repository = self.repositories.get(repository_name)
        if repository:
            raise RepositoryNameExistsException(repository_name)

        self.repositories[repository_name] = CodeCommit(
            self.region, repository_description, repository_name
        )

        return self.repositories[repository_name].repository_metadata

    def get_repository(self, repository_name):
        repository = self.repositories.get(repository_name)
        if not repository:
            raise RepositoryDoesNotExistException(repository_name)

        return repository.repository_metadata

    def delete_repository(self, repository_name):
        repository = self.repositories.get(repository_name)

        if repository:
            self.repositories.pop(repository_name)
            return repository.repository_metadata.get("repositoryId")

        return None


codecommit_backends = BackendDict(CodeCommitBackend, "codecommit")
