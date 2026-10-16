"""Handles incoming workspaces requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import WorkSpacesBackend, workspaces_backends


class WorkSpacesResponse(BaseResponse):
    """Handler for WorkSpaces requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="workspaces")
        self.automated_parameter_parsing = True

    @property
    def workspaces_backend(self) -> WorkSpacesBackend:
        """Return backend instance specific for this region."""
        return workspaces_backends[self.current_account][self.region]

    def create_workspaces(self) -> ActionResult:
        workspaces = self._get_param("Workspaces")
        failed_requests, pending_requests = self.workspaces_backend.create_workspaces(
            workspaces=workspaces,
        )
        return ActionResult(
            {"FailedRequests": failed_requests, "PendingRequests": pending_requests}
        )

    def describe_workspaces(self) -> ActionResult:
        workspace_ids = self._get_param("WorkspaceIds")
        directory_id = self._get_param("DirectoryId")
        user_name = self._get_param("UserName")
        bundle_id = self._get_param("BundleId")
        workspaces = self.workspaces_backend.describe_workspaces(
            workspace_ids=workspace_ids,
            directory_id=directory_id,
            user_name=user_name,
            bundle_id=bundle_id,
        )
        return ActionResult({"Workspaces": [x.to_dict_pending() for x in workspaces]})

    def describe_workspace_directories(self) -> ActionResult:
        directory_ids = self._get_param("DirectoryIds")
        directories = self.workspaces_backend.describe_workspace_directories(
            directory_ids=directory_ids,
        )
        return ActionResult({"Directories": [d.to_dict() for d in directories]})

    def terminate_workspaces(self) -> ActionResult:
        terminate_requests = self._get_param("TerminateWorkspaceRequests")

        failed_requests = self.workspaces_backend.terminate_workspaces(
            terminate_workspace_requests=terminate_requests,
        )

        return ActionResult(failed_requests)

    def register_workspace_directory(self) -> ActionResult:
        directory_id = self._get_param("DirectoryId")
        subnet_ids = self._get_param("SubnetIds")
        enable_self_service = self._get_param("EnableSelfService")
        tenancy = self._get_param("Tenancy")
        tags = self._get_param("Tags")
        self.workspaces_backend.register_workspace_directory(
            directory_id=directory_id,
            subnet_ids=subnet_ids,
            enable_self_service=enable_self_service,
            tenancy=tenancy,
            tags=tags,
        )
        return EmptyResult()

    def modify_workspace_creation_properties(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        workspace_creation_properties = self._get_param("WorkspaceCreationProperties")
        self.workspaces_backend.modify_workspace_creation_properties(
            resource_id=resource_id,
            workspace_creation_properties=workspace_creation_properties,
        )
        return EmptyResult()

    def create_tags(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        tags = self._get_param("Tags")
        self.workspaces_backend.create_tags(
            resource_id=resource_id,
            tags=tags,
        )
        return EmptyResult()

    def describe_tags(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        tag_list = self.workspaces_backend.describe_tags(
            resource_id=resource_id,
        )
        return ActionResult({"TagList": tag_list})

    def describe_client_properties(self) -> ActionResult:
        resource_ids = self._get_param("ResourceIds")
        client_properties_list = self.workspaces_backend.describe_client_properties(
            resource_ids=resource_ids,
        )
        return ActionResult({"ClientPropertiesList": client_properties_list})

    def modify_client_properties(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        client_properties = self._get_param("ClientProperties")
        self.workspaces_backend.modify_client_properties(
            resource_id=resource_id,
            client_properties=client_properties,
        )
        return EmptyResult()

    def create_workspace_image(self) -> ActionResult:
        name = self._get_param("Name")
        description = self._get_param("Description")
        workspace_id = self._get_param("WorkspaceId")
        tags = self._get_param("Tags")
        workspace_image = self.workspaces_backend.create_workspace_image(
            name=name,
            description=description,
            workspace_id=workspace_id,
            tags=tags,
        )
        return ActionResult(workspace_image)

    def describe_workspace_images(self) -> ActionResult:
        image_ids = self._get_param("ImageIds")
        image_type = self._get_param("ImageType")
        images = self.workspaces_backend.describe_workspace_images(
            image_ids=image_ids,
            image_type=image_type,
        )
        return ActionResult({"Images": images})

    def update_workspace_image_permission(self) -> ActionResult:
        image_id = self._get_param("ImageId")
        allow_copy_image = self._get_param("AllowCopyImage")
        shared_account_id = self._get_param("SharedAccountId")
        self.workspaces_backend.update_workspace_image_permission(
            image_id=image_id,
            allow_copy_image=allow_copy_image,
            shared_account_id=shared_account_id,
        )
        return EmptyResult()

    def describe_workspace_image_permissions(self) -> ActionResult:
        image_id = self._get_param("ImageId")
        (
            image_id,
            image_permissions,
        ) = self.workspaces_backend.describe_workspace_image_permissions(
            image_id=image_id,
        )
        return ActionResult(
            {"ImageId": image_id, "ImagePermissions": image_permissions}
        )

    def deregister_workspace_directory(self) -> ActionResult:
        directory_id = self._get_param("DirectoryId")
        self.workspaces_backend.deregister_workspace_directory(
            directory_id=directory_id,
        )
        return EmptyResult()

    def modify_selfservice_permissions(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        selfservice_permissions = self._get_param("SelfservicePermissions")
        self.workspaces_backend.modify_selfservice_permissions(
            resource_id=resource_id,
            selfservice_permissions=selfservice_permissions,
        )
        return EmptyResult()
