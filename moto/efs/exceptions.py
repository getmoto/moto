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


class FileSystemNotFound(EFSError):
    code = 404

    def __init__(self, file_system_id, *args, **kwargs):
        super(FileSystemNotFound, self).__init__(
            "FileSystemNotFound",
            "File system {} does not exist.".format(file_system_id),
            *args,
            **kwargs
        )


class FileSystemInUse(EFSError):
    code = 409

    def __init__(self, msg, *args, **kwargs):
        super(FileSystemInUse, self).__init__("FileSystemInUse", msg, *args, **kwargs)


class MountTargetConflict(EFSError):
    code = 409

    def __init__(self, msg, *args, **kwargs):
        super(MountTargetConflict, self).__init__(
            "MountTargetConflict", msg, *args, **kwargs
        )


class MountTargetNotFound(EFSError):
    code = 404

    def __init__(self, mount_target_id, *args, **kwargs):
        super(MountTargetNotFound, self).__init__(
            "MountTargetNotFound",
            "Mount target '{}' does not exist.".format(mount_target_id),
            *args,
            **kwargs
        )


class BadRequest(EFSError):
    code = 400

    def __init__(self, msg, *args, **kwargs):
        super(BadRequest, self).__init__("BadRequest", msg, *args, **kwargs)


class PolicyNotFound(EFSError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(PolicyNotFound, self).__init__("PolicyNotFound", *args, **kwargs)


class SubnetNotFound(EFSError):
    code = 404

    def __init__(self, subnet_id, *args, **kwargs):
        super(SubnetNotFound, self).__init__(
            "SubnetNotFound",
            "The subnet ID '{}' does not exist".format(subnet_id),
            *args,
            **kwargs
        )


class SecurityGroupNotFound(EFSError):
    code = 404

    def __init__(self, security_group_id, *args, **kwargs):
        super(SecurityGroupNotFound, self).__init__(
            "SecurityGroupNotFound",
            "The SecurityGroup ID '{}' does not exist".format(security_group_id),
            *args,
            **kwargs
        )


class SecurityGroupLimitExceeded(EFSError):
    code = 400

    def __init__(self, msg, *args, **kwargs):
        super(SecurityGroupLimitExceeded, self).__init__(
            "SecurityGroupLimitExceeded", msg, *args, **kwargs
        )
