"""Handles incoming pipes requests, invokes methods, returns responses."""

import json
from typing import Any
from urllib.parse import unquote

from moto.core.responses import BaseResponse

from .models import EventBridgePipesBackend, pipes_backends


class EventBridgePipesResponse(BaseResponse):
    """Handler for EventBridgePipes requests and responses."""

    def __init__(self):
        super().__init__(service_name="pipes")

    @property
    def pipes_backend(self) -> EventBridgePipesBackend:
        return pipes_backends[self.current_account][self.region]

    def create_pipe(self):
        body_params = json.loads(self.body) if self.body else {}

        name = body_params.get("Name") or self.uri.split("/")[-1]
        description = body_params.get("Description")
        desired_state = body_params.get("DesiredState")
        source = body_params.get("Source")
        source_parameters = body_params.get("SourceParameters")
        enrichment = body_params.get("Enrichment")
        enrichment_parameters = body_params.get("EnrichmentParameters")
        target = body_params.get("Target")
        target_parameters = body_params.get("TargetParameters")
        role_arn = body_params.get("RoleArn")
        tags = body_params.get("Tags")
        log_configuration = body_params.get("LogConfiguration")
        kms_key_identifier = body_params.get("KmsKeyIdentifier")
        arn, name, desired_state, current_state, creation_time, last_modified_time = (
            self.pipes_backend.create_pipe(
                name=name,
                description=description,
                desired_state=desired_state,
                source=source,
                source_parameters=source_parameters,
                enrichment=enrichment,
                enrichment_parameters=enrichment_parameters,
                target=target,
                target_parameters=target_parameters,
                role_arn=role_arn,
                tags=tags,
                log_configuration=log_configuration,
                kms_key_identifier=kms_key_identifier,
            )
        )
        return json.dumps(
            {
                "Arn": arn,
                "Name": name,
                "DesiredState": desired_state,
                "CurrentState": current_state,
                "CreationTime": creation_time,
                "LastModifiedTime": last_modified_time,
            }
        )

    def describe_pipe(self):
        name = self.uri.split("?")[0].split("/")[-1]
        (
            arn,
            name,
            description,
            desired_state,
            current_state,
            state_reason,
            source,
            source_parameters,
            enrichment,
            enrichment_parameters,
            target,
            target_parameters,
            role_arn,
            tags,
            creation_time,
            last_modified_time,
            log_configuration,
            kms_key_identifier,
        ) = self.pipes_backend.describe_pipe(
            name=name,
        )
        response_dict = {
            "Arn": arn,
            "Name": name,
            "DesiredState": desired_state,
            "CurrentState": current_state,
            "CreationTime": creation_time,
            "LastModifiedTime": last_modified_time,
        }
        if description is not None:
            response_dict["Description"] = description
        if state_reason is not None:
            response_dict["StateReason"] = state_reason
        if source is not None:
            response_dict["Source"] = source
        if source_parameters is not None:
            response_dict["SourceParameters"] = source_parameters
        if enrichment is not None:
            response_dict["Enrichment"] = enrichment
        if enrichment_parameters is not None:
            response_dict["EnrichmentParameters"] = enrichment_parameters
        if target is not None:
            response_dict["Target"] = target
        if target_parameters is not None:
            response_dict["TargetParameters"] = target_parameters
        if role_arn is not None:
            response_dict["RoleArn"] = role_arn
        if tags is not None:
            response_dict["Tags"] = tags
        if log_configuration is not None:
            response_dict["LogConfiguration"] = log_configuration
        if kms_key_identifier is not None:
            response_dict["KmsKeyIdentifier"] = kms_key_identifier
        return json.dumps(response_dict)

    def delete_pipe(self):
        name = self.uri.split("?")[0].split("/")[-1]

        arn, name, desired_state, current_state, creation_time, last_modified_time = (
            self.pipes_backend.delete_pipe(
                name=name,
            )
        )

        return json.dumps(
            {
                "Arn": arn,
                "Name": name,
                "DesiredState": desired_state,
                "CurrentState": current_state,
                "CreationTime": creation_time,
                "LastModifiedTime": last_modified_time,
            }
        )

    def tag_resource(self):
        resource_arn = unquote(self.uri_match.group("resourceArn"))
        body_params = json.loads(self.body) if self.body else {}
        tags = body_params.get("Tags") or body_params.get("tags")
        self.pipes_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return json.dumps({})

    def untag_resource(self):
        resource_arn = unquote(self.uri_match.group("resourceArn"))
        tag_keys = self.querystring.get("tagKeys", [])

        self.pipes_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return json.dumps({})

    def list_pipes(self):
        params = json.loads(self.body) if self.body else {}
        if not params and self.querystring:
            params = {
                k: (v[0] if isinstance(v, list) and len(v) > 0 else v)
                for k, v in self.querystring.items()
            }

        name_prefix = params.get("NamePrefix") or params.get("namePrefix")
        desired_state = params.get("DesiredState") or params.get("desiredState")
        current_state = params.get("CurrentState") or params.get("currentState")
        source_prefix = params.get("SourcePrefix") or params.get("sourcePrefix")
        target_prefix = params.get("TargetPrefix") or params.get("targetPrefix")
        next_token = params.get("NextToken") or params.get("nextToken")
        limit = params.get("Limit") or params.get("limit")
        if limit is not None and limit != "":
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = None

        pipes, next_token = self.pipes_backend.list_pipes(
            name_prefix=name_prefix,
            desired_state=desired_state,
            current_state=current_state,
            source_prefix=source_prefix,
            target_prefix=target_prefix,
            next_token=next_token,
            limit=limit,
        )

        response_dict: dict[str, Any] = {"Pipes": pipes}
        if next_token:
            response_dict["NextToken"] = next_token

        return json.dumps(response_dict)
