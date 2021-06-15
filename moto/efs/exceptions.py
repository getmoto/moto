from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class EFSError(RESTError):
    pass


class FileSystemAlreadyExists(EFSError):
    code = 409

    def __init__(self, creation_token, *args, **kwargs):
        super(FileSystemAlreadyExists, self).__init__(
            "FileSystemAlreadyExists",
            "File system with {} already exists.".format(creation_token),
            *args,
            **kwargs
        )


class BadRequest(EFSError):
    code = 400

    def __init__(self, msg, *args, **kwargs):
        super(BadRequest, self).__init__("BadRequest", msg, *args, **kwargs)
