from __future__ import unicode_literals
import json
from base64 import b64encode
from datetime import datetime
import time

from moto.core.responses import BaseResponse
from .models import ecr_backends, DEFAULT_REGISTRY_ID


class ECRResponse(BaseResponse):
    @property
    def ecr_backend(self):
        return ecr_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def create_repository(self):
        repository_name = self._get_param("repositoryName")
        encryption_config = self._get_param("encryptionConfiguration")
        image_scan_config = self._get_param("imageScanningConfiguration")
        image_tag_mutablility = self._get_param("imageTagMutability")
        tags = self._get_param("tags", [])

        repository = self.ecr_backend.create_repository(
            repository_name=repository_name,
            encryption_config=encryption_config,
            image_scan_config=image_scan_config,
            image_tag_mutablility=image_tag_mutablility,
            tags=tags,
        )
        return json.dumps({"repository": repository.response_object})

    def describe_repositories(self):
        describe_repositories_name = self._get_param("repositoryNames")
        registry_id = self._get_param("registryId")

        repositories = self.ecr_backend.describe_repositories(
            repository_names=describe_repositories_name, registry_id=registry_id
        )
        return json.dumps({"repositories": repositories, "failures": []})

    def delete_repository(self):
        repository_str = self._get_param("repositoryName")
        registry_id = self._get_param("registryId")
        repository = self.ecr_backend.delete_repository(repository_str, registry_id)
        return json.dumps({"repository": repository.response_object})

    def put_image(self):
        repository_str = self._get_param("repositoryName")
        image_manifest = self._get_param("imageManifest")
        image_tag = self._get_param("imageTag")
        image = self.ecr_backend.put_image(repository_str, image_manifest, image_tag)

        return json.dumps({"image": image.response_object})

    def list_images(self):
        repository_str = self._get_param("repositoryName")
        registry_id = self._get_param("registryId")
        images = self.ecr_backend.list_images(repository_str, registry_id)
        return json.dumps(
            {"imageIds": [image.response_list_object for image in images]}
        )

    def describe_images(self):
        repository_str = self._get_param("repositoryName")
        registry_id = self._get_param("registryId")
        image_ids = self._get_param("imageIds")
        images = self.ecr_backend.describe_images(
            repository_str, registry_id, image_ids
        )
        return json.dumps(
            {"imageDetails": [image.response_describe_object for image in images]}
        )

    def batch_check_layer_availability(self):
        if self.is_not_dryrun("BatchCheckLayerAvailability"):
            raise NotImplementedError(
                "ECR.batch_check_layer_availability is not yet implemented"
            )

    def batch_delete_image(self):
        repository_str = self._get_param("repositoryName")
        registry_id = self._get_param("registryId")
        image_ids = self._get_param("imageIds")

        response = self.ecr_backend.batch_delete_image(
            repository_str, registry_id, image_ids
        )
        return json.dumps(response)

    def batch_get_image(self):
        repository_str = self._get_param("repositoryName")
        registry_id = self._get_param("registryId")
        image_ids = self._get_param("imageIds")
        accepted_media_types = self._get_param("acceptedMediaTypes")

        response = self.ecr_backend.batch_get_image(
            repository_str, registry_id, image_ids, accepted_media_types
        )
        return json.dumps(response)

    def can_paginate(self):
        if self.is_not_dryrun("CanPaginate"):
            raise NotImplementedError("ECR.can_paginate is not yet implemented")

    def complete_layer_upload(self):
        if self.is_not_dryrun("CompleteLayerUpload"):
            raise NotImplementedError(
                "ECR.complete_layer_upload is not yet implemented"
            )

    def delete_repository_policy(self):
        if self.is_not_dryrun("DeleteRepositoryPolicy"):
            raise NotImplementedError(
                "ECR.delete_repository_policy is not yet implemented"
            )

    def generate_presigned_url(self):
        if self.is_not_dryrun("GeneratePresignedUrl"):
            raise NotImplementedError(
                "ECR.generate_presigned_url is not yet implemented"
            )

    def get_authorization_token(self):
        registry_ids = self._get_param("registryIds")
        if not registry_ids:
            registry_ids = [DEFAULT_REGISTRY_ID]
        auth_data = []
        for registry_id in registry_ids:
            password = "{}-auth-token".format(registry_id)
            auth_token = b64encode("AWS:{}".format(password).encode("ascii")).decode()
            auth_data.append(
                {
                    "authorizationToken": auth_token,
                    "expiresAt": time.mktime(datetime(2015, 1, 1).timetuple()),
                    "proxyEndpoint": "https://{}.dkr.ecr.{}.amazonaws.com".format(
                        registry_id, self.region
                    ),
                }
            )
        return json.dumps({"authorizationData": auth_data})

    def get_download_url_for_layer(self):
        if self.is_not_dryrun("GetDownloadUrlForLayer"):
            raise NotImplementedError(
                "ECR.get_download_url_for_layer is not yet implemented"
            )

    def get_paginator(self):
        if self.is_not_dryrun("GetPaginator"):
            raise NotImplementedError("ECR.get_paginator is not yet implemented")

    def get_repository_policy(self):
        if self.is_not_dryrun("GetRepositoryPolicy"):
            raise NotImplementedError(
                "ECR.get_repository_policy is not yet implemented"
            )

    def get_waiter(self):
        if self.is_not_dryrun("GetWaiter"):
            raise NotImplementedError("ECR.get_waiter is not yet implemented")

    def initiate_layer_upload(self):
        if self.is_not_dryrun("InitiateLayerUpload"):
            raise NotImplementedError(
                "ECR.initiate_layer_upload is not yet implemented"
            )

    def set_repository_policy(self):
        if self.is_not_dryrun("SetRepositoryPolicy"):
            raise NotImplementedError(
                "ECR.set_repository_policy is not yet implemented"
            )

    def upload_layer_part(self):
        if self.is_not_dryrun("UploadLayerPart"):
            raise NotImplementedError("ECR.upload_layer_part is not yet implemented")

    def list_tags_for_resource(self):
        arn = self._get_param("resourceArn")

        return json.dumps(self.ecr_backend.list_tags_for_resource(arn))

    def tag_resource(self):
        arn = self._get_param("resourceArn")
        tags = self._get_param("tags", [])

        return json.dumps(self.ecr_backend.tag_resource(arn, tags))

    def untag_resource(self):
        arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])

        return json.dumps(self.ecr_backend.untag_resource(arn, tag_keys))

    def put_image_tag_mutability(self):
        registry_id = self._get_param("registryId")
        repository_name = self._get_param("repositoryName")
        image_tag_mutability = self._get_param("imageTagMutability")

        return json.dumps(
            self.ecr_backend.put_image_tag_mutability(
                registry_id=registry_id,
                repository_name=repository_name,
                image_tag_mutability=image_tag_mutability,
            )
        )

    def put_image_scanning_configuration(self):
        registry_id = self._get_param("registryId")
        repository_name = self._get_param("repositoryName")
        image_scan_config = self._get_param("imageScanningConfiguration")

        return json.dumps(
            self.ecr_backend.put_image_scanning_configuration(
                registry_id=registry_id,
                repository_name=repository_name,
                image_scan_config=image_scan_config,
            )
        )
