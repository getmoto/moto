from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from moto.moto_api._internal import mock_random
from datetime import datetime
from typing import Dict, List, Optional
from .exceptions import RepositoryDoesNotExistException, RepositoryNameExistsException


class CodeCommit(BaseModel):
    def __init__(
        self,
        account_id: str,
        region: str,
        repository_description: str,
        repository_name: str,
    ):
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
        self.repository_metadata["repositoryId"] = str(mock_random.uuid4())
        self.repository_metadata[
            "Arn"
        ] = f"arn:aws:codecommit:{region}:{account_id}:{repository_name}"
        self.repository_metadata["accountId"] = account_id


class CodeCommitBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.repositories: Dict[str, CodeCommit] = {}

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: List[str]
    ) -> List[Dict[str, str]]:
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "codecommit"
        )

    def create_repository(
        self, repository_name: str, repository_description: str
    ) -> Dict[str, str]:
        repository = self.repositories.get(repository_name)
        if repository:
            raise RepositoryNameExistsException(repository_name)

        self.repositories[repository_name] = CodeCommit(
            self.account_id, self.region_name, repository_description, repository_name
        )

        return self.repositories[repository_name].repository_metadata

    def get_repository(self, repository_name: str) -> Dict[str, str]:
        repository = self.repositories.get(repository_name)
        if not repository:
            raise RepositoryDoesNotExistException(repository_name)

        return repository.repository_metadata

    def delete_repository(self, repository_name: str) -> Optional[str]:
        repository = self.repositories.get(repository_name)

        if repository:
            self.repositories.pop(repository_name)
            return repository.repository_metadata.get("repositoryId")

        return None


codecommit_backends = BackendDict(CodeCommitBackend, "codecommit")
