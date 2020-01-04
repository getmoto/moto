from moto.core.exceptions import JsonRESTError


class RepositoryNameExistsException(JsonRESTError):
    code = 400

    def __init__(self, repository_name):
        super(RepositoryNameExistsException, self).__init__(
            "RepositoryNameExistsException",
            "Repository named {0} already exists".format(repository_name),
        )


class RepositoryDoesNotExistException(JsonRESTError):
    code = 400

    def __init__(self, repository_name):
        super(RepositoryDoesNotExistException, self).__init__(
            "RepositoryDoesNotExistException",
            "{0} does not exist".format(repository_name),
        )


class InvalidRepositoryNameException(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidRepositoryNameException, self).__init__(
            "InvalidRepositoryNameException",
            "The repository name is not valid. Repository names can be any valid "
            "combination of letters, numbers, "
            "periods, underscores, and dashes between 1 and 100 characters in "
            "length. Names are case sensitive. "
            "For more information, see Limits in the AWS CodeCommit User Guide. ",
        )
