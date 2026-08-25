from typing import Any
from urllib.parse import unquote

import xmltodict

from moto.core.responses import TYPE_RESPONSE, BaseResponse, ActionResult, EmptyResult
from moto.core.utils import iso_8601_datetime_with_milliseconds

from .models import CloudFrontBackend, cloudfront_backends, random_id

XMLNS = "http://cloudfront.amazonaws.com/doc/2020-05-31/"


class CloudFrontResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="cloudfront")

    def _get_xml_body(self) -> dict[str, Any]:
        return xmltodict.parse(self.body, dict_constructor=dict, force_list="Path")

    @property
    def backend(self) -> CloudFrontBackend:
        return cloudfront_backends[self.current_account][self.partition]

    def _build_public_key_dict(self, key: Any, include_location: bool = False) -> dict[str, Any]:
        """Build a dict for a public key response."""
        result = {
            "PublicKey": {
                "Id": key.id,
                "CreatedTime": key.created,
                "PublicKeyConfig": {
                    "CallerReference": key.caller_ref,
                    "Name": key.name,
                    "EncodedKey": key.encoded_key,
                    "Comment": ""
                }
            },
            "ETag": key.etag
        }
        if include_location:
            result["Location"] = key.location
        return result

    def _build_public_key_list_dict(self, keys: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of public keys."""
        items = []
        for key in keys:
            items.append({
                "Id": key.id,
                "Name": key.name,
                "CreatedTime": key.created,
                "EncodedKey": key.encoded_key,
                "Comment": ""
            })
        return {
            "PublicKeyList": {
                "MaxItems": 100,
                "Quantity": len(keys),
                "Items": items if items else None
            }
        }

    def _build_invalidation_dict(self, invalidation: Any) -> dict[str, Any]:
        """Build a dict for an invalidation response."""
        paths = invalidation.paths if isinstance(invalidation.paths, list) else [invalidation.paths]
        return {
            "Invalidation": {
                "Id": invalidation.invalidation_id,
                "Status": invalidation.status,
                "CreateTime": invalidation.create_time,
                "InvalidationBatch": {
                    "CallerReference": invalidation.caller_ref,
                    "Paths": {
                        "Quantity": len(paths),
                        "Items": {"Path": paths} if paths else None
                    }
                }
            }
        }

    def _build_invalidation_list_dict(self, invalidations: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of invalidations."""
        items = []
        for inv in invalidations:
            items.append({
                "Id": inv.invalidation_id,
                "CreateTime": inv.create_time,
                "Status": inv.status
            })
        return {
            "InvalidationList": {
                "IsTruncated": False,
                "Items": {"InvalidationSummary": items} if items else None,
                "Marker": "",
                "MaxItems": 100,
                "Quantity": len(invalidations)
            }
        }

    def _build_oac_dict(self, control: Any) -> dict[str, Any]:
        """Build a dict for an Origin Access Control."""
        return {
            "OriginAccessControl": {
                "Id": control.id,
                "OriginAccessControlConfig": {
                    "Name": control.name,
                    "Description": control.description or "",
                    "SigningProtocol": control.signing_protocol,
                    "SigningBehavior": control.signing_behaviour,
                    "OriginAccessControlOriginType": control.origin_type
                }
            }
        }

    def _build_oac_list_dict(self, controls: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of Origin Access Controls."""
        items = []
        for control in controls:
            items.append({
                "Id": control.id,
                "Name": control.name,
                "Description": control.description or "",
                "SigningProtocol": control.signing_protocol,
                "SigningBehavior": control.signing_behaviour,
                "OriginAccessControlOriginType": control.origin_type
            })
        return {
            "OriginAccessControlList": {
                "Items": {"OriginAccessControlSummary": items} if items else None
            }
        }

    def _build_oai_dict(self, oai: Any) -> dict[str, Any]:
        """Build a dict for a CloudFront Origin Access Identity."""
        return {
            "CloudFrontOriginAccessIdentity": {
                "Id": oai.id,
                "S3CanonicalUserId": oai.s3_canonical_id,
                "CloudFrontOriginAccessIdentityConfig": {
                    "CallerReference": oai.caller_reference,
                    "Comment": oai.comment or ""
                }
            }
        }

    def _build_oai_list_dict(self, oais: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of CloudFront Origin Access Identities."""
        items = []
        for oai in oais:
            items.append({
                "Id": oai.id,
                "S3CanonicalUserId": oai.s3_canonical_id,
                "Comment": oai.comment or ""
            })
        return {
            "CloudFrontOriginAccessIdentityList": {
                "IsTruncated": False,
                "Items": {"CloudFrontOriginAccessIdentitySummary": items} if items else None,
                "Marker": "",
                "MaxItems": 100,
                "Quantity": len(oais)
            }
        }

    def _build_policy_dict(self, policy: Any, policy_type: str = "CachePolicy") -> dict[str, Any]:
        """Generic helper to build policy dict."""
        return {
            policy_type: {
                "Id": policy.id if hasattr(policy, 'id') else "",
                f"{policy_type}Config": policy.__dict__ if hasattr(policy, '__dict__') else policy,
                "ETag": policy.etag if hasattr(policy, 'etag') else ""
            }
        }

    def _build_distribution_meta_dict(self, distribution: Any) -> dict[str, Any]:
        """Build distribution metadata dict for list responses."""
        return {
            "Id": distribution.distribution_id,
            "ARN": distribution.arn,
            "Status": distribution.status,
            "LastModifiedTime": distribution.last_modified_time,
            "InProgressInvalidationBatches": distribution.in_progress_invalidation_batches,
            "DomainName": distribution.domain_name,
        }

    def _build_distribution_list_dict(self, distributions: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of distributions."""
        items = []
        for dist in distributions:
            items.append(self._build_distribution_meta_dict(dist))
        return {
            "DistributionList": {
                "IsTruncated": False,
                "Items": {"DistributionSummary": items} if items else None,
                "Marker": "",
                "MaxItems": 100,
                "Quantity": len(distributions)
            }
        }

    def _build_distribution_id_list_dict(self, dist_ids: list[str]) -> dict[str, Any]:
        """Build a dict for a list of distribution IDs."""
        return {
            "DistributionIdList": {
                "Marker": "",
                "MaxItems": 100,
                "IsTruncated": False,
                "Quantity": len(dist_ids),
                "Items": {"DistributionId": dist_ids} if dist_ids else None
            }
        }

    def _build_key_group_dict(self, group: Any, include_location: bool = False) -> dict[str, Any]:
        """Build a dict for a key group."""
        result = {
            "KeyGroup": {
                "Id": group.id,
                "KeyGroupConfig": {
                    "Name": group.name,
                    "Items": {"PublicKey": group.items} if group.items else None
                }
            },
            "ETag": group.etag
        }
        if include_location:
            result["Location"] = group.location
        return result

    def _build_key_group_list_dict(self, groups: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of key groups."""
        items = []
        for group in groups:
            items.append({
                "KeyGroup": {
                    "Id": group.id,
                    "KeyGroupConfig": {
                        "Name": group.name,
                        "Items": {"PublicKey": group.items} if group.items else None
                    }
                }
            })
        return {
            "KeyGroupList": {
                "MaxItems": 100,
                "Quantity": len(groups),
                "Items": {"KeyGroupSummary": items} if items else None
            }
        }

    def _build_function_dict(self, func: Any, include_location: bool = False) -> dict[str, Any]:
        """Build a dict for a function summary."""
        result = {
            "FunctionSummary": {
                "Name": func.name,
                "Status": func.status,
                "FunctionConfig": func.function_config,
                "FunctionMetadata": {
                    "FunctionARN": func.arn,
                    "CreationTime": func.created,
                    "LastModifiedTime": func.last_modified,
                    "Stage": func.stage
                }
            },
            "ETag": func.etag
        }
        if include_location:
            result["Location"] = f"https://cloudfront.amazonaws.com/2020-05-31/function/{func.name}"
        return result

    def _build_function_list_dict(self, funcs: list[Any]) -> dict[str, Any]:
        """Build a dict for a list of functions."""
        items = []
        for func in funcs:
            items.append({
                "Name": func.name,
                "Status": func.status,
                "FunctionConfig": func.function_config,
                "FunctionMetadata": {
                    "FunctionARN": func.arn,
                    "CreationTime": func.created,
                    "LastModifiedTime": func.last_modified,
                    "Stage": func.stage
                }
            })
        return {
            "FunctionList": {
                "MaxItems": 100,
                "Quantity": len(funcs),
                "Items": {"FunctionSummary": items} if items else None
            }
        }

    def _build_policy_response_dict(self, policy: Any, policy_type: str = "CachePolicy", include_location: bool = False) -> dict[str, Any]:
        """Build a dict for a policy response."""
        config_key = f"{policy_type}Config"
        result = {
            policy_type: {
                "Id": policy.id,
                "LastModifiedTime": policy.last_modified_time,
                config_key: {
                    "Name": policy.name,
                    "Comment": policy.comment
                }
            },
            "ETag": policy.etag
        }
        # Add policy-specific config fields
        if hasattr(policy, 'default_ttl'):
            result[policy_type][config_key]["DefaultTTL"] = policy.default_ttl
        if hasattr(policy, 'max_ttl'):
            result[policy_type][config_key]["MaxTTL"] = policy.max_ttl
        if hasattr(policy, 'min_ttl'):
            result[policy_type][config_key]["MinTTL"] = policy.min_ttl
        if include_location:
            policy_type_lower = "".join(["-" + c.lower() if c.isupper() else c for c in policy_type]).lstrip("-")
            result["Location"] = f"https://cloudfront.amazonaws.com/2020-05-31/{policy_type_lower}/{policy.id}"
        return result

    def _build_generic_dict(self, obj: Any, type_name: str, include_location: bool = False) -> dict[str, Any]:
        """Generic helper to build dict for objects with ETag."""
        result = {type_name: obj.__dict__ if hasattr(obj, '__dict__') else obj}
        if hasattr(obj, 'etag'):
            result["ETag"] = obj.etag
        if include_location and hasattr(obj, 'location'):
            result["Location"] = obj.location
        elif include_location and hasattr(obj, 'id'):
            type_lower = "".join(["-" + c.lower() if c.isupper() else c for c in type_name]).lstrip("-")
            result["Location"] = f"https://cloudfront.amazonaws.com/2020-05-31/{type_lower}/{obj.id}"
        return result

    def _build_generic_list_dict(self, items: list[Any], list_type_name: str, item_type_name: str) -> dict[str, Any]:
        """Generic helper to build list dict for objects."""
        return {
            list_type_name: {
                "MaxItems": 100,
                "Quantity": len(items),
                "Items": {item_type_name: [item.__dict__ if hasattr(item, '__dict__') else item for item in items]} if items else None
            }
        }

    def _build_policy_list_dict(self, policies: list[Any], policy_type: str = "CachePolicy") -> dict[str, Any]:
        """Build a dict for a list of policies."""
        list_type = f"{policy_type}List"
        summary_type = f"{policy_type}Summary"
        config_key = f"{policy_type}Config"
        items = []
        for policy in policies:
            items.append({
                "Type": "custom",
                policy_type: {
                    "Id": policy.id,
                    "LastModifiedTime": policy.last_modified_time,
                    config_key: {
                        "Name": policy.name,
                        "Comment": policy.comment
                    }
                }
            })
            # Add policy-specific fields to config
            if hasattr(policy, 'default_ttl'):
                items[-1][policy_type][config_key]["DefaultTTL"] = policy.default_ttl
            if hasattr(policy, 'max_ttl'):
                items[-1][policy_type][config_key]["MaxTTL"] = policy.max_ttl
            if hasattr(policy, 'min_ttl'):
                items[-1][policy_type][config_key]["MinTTL"] = policy.min_ttl
        return {
            list_type: {
                "MaxItems": 100,
                "Quantity": len(policies),
                "Items": {summary_type: items} if items else None
            }
        }

    @classmethod
    def tagging(cls, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE | ActionResult | EmptyResult:  # type: ignore
        response = cls()
        response.setup_class(request, full_url, headers)
        operation = response._get_param("Operation")
        if operation == "Tag":
            result = response.tag_resource()
            if isinstance(result, EmptyResult):
                return 204, {}, ""
            return result
        if operation == "Untag":
            result = response.untag_resource()
            if isinstance(result, EmptyResult):
                return 204, {}, ""
            return result
        if request.method == "GET":
            return response.list_tags_for_resource()

    def create_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        if "DistributionConfigWithTags" in params:
            config = params.get("DistributionConfigWithTags")
            tags = (config.get("Tags", {}).get("Items") or {}).get("Tag", [])  # type: ignore[union-attr]
            if not isinstance(tags, list):
                tags = [tags]
        else:
            config = params
            tags = []
        distribution_config = config.get("DistributionConfig")  # type: ignore[union-attr]
        distribution, location, e_tag = self.backend.create_distribution(
            distribution_config=distribution_config,
            tags=tags,
        )
        template = self.response_template(CREATE_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=distribution, xmlns=XMLNS)
        headers = {"ETag": e_tag, "Location": location}
        return 200, headers, response

    def list_distributions(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        distributions = self.backend.list_distributions()
        return ActionResult(self._build_distribution_list_dict(distributions))

    def delete_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        distribution_id = self.path.split("/")[-1]
        if_match = self._get_param("If-Match")
        self.backend.delete_distribution(distribution_id, if_match)
        return EmptyResult()

    def get_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        distribution_id = self.path.split("/")[-1]
        dist, etag = self.backend.get_distribution(distribution_id)
        template = self.response_template(GET_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=dist, xmlns=XMLNS)
        return 200, {"ETag": etag}, response

    def get_distribution_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        distribution_config, etag = self.backend.get_distribution_config(dist_id)
        template = self.response_template(GET_DISTRIBUTION_CONFIG_TEMPLATE)
        response = template.render(distribution=distribution_config, xmlns=XMLNS)
        return 200, {"ETag": etag}, response

    def update_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        params = self._get_xml_body()
        dist_config = params.get("DistributionConfig")
        if_match = self.headers["If-Match"]
        dist, location, e_tag = self.backend.update_distribution(
            dist_config=dist_config,  # type: ignore[arg-type]
            _id=dist_id,
            if_match=if_match,
        )
        template = self.response_template(UPDATE_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=dist, xmlns=XMLNS)
        headers = {"ETag": e_tag, "Location": location}
        return 200, headers, response

    def create_invalidation(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        params = self._get_xml_body()["InvalidationBatch"]
        paths = ((params.get("Paths") or {}).get("Items") or {}).get("Path") or []
        caller_ref = params.get("CallerReference")

        invalidation = self.backend.create_invalidation(dist_id, paths, caller_ref)  # type: ignore[arg-type]
        result = self._build_invalidation_dict(invalidation)
        result["Location"] = invalidation.location
        return ActionResult(result)

    def list_invalidations(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        invalidations = self.backend.list_invalidations(dist_id)
        return ActionResult(self._build_invalidation_list_dict(invalidations))

    def get_invalidation(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        pathItems = self.path.split("/")
        dist_id = pathItems[-3]
        id = pathItems[-1]
        invalidation = self.backend.get_invalidation(dist_id, id)
        return ActionResult(self._build_invalidation_dict(invalidation))

    def list_tags_for_resource(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        resource = unquote(self._get_param("Resource"))
        tags = self.backend.list_tags_for_resource(resource=resource)["Tags"]
        items = []
        for tag in tags:
            items.append({"Key": tag["Key"], "Value": tag["Value"]})
        return ActionResult({
            "Tags": {
                "Items": {"Tag": items} if items else None
            }
        })

    def tag_resource(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        resource = unquote(self._get_param("Resource"))
        params = self._get_xml_body()
        tags = params.get("Tags", {}).get("Items", {}).get("Tag", [])
        if not isinstance(tags, list):
            tags = [tags]
        self.backend.tag_resource(resource=resource, tags=tags)
        return EmptyResult()

    def untag_resource(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        resource = unquote(self._get_param("Resource"))
        params = self._get_xml_body()
        tag_keys_data = params.get("TagKeys", {}).get("Items", {}).get("Key", [])
        if not isinstance(tag_keys_data, list):
            tag_keys_data = [tag_keys_data]
        self.backend.untag_resource(resource=resource, tag_keys=tag_keys_data)
        return EmptyResult()

    def create_origin_access_control(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("OriginAccessControlConfig", {})
        config.pop("@xmlns", None)
        control = self.backend.create_origin_access_control(config)
        result = self._build_oac_dict(control)
        result["ETag"] = control.etag
        return ActionResult(result)

    def get_origin_access_control(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        control_id = self.path.split("/")[-1]
        control = self.backend.get_origin_access_control(control_id)
        result = self._build_oac_dict(control)
        result["ETag"] = control.etag
        return ActionResult(result)

    def list_origin_access_controls(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        controls = self.backend.list_origin_access_controls()
        return ActionResult(self._build_oac_list_dict(controls))

    def update_origin_access_control(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        control_id = self.path.split("/")[-2]
        config = self._get_xml_body().get("OriginAccessControlConfig", {})
        config.pop("@xmlns", None)
        control = self.backend.update_origin_access_control(control_id, config)
        result = self._build_oac_dict(control)
        result["ETag"] = control.etag
        return ActionResult(result)

    def delete_origin_access_control(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        control_id = self.path.split("/")[-1]
        self.backend.delete_origin_access_control(control_id)
        return EmptyResult()

    def create_public_key(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body()["PublicKeyConfig"]
        caller_ref = config["CallerReference"]
        name = config["Name"]
        encoded_key = config["EncodedKey"]
        public_key = self.backend.create_public_key(
            caller_ref=caller_ref, name=name, encoded_key=encoded_key
        )
        return ActionResult(self._build_public_key_dict(public_key, include_location=True))

    def get_public_key(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        key_id = self.parsed_url.path.split("/")[-1]
        public_key = self.backend.get_public_key(key_id=key_id)
        return ActionResult(self._build_public_key_dict(public_key))

    def delete_public_key(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        key_id = self.parsed_url.path.split("/")[-1]
        self.backend.delete_public_key(key_id=key_id)
        return EmptyResult()

    def list_public_keys(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        keys = self.backend.list_public_keys()
        return ActionResult(self._build_public_key_list_dict(keys))

    def create_key_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("KeyGroupConfig") or {}
        config.pop("@xmlns", None)
        name = config.get("Name", "")
        items_wrapper = config.get("Items") or {}
        items = items_wrapper.get("PublicKey") or []
        if isinstance(items, str):
            # Serialized as a string if there is only one item
            items = [items]

        key_group = self.backend.create_key_group(name=name, items=items)
        return ActionResult(self._build_key_group_dict(key_group, include_location=True))

    def get_key_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        group_id = self.parsed_url.path.split("/")[-1]
        key_group = self.backend.get_key_group(group_id=group_id)
        return ActionResult(self._build_key_group_dict(key_group))

    def list_key_groups(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        groups = self.backend.list_key_groups()
        return ActionResult(self._build_key_group_list_dict(groups))

    def update_key_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        group_id = self.parsed_url.path.split("/")[-1]
        config = self._get_xml_body().get("KeyGroupConfig") or {}
        config.pop("@xmlns", None)
        name = config.get("Name", "")
        items = (config.get("Items") or {}).get("PublicKey") or []
        if isinstance(items, str):
            items = [items]
        key_group = self.backend.update_key_group(
            group_id=group_id, name=name, items=items
        )
        return ActionResult(self._build_key_group_dict(key_group))

    def delete_key_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        group_id = self.parsed_url.path.split("/")[-1]
        self.backend.delete_key_group(group_id=group_id)
        return EmptyResult()

    # CloudFront Functions
    def create_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body().get("CreateFunctionRequest", {})
        params.pop("@xmlns", None)
        name = params.get("Name", "")
        function_code = params.get("FunctionCode", "")
        function_config = params.get("FunctionConfig", {})
        func = self.backend.create_function(
            name=name,
            function_code=function_code,
            function_config=function_config,
        )
        return ActionResult(self._build_function_dict(func, include_location=True))

    def describe_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-2]
        func = self.backend.describe_function(name)
        return ActionResult(self._build_function_dict(func))

    def get_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        func = self.backend.get_function(name)
        headers = {"ETag": func.etag, "Content-Type": "application/octet-stream"}
        return 200, headers, func.function_code

    def update_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        if_match = self.headers.get("If-Match", "")
        params = self._get_xml_body().get("UpdateFunctionRequest", {})
        params.pop("@xmlns", None)
        function_code = params.get("FunctionCode", "")
        function_config = params.get("FunctionConfig", {})
        func = self.backend.update_function(
            name=name,
            function_code=function_code,
            function_config=function_config,
            if_match=if_match,
        )
        return ActionResult(self._build_function_dict(func))

    def delete_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        if_match = self.headers.get("If-Match", "")
        self.backend.delete_function(name=name, if_match=if_match)
        return EmptyResult()

    def publish_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-2]
        if_match = self.headers.get("If-Match", "")
        func = self.backend.publish_function(name=name, if_match=if_match)
        return ActionResult(self._build_function_dict(func))

    def list_functions(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        functions = self.backend.list_functions()
        return ActionResult(self._build_function_list_dict(functions))

    # Cache Policies
    def create_cache_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("CachePolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.create_cache_policy(config)
        return ActionResult(self._build_policy_response_dict(policy, "CachePolicy", include_location=True))

    def get_cache_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        policy = self.backend.get_cache_policy(policy_id)
        return ActionResult(self._build_policy_response_dict(policy, "CachePolicy"))

    def update_cache_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        config = self._get_xml_body().get("CachePolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.update_cache_policy(policy_id, config)
        return ActionResult(self._build_policy_response_dict(policy, "CachePolicy"))

    def delete_cache_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        self.backend.delete_cache_policy(policy_id)
        return EmptyResult()

    def list_cache_policies(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policies = self.backend.list_cache_policies()
        return ActionResult(self._build_policy_list_dict(policies, "CachePolicy"))

    # Response Headers Policies
    def create_response_headers_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("ResponseHeadersPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.create_response_headers_policy(config)
        return ActionResult(self._build_policy_response_dict(policy, "ResponseHeadersPolicy", include_location=True))

    def get_response_headers_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        policy = self.backend.get_response_headers_policy(policy_id)
        return ActionResult(self._build_policy_response_dict(policy, "ResponseHeadersPolicy"))

    def update_response_headers_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        config = self._get_xml_body().get("ResponseHeadersPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.update_response_headers_policy(policy_id, config)
        return ActionResult(self._build_policy_response_dict(policy, "ResponseHeadersPolicy"))

    def delete_response_headers_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        self.backend.delete_response_headers_policy(policy_id)
        return EmptyResult()

    def list_response_headers_policies(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policies = self.backend.list_response_headers_policies()
        return ActionResult(self._build_policy_list_dict(policies, "ResponseHeadersPolicy"))

    # Origin Access Identities
    def create_cloud_front_origin_access_identity(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        config = params.get("CloudFrontOriginAccessIdentityConfig", {})
        config.pop("@xmlns", None)
        caller_reference = config.get("CallerReference", "")
        comment = config.get("Comment", "")
        oai = self.backend.create_cloud_front_origin_access_identity(
            caller_reference=caller_reference, comment=comment
        )
        result = self._build_oai_dict(oai)
        result["Location"] = f"https://cloudfront.amazonaws.com/2020-05-31/origin-access-identity/cloudfront/{oai.id}"
        result["ETag"] = oai.etag
        return ActionResult(result)

    def get_cloud_front_origin_access_identity(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        identity_id = self.path.split("/")[-1]
        oai = self.backend.get_cloud_front_origin_access_identity(identity_id)
        result = self._build_oai_dict(oai)
        result["ETag"] = oai.etag
        return ActionResult(result)

    def get_cloud_front_origin_access_identity_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        identity_id = self.path.split("/")[-2]
        oai = self.backend.get_cloud_front_origin_access_identity_config(identity_id)
        result = {
            "CloudFrontOriginAccessIdentityConfig": {
                "CallerReference": oai.caller_reference,
                "Comment": oai.comment or ""
            },
            "ETag": oai.etag
        }
        return ActionResult(result)

    def update_cloud_front_origin_access_identity(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        identity_id = self.path.split("/")[-2]
        params = self._get_xml_body()
        config = params.get("CloudFrontOriginAccessIdentityConfig", {})
        config.pop("@xmlns", None)
        oai = self.backend.update_cloud_front_origin_access_identity(
            identity_id, config.get("CallerReference", ""), config.get("Comment", "")
        )
        result = self._build_oai_dict(oai)
        result["ETag"] = oai.etag
        return ActionResult(result)

    def delete_cloud_front_origin_access_identity(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        identity_id = self.path.split("/")[-1]
        self.backend.delete_cloud_front_origin_access_identity(identity_id)
        return EmptyResult()

    def list_cloud_front_origin_access_identities(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        oais = self.backend.list_cloud_front_origin_access_identities()
        return ActionResult(self._build_oai_list_dict(oais))

    # Streaming Distributions
    def create_streaming_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        if "StreamingDistributionConfigWithTags" in params:
            wrapper = params["StreamingDistributionConfigWithTags"] or {}
            wrapper.pop("@xmlns", None)
            config = wrapper.get("StreamingDistributionConfig") or {}
            tags_items = (wrapper.get("Tags") or {}).get("Items") or {}
            tags = tags_items.get("Tag") or []
            if not isinstance(tags, list):
                tags = [tags]
        else:
            config = params.get("StreamingDistributionConfig") or {}
            tags = []
        config.pop("@xmlns", None)
        dist = self.backend.create_streaming_distribution(config, tags)
        return ActionResult(self._build_generic_dict(dist, "StreamingDistribution", include_location=True))

    def create_streaming_distribution_with_tags(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return self.create_streaming_distribution()

    def get_streaming_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-1]
        dist = self.backend.get_streaming_distribution(dist_id)
        return ActionResult(self._build_generic_dict(dist, "StreamingDistribution"))

    def get_streaming_distribution_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        dist = self.backend.get_streaming_distribution_config(dist_id)
        result = {
            "StreamingDistributionConfig": dist.__dict__ if hasattr(dist, '__dict__') else dist,
            "ETag": dist.etag
        }
        return ActionResult(result)

    def update_streaming_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        params = self._get_xml_body()
        config = params.get("StreamingDistributionConfig", {})
        config.pop("@xmlns", None)
        dist = self.backend.update_streaming_distribution(dist_id, config)
        return ActionResult(self._build_generic_dict(dist, "StreamingDistribution"))

    def delete_streaming_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-1]
        self.backend.delete_streaming_distribution(dist_id)
        return EmptyResult()

    def list_streaming_distributions(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dists = self.backend.list_streaming_distributions()
        return ActionResult(self._build_generic_list_dict(dists, "StreamingDistributionList", "StreamingDistributionSummary"))

    # Origin Request Policies
    def create_origin_request_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("OriginRequestPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.create_origin_request_policy(config)
        return ActionResult(self._build_policy_response_dict(policy, "OriginRequestPolicy", include_location=True))

    def get_origin_request_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        policy = self.backend.get_origin_request_policy(policy_id)
        return ActionResult(self._build_policy_response_dict(policy, "OriginRequestPolicy"))

    def get_origin_request_policy_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-2]
        policy = self.backend.get_origin_request_policy_config(policy_id)
        result = {
            "OriginRequestPolicyConfig": policy.__dict__ if hasattr(policy, '__dict__') else policy,
            "ETag": policy.etag
        }
        return ActionResult(result)

    def update_origin_request_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        config = self._get_xml_body().get("OriginRequestPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.update_origin_request_policy(policy_id, config)
        return ActionResult(self._build_policy_response_dict(policy, "OriginRequestPolicy"))

    def delete_origin_request_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        self.backend.delete_origin_request_policy(policy_id)
        return EmptyResult()

    def list_origin_request_policies(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policies = self.backend.list_origin_request_policies()
        return ActionResult(self._build_policy_list_dict(policies, "OriginRequestPolicy"))

    # Field Level Encryption
    def create_field_level_encryption_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("FieldLevelEncryptionConfig", {})
        config.pop("@xmlns", None)
        fle = self.backend.create_field_level_encryption_config(config)
        return ActionResult(self._build_generic_dict(fle, "FieldLevelEncryption", include_location=True))

    def get_field_level_encryption(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config_id = self.path.split("/")[-1]
        fle = self.backend.get_field_level_encryption(config_id)
        return ActionResult(self._build_generic_dict(fle, "FieldLevelEncryption"))

    def get_field_level_encryption_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config_id = self.path.split("/")[-2]
        fle = self.backend.get_field_level_encryption_config(config_id)
        result = {
            "FieldLevelEncryptionConfig": fle.__dict__ if hasattr(fle, '__dict__') else fle,
            "ETag": fle.etag
        }
        return ActionResult(result)

    def update_field_level_encryption_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config_id = self.path.split("/")[-2]
        config = self._get_xml_body().get("FieldLevelEncryptionConfig", {})
        config.pop("@xmlns", None)
        fle = self.backend.update_field_level_encryption_config(config_id, config)
        return ActionResult(self._build_generic_dict(fle, "FieldLevelEncryption"))

    def delete_field_level_encryption_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config_id = self.path.split("/")[-1]
        self.backend.delete_field_level_encryption_config(config_id)
        return EmptyResult()

    def list_field_level_encryption_configs(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        configs = self.backend.list_field_level_encryption_configs()
        return ActionResult(self._build_generic_list_dict(configs, "FieldLevelEncryptionList", "FieldLevelEncryptionSummary"))

    # Field Level Encryption Profiles
    def create_field_level_encryption_profile(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("FieldLevelEncryptionProfileConfig", {})
        config.pop("@xmlns", None)
        profile = self.backend.create_field_level_encryption_profile(config)
        return ActionResult(self._build_generic_dict(profile, "FieldLevelEncryptionProfile", include_location=True))

    def get_field_level_encryption_profile(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        profile_id = self.path.split("/")[-1]
        profile = self.backend.get_field_level_encryption_profile(profile_id)
        return ActionResult(self._build_generic_dict(profile, "FieldLevelEncryptionProfile"))

    def get_field_level_encryption_profile_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        profile_id = self.path.split("/")[-2]
        profile = self.backend.get_field_level_encryption_profile_config(profile_id)
        result = {
            "FieldLevelEncryptionProfileConfig": profile.__dict__ if hasattr(profile, '__dict__') else profile,
            "ETag": profile.etag
        }
        return ActionResult(result)

    def update_field_level_encryption_profile(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        profile_id = self.path.split("/")[-2]
        config = self._get_xml_body().get("FieldLevelEncryptionProfileConfig", {})
        config.pop("@xmlns", None)
        profile = self.backend.update_field_level_encryption_profile(profile_id, config)
        return ActionResult(self._build_generic_dict(profile, "FieldLevelEncryptionProfile"))

    def delete_field_level_encryption_profile(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        profile_id = self.path.split("/")[-1]
        self.backend.delete_field_level_encryption_profile(profile_id)
        return EmptyResult()

    def list_field_level_encryption_profiles(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        profiles = self.backend.list_field_level_encryption_profiles()
        return ActionResult(self._build_generic_list_dict(profiles, "FieldLevelEncryptionProfileList", "FieldLevelEncryptionProfileSummary"))

    # Continuous Deployment Policies
    def create_continuous_deployment_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        config = self._get_xml_body().get("ContinuousDeploymentPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.create_continuous_deployment_policy(config)
        return ActionResult(self._build_generic_dict(policy, "ContinuousDeploymentPolicy", include_location=True))

    def get_continuous_deployment_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        policy = self.backend.get_continuous_deployment_policy(policy_id)
        return ActionResult(self._build_generic_dict(policy, "ContinuousDeploymentPolicy"))

    def get_continuous_deployment_policy_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-2]
        policy = self.backend.get_continuous_deployment_policy_config(policy_id)
        result = {
            "ContinuousDeploymentPolicyConfig": policy.__dict__ if hasattr(policy, '__dict__') else policy,
            "ETag": policy.etag
        }
        return ActionResult(result)

    def update_continuous_deployment_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-2]
        config = self._get_xml_body().get("ContinuousDeploymentPolicyConfig", {})
        config.pop("@xmlns", None)
        policy = self.backend.update_continuous_deployment_policy(policy_id, config)
        return ActionResult(self._build_generic_dict(policy, "ContinuousDeploymentPolicy"))

    def delete_continuous_deployment_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        self.backend.delete_continuous_deployment_policy(policy_id)
        return EmptyResult()

    def list_continuous_deployment_policies(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policies = self.backend.list_continuous_deployment_policies()
        return ActionResult(self._build_generic_list_dict(policies, "ContinuousDeploymentPolicyList", "ContinuousDeploymentPolicySummary"))

    # Monitoring Subscriptions
    def create_monitoring_subscription(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        params = self._get_xml_body()
        ms_config = params.get("MonitoringSubscription", {})
        ms_config.pop("@xmlns", None)
        realtime_config = ms_config.get("RealtimeMetricsSubscriptionConfig", {})
        sub = self.backend.create_monitoring_subscription(dist_id, realtime_config)
        return ActionResult(self._build_generic_dict(sub, "MonitoringSubscription"))

    def get_monitoring_subscription(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        sub = self.backend.get_monitoring_subscription(dist_id)
        return ActionResult(self._build_generic_dict(sub, "MonitoringSubscription"))

    def delete_monitoring_subscription(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        self.backend.delete_monitoring_subscription(dist_id)
        return EmptyResult()

    # Realtime Log Configs
    def _parse_realtime_body(self) -> dict[str, Any]:
        """Parse body as XML (botocore sends XML for CloudFront rest-xml protocol)."""
        body = self._get_xml_body()
        # Unwrap the request wrapper element if present
        for key in (
            "CreateRealtimeLogConfigRequest",
            "UpdateRealtimeLogConfigRequest",
            "GetRealtimeLogConfigRequest",
            "DeleteRealtimeLogConfigRequest",
        ):
            if key in body:
                body = body[key] or {}
                break
        body.pop("@xmlns", None)
        return body

    @staticmethod
    def _extract_endpoints(body: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract EndPoints from parsed XML body."""
        eps_raw = (body.get("EndPoints") or {}).get("member") or []
        if isinstance(eps_raw, dict):
            eps_raw = [eps_raw]
        end_points = []
        for ep in eps_raw:
            entry: dict[str, Any] = {"StreamType": ep.get("StreamType", "Kinesis")}
            kinesis = ep.get("KinesisStreamConfig") or {}
            if kinesis:
                entry["KinesisStreamConfig"] = {
                    "RoleARN": kinesis.get("RoleARN", ""),
                    "StreamARN": kinesis.get("StreamARN", ""),
                }
            end_points.append(entry)
        return end_points

    @staticmethod
    def _extract_fields(body: dict[str, Any]) -> list[str]:
        """Extract Fields from parsed XML body."""
        fields_raw = (body.get("Fields") or {}).get("Field") or []
        if isinstance(fields_raw, str):
            fields_raw = [fields_raw]
        return fields_raw

    def create_realtime_log_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._parse_realtime_body()
        name = body.get("Name", "")
        sampling_rate = int(body.get("SamplingRate", 100))
        end_points = self._extract_endpoints(body)
        fields = self._extract_fields(body)
        config = self.backend.create_realtime_log_config(
            name=name,
            sampling_rate=sampling_rate,
            end_points=end_points,
            fields=fields,
        )
        return ActionResult(self._build_generic_dict(config, "RealtimeLogConfig"))

    def get_realtime_log_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._parse_realtime_body() if self.body else {}
        config = self.backend.get_realtime_log_config(
            name=body.get("Name"), arn=body.get("ARN")
        )
        return ActionResult(self._build_generic_dict(config, "RealtimeLogConfig"))

    def update_realtime_log_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._parse_realtime_body() if self.body else {}
        sr = body.get("SamplingRate")
        end_points = self._extract_endpoints(body) if "EndPoints" in body else None
        fields = self._extract_fields(body) if "Fields" in body else None
        config = self.backend.update_realtime_log_config(
            name=body.get("Name"),
            arn=body.get("ARN"),
            sampling_rate=int(sr) if sr is not None else None,
            end_points=end_points,
            fields=fields,
        )
        return ActionResult(self._build_generic_dict(config, "RealtimeLogConfig"))

    def delete_realtime_log_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._parse_realtime_body() if self.body else {}
        self.backend.delete_realtime_log_config(
            name=body.get("Name"), arn=body.get("ARN")
        )
        return EmptyResult()

    def list_realtime_log_configs(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        configs = self.backend.list_realtime_log_configs()
        return ActionResult(self._build_generic_list_dict(configs, "RealtimeLogConfigList", "RealtimeLogConfigSummary"))

    # Distribution query operations
    def list_distributions_by_web_acl_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        web_acl_id = self.path.split("/")[-1]
        distributions = self.backend.list_distributions_by_web_acl_id(web_acl_id)
        return ActionResult(self._build_distribution_list_dict(distributions))

    def list_distributions_by_web_a_c_l_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return self.list_distributions_by_web_acl_id()

    def list_distributions_by_cache_policy_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        dist_ids = self.backend.list_distributions_by_cache_policy_id(policy_id)
        return ActionResult(self._build_distribution_id_list_dict(dist_ids))

    def list_distributions_by_origin_request_policy_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        dist_ids = self.backend.list_distributions_by_origin_request_policy_id(
            policy_id
        )
        return ActionResult(self._build_distribution_id_list_dict(dist_ids))

    def list_distributions_by_response_headers_policy_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-1]
        dist_ids = self.backend.list_distributions_by_response_headers_policy_id(
            policy_id
        )
        return ActionResult(self._build_distribution_id_list_dict(dist_ids))

    def list_distributions_by_key_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        key_group_id = self.path.split("/")[-1]
        dist_ids = self.backend.list_distributions_by_key_group(key_group_id)
        return ActionResult(self._build_distribution_id_list_dict(dist_ids))

    def list_distributions_by_realtime_log_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._parse_realtime_body() if self.body else {}
        distributions = self.backend.list_distributions_by_realtime_log_config(
            body.get("RealtimeLogConfigArn", "")
        )
        return ActionResult(self._build_distribution_list_dict(distributions))

    # Config-only getters
    def get_cache_policy_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-2]
        policy = self.backend.get_cache_policy_config(policy_id)
        result = {
            "CachePolicyConfig": policy.__dict__ if hasattr(policy, '__dict__') else policy,
            "ETag": policy.etag
        }
        return ActionResult(result)

    def get_key_group_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        group_id = self.path.split("/")[-2]
        group = self.backend.get_key_group_config(group_id)
        result = {
            "KeyGroupConfig": {
                "Name": group.name,
                "Items": {"PublicKey": group.items}
            },
            "ETag": group.etag
        }
        return ActionResult(result)

    def get_origin_access_control_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        control_id = self.path.split("/")[-2]
        control = self.backend.get_origin_access_control_config(control_id)
        result = {
            "OriginAccessControlConfig": {
                "Name": control.name,
                "Description": control.description or "",
                "SigningProtocol": control.signing_protocol,
                "SigningBehavior": control.signing_behaviour,
                "OriginAccessControlOriginType": control.origin_type
            },
            "ETag": control.etag
        }
        return ActionResult(result)

    def get_public_key_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        key_id = self.path.split("/")[-2]
        key = self.backend.get_public_key_config(key_id)
        result = {
            "PublicKeyConfig": {
                "CallerReference": key.caller_ref,
                "Name": key.name,
                "EncodedKey": key.encoded_key,
                "Comment": ""
            },
            "ETag": key.etag
        }
        return ActionResult(result)

    def get_response_headers_policy_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        policy_id = self.path.split("/")[-2]
        policy = self.backend.get_response_headers_policy_config(policy_id)
        result = {
            "ResponseHeadersPolicyConfig": policy.__dict__ if hasattr(policy, '__dict__') else policy,
            "ETag": policy.etag
        }
        return ActionResult(result)

    def update_public_key(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        key_id = self.path.split("/")[-2]
        key = self.backend.update_public_key(key_id)
        return ActionResult(self._build_public_key_dict(key))

    # Alias operations
    def associate_alias(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        alias = self._get_param("Alias")
        self.backend.associate_alias(dist_id, alias)
        return EmptyResult()

    def test_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-2]
        result = self.backend.test_function(name, event_object="")
        return ActionResult({
            "TestResult": {
                "FunctionOutput": '{"response":{"statusCode":200}}',
                "ComputeUtilization": 12
            }
        })

    def list_conflicting_aliases(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self._get_param("DistributionId")
        alias = self._get_param("Alias")
        items = self.backend.list_conflicting_aliases(dist_id, alias)
        return ActionResult({
            "ConflictingAliasesList": {
                "IsTruncated": False,
                "Items": {"ConflictingAlias": items} if items else None,
                "MaxItems": 100,
                "Quantity": len(items) if items else 0
            }
        })

    def create_distribution_with_tags(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return self.create_distribution()

    # Stub operations for newer/niche APIs
    def associate_distribution_web_acl(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    def copy_distribution(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        distribution_id = self.path.split("/")[-1]
        dist, etag = self.backend.get_distribution(distribution_id)
        return ActionResult({"Distribution": {"Id": dist.distribution_id, "ETag": etag}})

    # Alias for Moto dispatch compatibility
    associate_distribution_web_a_c_l = associate_distribution_web_acl

    def disassociate_distribution_web_acl(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    disassociate_distribution_web_a_c_l = disassociate_distribution_web_acl

    def associate_distribution_tenant_web_acl(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    associate_distribution_tenant_web_a_c_l = associate_distribution_tenant_web_acl

    def disassociate_distribution_tenant_web_acl(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    disassociate_distribution_tenant_web_a_c_l = (
        disassociate_distribution_tenant_web_acl
    )

    def create_key_value_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        body = self._get_xml_body()
        req = body.get("CreateKeyValueStoreRequest") or body
        if isinstance(req, dict):
            req.pop("@xmlns", None)
        else:
            req = {}
        name = req.get("Name", "")
        comment = req.get("Comment", "")
        kvs = self.backend.create_key_value_store(name=name, comment=comment)
        return ActionResult(self._build_generic_dict(kvs, "KeyValueStore", include_location=True))

    def describe_key_value_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        kvs = self.backend.describe_key_value_store(name)
        return ActionResult(self._build_generic_dict(kvs, "KeyValueStore"))

    def delete_key_value_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        self.backend.delete_key_value_store(name)
        return EmptyResult()

    def update_key_value_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        body = self._get_xml_body()
        req = body.get("UpdateKeyValueStoreRequest") or body
        if isinstance(req, dict):
            req.pop("@xmlns", None)
        else:
            req = {}
        comment = req.get("Comment", "")
        kvs = self.backend.update_key_value_store(name=name, comment=comment)
        return ActionResult(self._build_generic_dict(kvs, "KeyValueStore"))

    def list_key_value_stores(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        stores = self.backend.list_key_value_stores()
        return ActionResult(self._build_generic_list_dict(stores, "KeyValueStoreList", "KeyValueStoreSummary"))

    # VPC Origins
    def create_vpc_origin(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateVpcOriginRequest", params)
        config = root.get("VpcOriginEndpointConfig", {})
        config.pop("@xmlns", None)
        vo = self.backend.create_vpc_origin(config)
        return ActionResult(self._build_generic_dict(vo, "VpcOrigin", include_location=True))

    def get_vpc_origin(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        vpc_id = self.path.split("/")[-1]
        vo = self.backend.get_vpc_origin(vpc_id)
        return ActionResult(self._build_generic_dict(vo, "VpcOrigin"))

    def delete_vpc_origin(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        vpc_id = self.path.split("/")[-1]
        self.backend.delete_vpc_origin(vpc_id)
        return EmptyResult()

    def update_vpc_origin(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        vpc_id = self.path.split("/")[-1]
        params = self._get_xml_body()
        root = params.get("UpdateVpcOriginRequest", params)
        config = root.get("VpcOriginEndpointConfig", {})
        config.pop("@xmlns", None)
        vo = self.backend.update_vpc_origin(vpc_id, config)
        return ActionResult(self._build_generic_dict(vo, "VpcOrigin"))

    def list_vpc_origins(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        origins = self.backend.list_vpc_origins()
        return ActionResult(self._build_generic_list_dict(origins, "VpcOriginList", "VpcOriginSummary"))

    # Trust Stores
    def create_trust_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateTrustStoreRequest", params)
        root.pop("@xmlns", None)
        name = root.get("Name", "")
        ts = self.backend.create_trust_store(name)
        return ActionResult(self._build_generic_dict(ts, "TrustStore", include_location=True))

    def get_trust_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        store_id = self.path.split("/")[-1]
        ts = self.backend.get_trust_store(store_id)
        return ActionResult(self._build_generic_dict(ts, "TrustStore"))

    def delete_trust_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        store_id = self.path.split("/")[-1]
        self.backend.delete_trust_store(store_id)
        return EmptyResult()

    def update_trust_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        store_id = self.path.split("/")[-1]
        ts = self.backend.update_trust_store(store_id)
        return ActionResult(self._build_generic_dict(ts, "TrustStore"))

    def list_trust_stores(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        stores = self.backend.list_trust_stores()
        return ActionResult(self._build_generic_list_dict(stores, "TrustStoreList", "TrustStoreSummary"))

    # Resource Policy
    def get_resource_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"ResourcePolicy": {}, "ETag": random_id(length=14)})

    def put_resource_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"ResourcePolicy": {}, "ETag": random_id(length=14)})

    def delete_resource_policy(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    # Anycast IP Lists
    def create_anycast_ip_list(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateAnycastIpListRequest", params)
        root.pop("@xmlns", None)
        name = root.get("Name", "")
        aip = self.backend.create_anycast_ip_list(name)
        return ActionResult(self._build_generic_dict(aip, "AnycastIpList", include_location=True))

    def get_anycast_ip_list(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        list_id = self.path.split("/")[-1]
        aip = self.backend.get_anycast_ip_list(list_id)
        return ActionResult(self._build_generic_dict(aip, "AnycastIpList"))

    def delete_anycast_ip_list(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        list_id = self.path.split("/")[-1]
        self.backend.delete_anycast_ip_list(list_id)
        return EmptyResult()

    def update_anycast_ip_list(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return self.get_anycast_ip_list()

    def list_anycast_ip_lists(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        lists = self.backend.list_anycast_ip_lists()
        return ActionResult(self._build_generic_list_dict(lists, "AnycastIpListList", "AnycastIpListSummary"))

    # Connection Groups
    def create_connection_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateConnectionGroupRequest", params)
        root.pop("@xmlns", None)
        name = root.get("Name", "")
        cg = self.backend.create_connection_group(name)
        return ActionResult(self._build_generic_dict(cg, "ConnectionGroup", include_location=True))

    def get_connection_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        cg_id = self.path.split("/")[-1]
        cg = self.backend.get_connection_group(cg_id)
        return ActionResult(self._build_generic_dict(cg, "ConnectionGroup"))

    def delete_connection_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        cg_id = self.path.split("/")[-1]
        self.backend.delete_connection_group(cg_id)
        return EmptyResult()

    def update_connection_group(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        cg_id = self.path.split("/")[-1]
        cg = self.backend.get_connection_group(cg_id)
        cg.etag = random_id(length=14)
        return ActionResult(self._build_generic_dict(cg, "ConnectionGroup"))

    def list_connection_groups(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        groups = self.backend.list_connection_groups()
        return ActionResult(self._build_generic_list_dict(groups, "ConnectionGroupList", "ConnectionGroupSummary"))

    def get_connection_group_by_routing_endpoint(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        template = self.response_template(ERROR_TEMPLATE)
        return 404, {}, template.render(code="NoSuchResource", message="The specified resource does not exist.", xmlns=XMLNS)

    # Distribution Tenants
    def create_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateDistributionTenantRequest", params)
        root.pop("@xmlns", None)
        name = root.get("Name", "")
        dist_id = root.get("DistributionId", "")
        dt = self.backend.create_distribution_tenant(name, dist_id)
        return ActionResult(self._build_generic_dict(dt, "DistributionTenant", include_location=True))

    def get_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dt_id = self.path.split("/")[-1]
        dt = self.backend.get_distribution_tenant(dt_id)
        return ActionResult(self._build_generic_dict(dt, "DistributionTenant"))

    def delete_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dt_id = self.path.split("/")[-1]
        self.backend.delete_distribution_tenant(dt_id)
        return EmptyResult()

    def update_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dt_id = self.path.split("/")[-1]
        dt = self.backend.get_distribution_tenant(dt_id)
        dt.etag = random_id(length=14)
        return ActionResult(self._build_generic_dict(dt, "DistributionTenant"))

    def list_distribution_tenants(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        tenants = self.backend.list_distribution_tenants()
        return ActionResult(self._build_generic_list_dict(tenants, "DistributionTenantList", "DistributionTenantSummary"))

    def get_distribution_tenant_by_domain(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        template = self.response_template(ERROR_TEMPLATE)
        return 404, {}, template.render(code="NoSuchResource", message="The specified resource does not exist.", xmlns=XMLNS)

    def list_distribution_tenants_by_customization(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_generic_list_dict([], "DistributionTenantList", "DistributionTenantSummary"))

    def create_invalidation_for_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        inv_id = random_id()
        return ActionResult({"TenantInvalidation": {"Id": inv_id}})

    def get_invalidation_for_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        inv_id = self.path.split("/")[-1]
        return ActionResult({"TenantInvalidation": {"Id": inv_id}})

    def list_invalidations_for_distribution_tenant(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"TenantInvalidationList": {"Items": None, "Quantity": 0}})

    # Connection Functions
    def create_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        params = self._get_xml_body()
        root = params.get("CreateConnectionFunctionRequest", params)
        root.pop("@xmlns", None)
        name = root.get("Name", "")
        cf = self.backend.create_connection_function(name)
        return ActionResult(self._build_generic_dict(cf, "ConnectionFunction", include_location=True))

    def get_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        cf = self.backend.get_connection_function(name)
        return ActionResult(self._build_generic_dict(cf, "ConnectionFunction"))

    def describe_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-2]
        cf = self.backend.get_connection_function(name)
        return ActionResult(self._build_generic_dict(cf, "ConnectionFunction"))

    def delete_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        self.backend.delete_connection_function(name)
        return EmptyResult()

    def update_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-1]
        cf = self.backend.get_connection_function(name)
        cf.etag = random_id(length=14)
        return ActionResult(self._build_generic_dict(cf, "ConnectionFunction"))

    def publish_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        name = self.path.split("/")[-2]
        cf = self.backend.get_connection_function(name)
        cf.stage = "LIVE"
        cf.etag = random_id(length=14)
        return ActionResult(self._build_generic_dict(cf, "ConnectionFunction"))

    def test_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"TestConnectionFunctionResult": {"Status": "Success"}})

    def list_connection_functions(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        funcs = self.backend.list_connection_functions()
        return ActionResult(self._build_generic_list_dict(funcs, "ConnectionFunctionList", "ConnectionFunctionSummary"))

    def list_distributions_by_anycast_ip_list_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_id_list_dict([]))

    def list_distributions_by_connection_function(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_id_list_dict([]))

    def list_distributions_by_connection_mode(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_list_dict([]))

    def list_distributions_by_owned_resource(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_id_list_dict([]))

    def list_distributions_by_trust_store(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_id_list_dict([]))

    def list_distributions_by_vpc_origin_id(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult(self._build_distribution_id_list_dict([]))

    def list_domain_conflicts(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"DomainConflictsList": {"Items": None, "Quantity": 0}})

    def update_distribution_with_staging_config(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        dist_id = self.path.split("/")[-2]
        dist, etag = self.backend.get_distribution(dist_id)
        template = self.response_template(GET_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=dist, xmlns=XMLNS)
        return 200, {"ETag": etag}, response

    def update_domain_association(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return EmptyResult()

    def get_managed_certificate_details(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"ManagedCertificateDetails": {"DomainName": "example.com", "ValidationMethod": "DNS"}})

    def verify_dns_configuration(self) -> TYPE_RESPONSE | ActionResult | EmptyResult:
        return ActionResult({"VerifyDnsConfigurationResult": {"Verified": True}})


DIST_META_TEMPLATE = """
    <Id>{{ distribution.distribution_id }}</Id>
    <ARN>{{ distribution.arn }}</ARN>
    <Status>{{ distribution.status }}</Status>
    <LastModifiedTime>{{ distribution.last_modified_time }}</LastModifiedTime>
    <InProgressInvalidationBatches>{{ distribution.in_progress_invalidation_batches }}</InProgressInvalidationBatches>
    <DomainName>{{ distribution.domain_name }}</DomainName>
"""


DIST_CONFIG_TEMPLATE = """
      <CallerReference>{{ distribution.distribution_config.caller_reference }}</CallerReference>
      <Aliases>
        <Quantity>{{ distribution.distribution_config.aliases|length }}</Quantity>
        <Items>
          {% for alias  in distribution.distribution_config.aliases %}
            <CNAME>{{ alias }}</CNAME>
          {% endfor %}
        </Items>
      </Aliases>
      <DefaultRootObject>{{ distribution.distribution_config.default_root_object }}</DefaultRootObject>
      <Origins>
        <Quantity>{{ distribution.distribution_config.origins|length }}</Quantity>
        <Items>
          {% for origin  in distribution.distribution_config.origins %}
          <Origin>
            <Id>{{ origin.id }}</Id>
            <DomainName>{{ origin.domain_name }}</DomainName>
            <OriginPath>{{ origin.origin_path }}</OriginPath>
            <CustomHeaders>
              <Quantity>{{ origin.custom_headers|length }}</Quantity>
              <Items>
                {% for header  in origin.custom_headers %}
                  <OriginCustomHeader>
                  <HeaderName>{{ header['HeaderName'] }}</HeaderName>
                  <HeaderValue>{{ header['HeaderValue'] }}</HeaderValue>
                  </OriginCustomHeader>
                {% endfor %}
              </Items>
            </CustomHeaders>
            {% if origin.s3_access_identity %}
            <S3OriginConfig>
              <OriginAccessIdentity>{{ origin.s3_access_identity }}</OriginAccessIdentity>
            </S3OriginConfig>
            {% endif %}
            {% if origin.custom_origin %}
            <CustomOriginConfig>
              <HTTPPort>{{ origin.custom_origin.http_port }}</HTTPPort>
              <HTTPSPort>{{ origin.custom_origin.https_port }}</HTTPSPort>
              <OriginProtocolPolicy>{{ origin.custom_origin.protocol_policy }}</OriginProtocolPolicy>
              <OriginSslProtocols>
                <Quantity>{{ origin.custom_origin.ssl_protocols|length }}</Quantity>
                <Items>
                  {% for protocol  in origin.custom_origin.ssl_protocols %}
                  <SslProtocol>{{ protocol }}</SslProtocol>
                  {% endfor %}
                </Items>
              </OriginSslProtocols>
              <OriginReadTimeout>{{ origin.custom_origin.read_timeout }}</OriginReadTimeout>
              <OriginKeepaliveTimeout>{{ origin.custom_origin.keep_alive }}</OriginKeepaliveTimeout>
            </CustomOriginConfig>
            {% endif %}
            <ConnectionAttempts>{{ origin.connection_attempts }}</ConnectionAttempts>
            <ConnectionTimeout>{{ origin.connection_timeout }}</ConnectionTimeout>
            {% if origin.origin_shield %}
            <OriginShield>
              <Enabled>{{ origin.origin_shield.get("Enabled") }}</Enabled>
              <OriginShieldRegion>{{ origin.origin_shield.get("OriginShieldRegion") }}</OriginShieldRegion>
            </OriginShield>
            {% else %}
            <OriginShield>
              <Enabled>false</Enabled>
            </OriginShield>
            {% endif %}
            </Origin>
          {% endfor %}
        </Items>
      </Origins>
      <OriginGroups>
        <Quantity>{{ distribution.distribution_config.origin_groups|length }}</Quantity>
        {% if distribution.distribution_config.origin_groups %}
        <Items>
          {% for origin_group  in distribution.distribution_config.origin_groups %}
            <Id>{{ origin_group.id }}</Id>
            <FailoverCriteria>
              <StatusCodes>
                <Quantity>{{ origin_group.failover_criteria.status_codes.quantity }}</Quantity>
                <Items>
                  {% for status_code_list  in origin_group_list.failover_criteria.status_codes.StatusCodeList %}
                    <StatusCode>{{ status_code_list.status_code }}</StatusCode>
                  {% endfor %}
                </Items>
              </StatusCodes>
            </FailoverCriteria>
            <Members>
              <Quantity>{{ origin_group.members.quantity }}</Quantity>
              <Items>
                {% for origin_group_member_list  in origin_group.members.OriginGroupMemberList %}
                  <OriginId>{{ origin_group_member_list.origin_id }}</OriginId>
                {% endfor %}
              </Items>
            </Members>
          {% endfor %}
        </Items>
        {% endif %}
      </OriginGroups>
      <DefaultCacheBehavior>
        <TargetOriginId>{{ distribution.distribution_config.default_cache_behavior.target_origin_id }}</TargetOriginId>
        <TrustedSigners>
          <Enabled>{{ 'true' if distribution.distribution_config.default_cache_behavior.trusted_signers.acct_nums|length > 0 else 'false' }}</Enabled>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.trusted_signers.acct_nums|length }}</Quantity>
          <Items>
            {% for aws_account_number  in distribution.distribution_config.default_cache_behavior.trusted_signers.acct_nums %}
              <AwsAccountNumber>{{ aws_account_number }}</AwsAccountNumber>
            {% endfor %}
          </Items>
        </TrustedSigners>
        <TrustedKeyGroups>
          <Enabled>{{ 'true' if distribution.distribution_config.default_cache_behavior.trusted_key_groups.group_ids|length > 0 else 'false' }}</Enabled>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.trusted_key_groups.group_ids|length }}</Quantity>
          <Items>
            {% for group_id  in distribution.distribution_config.default_cache_behavior.trusted_key_groups.group_ids %}
              <KeyGroup>{{ group_id }}</KeyGroup>
            {% endfor %}
          </Items>
        </TrustedKeyGroups>
        <ViewerProtocolPolicy>{{ distribution.distribution_config.default_cache_behavior.viewer_protocol_policy }}</ViewerProtocolPolicy>
        <AllowedMethods>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.allowed_methods|length }}</Quantity>
          <Items>
            {% for method in distribution.distribution_config.default_cache_behavior.allowed_methods %}
            <Method>{{ method }}</Method>
            {% endfor %}
          </Items>
          <CachedMethods>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.cached_methods|length }}</Quantity>
            <Items>
              {% for method in distribution.distribution_config.default_cache_behavior.cached_methods %}
              <Method>{{ method }}</Method>
              {% endfor %}
            </Items>
          </CachedMethods>
        </AllowedMethods>
        <SmoothStreaming>{{ distribution.distribution_config.default_cache_behavior.smooth_streaming }}</SmoothStreaming>
        <Compress>{{ 'true' if distribution.distribution_config.default_cache_behavior.compress else 'false' }}</Compress>
        <LambdaFunctionAssociations>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.lambda_function_associations|length }}</Quantity>
          {% if distribution.distribution_config.default_cache_behavior.lambda_function_associations %}
          <Items>
            {% for func in distribution.distribution_config.default_cache_behavior.lambda_function_associations %}
              <LambdaFunctionARN>{{ func.arn }}</LambdaFunctionARN>
              <EventType>{{ func.event_type }}</EventType>
              <IncludeBody>{{ func.include_body }}</IncludeBody>
            {% endfor %}
          </Items>
          {% endif %}
        </LambdaFunctionAssociations>
        <FunctionAssociations>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.function_associations|length }}</Quantity>
          {% if distribution.distribution_config.default_cache_behavior.function_associations %}
          <Items>
            {% for func in distribution.distribution_config.default_cache_behavior.function_associations %}
              <FunctionARN>{{ func.arn }}</FunctionARN>
              <EventType>{{ func.event_type }}</EventType>
            {% endfor %}
          </Items>
          {% endif %}
        </FunctionAssociations>
        <FieldLevelEncryptionId>{{ distribution.distribution_config.default_cache_behavior.field_level_encryption_id }}</FieldLevelEncryptionId>
        <RealtimeLogConfigArn>{{ distribution.distribution_config.default_cache_behavior.realtime_log_config_arn }}</RealtimeLogConfigArn>
        <CachePolicyId>{{ distribution.distribution_config.default_cache_behavior.cache_policy_id }}</CachePolicyId>
        <OriginRequestPolicyId>{{ distribution.distribution_config.default_cache_behavior.origin_request_policy_id }}</OriginRequestPolicyId>
        <ResponseHeadersPolicyId>{{ distribution.distribution_config.default_cache_behavior.response_headers_policy_id }}</ResponseHeadersPolicyId>
        <ForwardedValues>
          <QueryString>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.query_string }}</QueryString>
          <Cookies>
            <Forward>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.cookie_forward }}</Forward>
            <WhitelistedNames>
              <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.whitelisted_names|length }}</Quantity>
              <Items>
                {% for name  in distribution.distribution_config.default_cache_behavior.forwarded_values.whitelisted_names %}
                  <Name>{{ name }}</Name>
                {% endfor %}
              </Items>
            </WhitelistedNames>
          </Cookies>
          <Headers>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.headers|length }}</Quantity>
            <Items>
              {% for h  in distribution.distribution_config.default_cache_behavior.forwarded_values.headers %}
                <Name>{{ h }}</Name>
              {% endfor %}
            </Items>
          </Headers>
          <QueryStringCacheKeys>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.query_string_cache_keys|length }}</Quantity>
            <Items>
              {% for key  in distribution.distribution_config.default_cache_behavior.forwarded_values.query_string_cache_keys %}
                <Name>{{ key }}</Name>
              {% endfor %}
            </Items>
          </QueryStringCacheKeys>
        </ForwardedValues>
        <MinTTL>{{ distribution.distribution_config.default_cache_behavior.min_ttl }}</MinTTL>
        <DefaultTTL>{{ distribution.distribution_config.default_cache_behavior.default_ttl }}</DefaultTTL>
        <MaxTTL>{{ distribution.distribution_config.default_cache_behavior.max_ttl }}</MaxTTL>
      </DefaultCacheBehavior>
      <CacheBehaviors>
        <Quantity>{{ distribution.distribution_config.cache_behaviors|length }}</Quantity>
        {% if distribution.distribution_config.cache_behaviors %}
        <Items>
          {% for behaviour in distribution.distribution_config.cache_behaviors %}
            <CacheBehavior>
                <PathPattern>{{ behaviour.path_pattern }}</PathPattern>
                <TargetOriginId>{{ behaviour.target_origin_id }}</TargetOriginId>
                <TrustedSigners>
                  <Enabled>{{ 'true' if behaviour.trusted_signers.acct_nums|length > 0 else 'false' }}</Enabled>
                  <Quantity>{{ behaviour.trusted_signers.acct_nums | length }}</Quantity>
                  <Items>
                    {% for account_nr  in behaviour.trusted_signers.acct_nums %}
                      <AwsAccountNumber>{{ account_nr }}</AwsAccountNumber>
                    {% endfor %}
                  </Items>
                </TrustedSigners>
                <TrustedKeyGroups>
                  <Enabled>{{ 'true' if behaviour.trusted_key_groups.group_ids|length > 0 else 'false' }}</Enabled>
                  <Quantity>{{ behaviour.trusted_key_groups.group_ids | length }}</Quantity>
                  <Items>
                    {% for group_id  in behaviour.trusted_key_groups.group_ids %}
                      <KeyGroup>{{ group_id }}</KeyGroup>
                    {% endfor %}
                  </Items>
                </TrustedKeyGroups>
                <ViewerProtocolPolicy>{{ behaviour.viewer_protocol_policy }}</ViewerProtocolPolicy>
                <AllowedMethods>
                  <Quantity>{{ behaviour.allowed_methods | length }}</Quantity>
                  <Items>
                    {% for method in behaviour.allowed_methods %}<Method>{{ method }}</Method>{% endfor %}
                  </Items>
                  <CachedMethods>
                    <Quantity>{{ behaviour.cached_methods|length }}</Quantity>
                    <Items>
                      {% for method in behaviour.cached_methods %}<Method>{{ method }}</Method>{% endfor %}
                    </Items>
                  </CachedMethods>
                </AllowedMethods>
                <SmoothStreaming>{{ behaviour.smooth_streaming }}</SmoothStreaming>
                <Compress>{{ behaviour.compress }}</Compress>
                <LambdaFunctionAssociations>
                  <Quantity>{{ behaviour.lambda_function_associations | length }}</Quantity>
                  <Items>
                    {% for lambda_function_association_list in behaviour.lambda_function_associations %}
                      <LambdaFunctionARN>{{ LambdaFunctionARN }}</LambdaFunctionARN>
                      <EventType>{{ EventType }}</EventType>
                      <IncludeBody>{{ lambda_function_association_list.include_body }}</IncludeBody>
                    {% endfor %}
                  </Items>
                </LambdaFunctionAssociations>
                <FunctionAssociations>
                  <Quantity>{{ behaviour.function_associations | length }}</Quantity>
                  <Items>
                    {% for function_association_list  in behaviour.function_associations %}
                      <FunctionARN>{{ FunctionARN }}</FunctionARN>
                      <EventType>{{ EventType }}</EventType>
                    {% endfor %}
                  </Items>
                </FunctionAssociations>
                <FieldLevelEncryptionId>{{ behaviour.field_level_encryption_id }}</FieldLevelEncryptionId>
                <RealtimeLogConfigArn>{{ behaviour.realtime_log_config_arn }}</RealtimeLogConfigArn>
                <CachePolicyId>{{ behaviour.cache_policy_id }}</CachePolicyId>
                <OriginRequestPolicyId>{{ behaviour.origin_request_policy_id }}</OriginRequestPolicyId>
                <ResponseHeadersPolicyId>{{ behaviour.response_headers_policy_id }}</ResponseHeadersPolicyId>
                <ForwardedValues>
                  <QueryString>{{ behaviour.forwarded_values.query_string }}</QueryString>
                  <Cookies>
                    <Forward>{{ behaviour.forwarded_values.cookie_forward }}</Forward>
                    <WhitelistedNames>
                      <Quantity>{{ behaviour.forwarded_values.whitelisted_names| length }}</Quantity>
                      <Items>
                        {% for wl_name in behaviour.forwarded_values.whitelisted_names %}
                          <Name>{{ wl_name }}</Name>
                        {% endfor %}
                      </Items>
                    </WhitelistedNames>
                  </Cookies>
                  <Headers>
                    <Quantity>{{ behaviour.forwarded_values.headers | length }}</Quantity>
                    <Items>
                      {% for header_list in behaviour.forwarded_values.headers %}
                        <Name>{{ header_list.name }}</Name>
                      {% endfor %}
                    </Items>
                  </Headers>
                  <QueryStringCacheKeys>
                    <Quantity>{{ behaviour.forwarded_values.query_string_cache_keys | length }}</Quantity>
                    <Items>
                      {% for query_string_cache_keys_list in behaviour.forwarded_values.query_string_cache_keys %}
                        <Name>{{ query_string_cache_keys_list.name }}</Name>
                      {% endfor %}
                    </Items>
                  </QueryStringCacheKeys>
                </ForwardedValues>
                <MinTTL>{{ behaviour.min_ttl }}</MinTTL>
                <DefaultTTL>{{ behaviour.default_ttl }}</DefaultTTL>
                <MaxTTL>{{ behaviour.max_ttl }}</MaxTTL>
            </CacheBehavior>
          {% endfor %}
        </Items>
        {% endif %}
      </CacheBehaviors>
      <CustomErrorResponses>
        <Quantity>{{ distribution.distribution_config.custom_error_responses|length }}</Quantity>
        {% if distribution.distribution_config.custom_error_responses %}
        <Items>
          {% for response  in distribution.distribution_config.custom_error_responses %}
            <ErrorCode>{{ response.error_code }}</ErrorCode>
            <ResponsePagePath>{{ response.response_page_path }}</ResponsePagePath>
            <ResponseCode>{{ response.response_code }}</ResponseCode>
            <ErrorCachingMinTTL>{{ response.error_caching_min_ttl }}</ErrorCachingMinTTL>
          {% endfor %}
        </Items>
        {% endif %}
      </CustomErrorResponses>
      <Comment>{{ distribution.distribution_config.comment }}</Comment>
      <Logging>
        <Enabled>{{ distribution.distribution_config.logging.enabled }}</Enabled>
        <IncludeCookies>{{ distribution.distribution_config.logging.include_cookies }}</IncludeCookies>
        <Bucket>{{ distribution.distribution_config.logging.bucket }}</Bucket>
        <Prefix>{{ distribution.distribution_config.logging.prefix }}</Prefix>
      </Logging>
      <PriceClass>{{ distribution.distribution_config.price_class }}</PriceClass>
      <Enabled>{{ distribution.distribution_config.enabled }}</Enabled>
      <ViewerCertificate>
        <CloudFrontDefaultCertificate>{{ 'true' if distribution.distribution_config.viewer_certificate.cloud_front_default_certificate == True else 'false' }}</CloudFrontDefaultCertificate>
        <IAMCertificateId>{{ distribution.distribution_config.viewer_certificate.iam_certificate_id }}</IAMCertificateId>
        <ACMCertificateArn>{{ distribution.distribution_config.viewer_certificate.acm_certificate_arn }}</ACMCertificateArn>
        <SSLSupportMethod>{{ distribution.distribution_config.viewer_certificate.ssl_support_method }}</SSLSupportMethod>
        <MinimumProtocolVersion>{{ distribution.distribution_config.viewer_certificate.min_protocol_version }}</MinimumProtocolVersion>
        <Certificate>{{ distribution.distribution_config.viewer_certificate.certificate }}</Certificate>
        <CertificateSource>{{ distribution.distribution_config.viewer_certificate.certificate_source }}</CertificateSource>
      </ViewerCertificate>
      <Restrictions>
        <GeoRestriction>
          <RestrictionType>{{ distribution.distribution_config.geo_restriction._type }}</RestrictionType>
          <Quantity>{{ distribution.distribution_config.geo_restriction.restrictions|length }}</Quantity>
          {% if distribution.distribution_config.geo_restriction.restrictions %}
          <Items>
            {% for location  in distribution.distribution_config.geo_restriction.restrictions %}
              <Location>{{ location }}</Location>
            {% endfor %}
          </Items>
          {% endif %}
        </GeoRestriction>
      </Restrictions>
      <WebACLId>{{ distribution.distribution_config.web_acl_id }}</WebACLId>
      <HttpVersion>{{ distribution.distribution_config.http_version }}</HttpVersion>
      <IsIPV6Enabled>{{ 'true' if distribution.distribution_config.is_ipv6_enabled else 'false' }}</IsIPV6Enabled>
"""


DISTRIBUTION_TEMPLATE = (
    DIST_META_TEMPLATE
    + """
    <ActiveTrustedSigners>
      <Enabled>{{ distribution.active_trusted_signers.enabled }}</Enabled>
      <Quantity>{{ distribution.active_trusted_signers.quantity }}</Quantity>
      <Items>
        {% for signer  in distribution.active_trusted_signers.signers %}
          <AwsAccountNumber>{{ signer.aws_account_number }}</AwsAccountNumber>
          <KeyPairIds>
            <Quantity>{{ signer.key_pair_ids.quantity }}</Quantity>
            <Items>
              {% for key_pair_id_list  in signer.key_pair_ids.KeyPairIdList %}
                <KeyPairId>{{ key_pair_id_list.key_pair_id }}</KeyPairId>
              {% endfor %}
            </Items>
          </KeyPairIds>
        {% endfor %}
      </Items>
    </ActiveTrustedSigners>
    <ActiveTrustedKeyGroups>
      <Enabled>{{ distribution.active_trusted_key_groups.enabled }}</Enabled>
      <Quantity>{{ distribution.active_trusted_key_groups.quantity }}</Quantity>
      <Items>
        {% for kg_key_pair_id  in distribution.active_trusted_key_groups.kg_key_pair_ids %}
          <KeyGroupId>{{ kg_key_pair_id.key_group_id }}</KeyGroupId>
          <KeyPairIds>
            <Quantity>{{ kg_key_pair_id.key_pair_ids.quantity }}</Quantity>
            <Items>
              {% for key_pair_id_list  in kg_key_pair_ids_list.key_pair_ids.KeyPairIdList %}
                <KeyPairId>{{ key_pair_id_list.key_pair_id }}</KeyPairId>
              {% endfor %}
            </Items>
          </KeyPairIds>
        {% endfor %}
      </Items>
    </ActiveTrustedKeyGroups>
    <DistributionConfig>
      """
    + DIST_CONFIG_TEMPLATE
    + """
    </DistributionConfig>
    <AliasICPRecordals>
      {% for a  in distribution.alias_icp_recordals %}
        <CNAME>{{ a.cname }}</CNAME>
        <ICPRecordalStatus>{{ a.status }}</ICPRecordalStatus>
      {% endfor %}
    </AliasICPRecordals>"""
)

CREATE_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <CreateDistributionResult xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </CreateDistributionResult>
"""
)

GET_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <Distribution xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </Distribution>
"""
)

GET_DISTRIBUTION_CONFIG_TEMPLATE = (
    """<?xml version="1.0"?>
  <DistributionConfig>
"""
    + DIST_CONFIG_TEMPLATE
    + """
  </DistributionConfig>
"""
)


LIST_TEMPLATE = (
    """<?xml version="1.0"?>
<DistributionList xmlns="http://cloudfront.amazonaws.com/doc/2020-05-31/">
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ distributions|length }}</Quantity>
  {% if distributions %}
  <Items>
      {% for distribution in distributions %}
      <DistributionSummary>
      """
    + DIST_META_TEMPLATE
    + """
      """
    + DIST_CONFIG_TEMPLATE
    + """
      </DistributionSummary>
      {% endfor %}
  </Items>
  {% endif %}
</DistributionList>"""
)

UPDATE_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <Distribution xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </Distribution>
"""
)

CREATE_INVALIDATION_TEMPLATE = """<?xml version="1.0"?>
<Invalidation>
  <Id>{{ invalidation.invalidation_id }}</Id>
  <Status>{{ invalidation.status }}</Status>
  <CreateTime>{{ invalidation.create_time }}</CreateTime>
  <InvalidationBatch>
    <CallerReference>{{ invalidation.caller_ref }}</CallerReference>
    <Paths>
      <Quantity>{{ invalidation.paths|length }}</Quantity>
      <Items>
        {% for path in invalidation.paths %}<Path>{{ path }}</Path>{% endfor %}
      </Items>
    </Paths>
  </InvalidationBatch>
</Invalidation>
"""

GET_INVALIDATION_TEMPLATE = CREATE_INVALIDATION_TEMPLATE

INVALIDATIONS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<InvalidationList>
   <IsTruncated>false</IsTruncated>
   {% if invalidations %}
   <Items>
      {% for invalidation in invalidations %}
      <InvalidationSummary>
         <CreateTime>{{ invalidation.create_time }}</CreateTime>
         <Id>{{ invalidation.invalidation_id }}</Id>
         <Status>{{ invalidation.status }}</Status>
      </InvalidationSummary>
      {% endfor %}
   </Items>
   {% endif %}
   <Marker></Marker>
   <MaxItems>100</MaxItems>
   <Quantity>{{ invalidations|length }}</Quantity>
</InvalidationList>
"""

TAGS_TEMPLATE = """<?xml version="1.0"?>
<Tags>
  <Items>
    {% for tag in tags %}
      <Tag>
      <Key>{{ tag["Key"] }}</Key>
      <Value>{{ tag["Value"] }}</Value>
      </Tag>
    {% endfor %}
  </Items>
</Tags>
"""


ORIGIN_ACCESS_CONTROl = """<?xml version="1.0"?>
<OriginAccessControl>
  <Id>{{ control.id }}</Id>
  <OriginAccessControlConfig>
    <Name>{{ control.name }}</Name>
    {% if control.description %}
    <Description>{{ control.description }}</Description>
    {% endif %}
    <SigningProtocol>{{ control.signing_protocol }}</SigningProtocol>
    <SigningBehavior>{{ control.signing_behaviour }}</SigningBehavior>
    <OriginAccessControlOriginType>{{ control.origin_type }}</OriginAccessControlOriginType>
  </OriginAccessControlConfig>
</OriginAccessControl>
"""


LIST_ORIGIN_ACCESS_CONTROl = """<?xml version="1.0"?>
<OriginAccessControlList>
  <Items>
  {% for control in controls %}
    <OriginAccessControlSummary>
      <Id>{{ control.id }}</Id>
      <Name>{{ control.name }}</Name>
      {% if control.description %}
      <Description>{{ control.description }}</Description>
      {% endif %}
      <SigningProtocol>{{ control.signing_protocol }}</SigningProtocol>
      <SigningBehavior>{{ control.signing_behaviour }}</SigningBehavior>
      <OriginAccessControlOriginType>{{ control.origin_type }}</OriginAccessControlOriginType>
    </OriginAccessControlSummary>
  {% endfor %}
  </Items>
</OriginAccessControlList>
"""


PUBLIC_KEY_TEMPLATE = """<?xml version="1.0"?>
<PublicKey>
    <Id>{{ key.id }}</Id>
    <CreatedTime>{{ key.created }}</CreatedTime>
    <PublicKeyConfig>
        <CallerReference>{{ key.caller_ref }}</CallerReference>
        <Name>{{ key.name }}</Name>
        <EncodedKey>{{ key.encoded_key }}</EncodedKey>
        <Comment></Comment>
    </PublicKeyConfig>
</PublicKey>
"""


LIST_PUBLIC_KEYS = """<?xml version="1.0"?>
<PublicKeyList>
    <MaxItems>100</MaxItems>
    <Quantity>{{ keys|length }}</Quantity>
    {% if keys %}
    <Items>
        {% for key in keys %}
        <PublicKeySummary>
            <Id>{{ key.id }}</Id>
            <Name>{{ key.name }}</Name>
            <CreatedTime>{{ key.created }}</CreatedTime>
            <EncodedKey>{{ key.encoded_key }}</EncodedKey>
            <Comment></Comment>
        </PublicKeySummary>
        {% endfor %}
    </Items>
    {% endif %}
</PublicKeyList>
"""


KEY_GROUP_TEMPLATE = """<?xml version="1.0"?>
<KeyGroup>
  <Id>{{ group.id }}</Id>
  <KeyGroupConfig>
    <Name>{{ group.name }}</Name>
    <Items>
     {% for item in group.items %}<PublicKey>{{ item }}</PublicKey>{% endfor %}
    </Items>
  </KeyGroupConfig>
</KeyGroup>
"""


LIST_KEY_GROUPS_TEMPLATE = """<?xml version="1.0"?>
<KeyGroupList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ groups|length }}</Quantity>
  {% if groups %}
  <Items>
    {% for group in groups %}
    <KeyGroupSummary>
      <KeyGroup>
        <Id>{{ group.id }}</Id>
        <KeyGroupConfig>
          <Name>{{ group.name }}</Name>
          <Items>
           {% for item in group.items %}<PublicKey>{{ item }}</PublicKey>{% endfor %}
          </Items>
        </KeyGroupConfig>
      </KeyGroup>
    </KeyGroupSummary>
    {% endfor %}
  </Items>
  {% endif %}
</KeyGroupList>"""


FUNCTION_SUMMARY_TEMPLATE = """<?xml version="1.0"?>
<FunctionSummary>
  <Name>{{ func.name }}</Name>
  <Status>{{ func.status }}</Status>
  <FunctionConfig>
    <Comment>{{ func.function_config.get("Comment", "") }}</Comment>
    <Runtime>{{ func.function_config.get("Runtime", "cloudfront-js-1.0") }}</Runtime>
  </FunctionConfig>
  <FunctionMetadata>
    <FunctionARN>{{ func.function_arn }}</FunctionARN>
    <Stage>{{ func.stage }}</Stage>
    <CreatedTime>{{ func.created_time }}</CreatedTime>
    <LastModifiedTime>{{ func.last_modified_time }}</LastModifiedTime>
  </FunctionMetadata>
</FunctionSummary>
"""


LIST_FUNCTIONS_TEMPLATE = """<?xml version="1.0"?>
<FunctionList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ functions|length }}</Quantity>
  {% if functions %}
  <Items>
    {% for func in functions %}
    <FunctionSummary>
      <Name>{{ func.name }}</Name>
      <Status>{{ func.status }}</Status>
      <FunctionConfig>
        <Comment>{{ func.function_config.get("Comment", "") }}</Comment>
        <Runtime>{{ func.function_config.get("Runtime", "cloudfront-js-1.0") }}</Runtime>
      </FunctionConfig>
      <FunctionMetadata>
        <FunctionARN>{{ func.function_arn }}</FunctionARN>
        <Stage>{{ func.stage }}</Stage>
        <CreatedTime>{{ func.created_time }}</CreatedTime>
        <LastModifiedTime>{{ func.last_modified_time }}</LastModifiedTime>
      </FunctionMetadata>
    </FunctionSummary>
    {% endfor %}
  </Items>
  {% endif %}
</FunctionList>
"""


CACHE_POLICY_TEMPLATE = """<?xml version="1.0"?>
<CachePolicy>
  <Id>{{ policy.id }}</Id>
  <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
  <CachePolicyConfig>
    <Name>{{ policy.name }}</Name>
    <Comment>{{ policy.comment }}</Comment>
    <DefaultTTL>{{ policy.default_ttl }}</DefaultTTL>
    <MaxTTL>{{ policy.max_ttl }}</MaxTTL>
    <MinTTL>{{ policy.min_ttl }}</MinTTL>
  </CachePolicyConfig>
</CachePolicy>
"""


LIST_CACHE_POLICIES_TEMPLATE = """<?xml version="1.0"?>
<CachePolicyList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ policies|length }}</Quantity>
  {% if policies %}
  <Items>
    {% for policy in policies %}
    <CachePolicySummary>
      <Type>custom</Type>
      <CachePolicy>
        <Id>{{ policy.id }}</Id>
        <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
        <CachePolicyConfig>
          <Name>{{ policy.name }}</Name>
          <Comment>{{ policy.comment }}</Comment>
          <DefaultTTL>{{ policy.default_ttl }}</DefaultTTL>
          <MaxTTL>{{ policy.max_ttl }}</MaxTTL>
          <MinTTL>{{ policy.min_ttl }}</MinTTL>
        </CachePolicyConfig>
      </CachePolicy>
    </CachePolicySummary>
    {% endfor %}
  </Items>
  {% endif %}
</CachePolicyList>
"""


RESPONSE_HEADERS_POLICY_TEMPLATE = """<?xml version="1.0"?>
<ResponseHeadersPolicy>
  <Id>{{ policy.id }}</Id>
  <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
  <ResponseHeadersPolicyConfig>
    <Name>{{ policy.name }}</Name>
    <Comment>{{ policy.comment }}</Comment>
  </ResponseHeadersPolicyConfig>
</ResponseHeadersPolicy>
"""


LIST_RESPONSE_HEADERS_POLICIES_TEMPLATE = """<?xml version="1.0"?>
<ResponseHeadersPolicyList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ policies|length }}</Quantity>
  {% if policies %}
  <Items>
    {% for policy in policies %}
    <ResponseHeadersPolicySummary>
      <Type>custom</Type>
      <ResponseHeadersPolicy>
        <Id>{{ policy.id }}</Id>
        <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
        <ResponseHeadersPolicyConfig>
          <Name>{{ policy.name }}</Name>
          <Comment>{{ policy.comment }}</Comment>
        </ResponseHeadersPolicyConfig>
      </ResponseHeadersPolicy>
    </ResponseHeadersPolicySummary>
    {% endfor %}
  </Items>
  {% endif %}
</ResponseHeadersPolicyList>
"""


# Origin Access Identity templates
OAI_TEMPLATE = """<?xml version="1.0"?>
<CloudFrontOriginAccessIdentity>
  <Id>{{ oai.id }}</Id>
  <S3CanonicalUserId>{{ oai.s3_canonical_user_id }}</S3CanonicalUserId>
  <CloudFrontOriginAccessIdentityConfig>
    <CallerReference>{{ oai.caller_reference }}</CallerReference>
    <Comment>{{ oai.comment }}</Comment>
  </CloudFrontOriginAccessIdentityConfig>
</CloudFrontOriginAccessIdentity>
"""

OAI_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<CloudFrontOriginAccessIdentityConfig>
  <CallerReference>{{ oai.caller_reference }}</CallerReference>
  <Comment>{{ oai.comment }}</Comment>
</CloudFrontOriginAccessIdentityConfig>
"""

LIST_OAI_TEMPLATE = """<?xml version="1.0"?>
<CloudFrontOriginAccessIdentityList>
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ oais|length }}</Quantity>
  {% if oais %}
  <Items>
    {% for oai in oais %}
    <CloudFrontOriginAccessIdentitySummary>
      <Id>{{ oai.id }}</Id>
      <S3CanonicalUserId>{{ oai.s3_canonical_user_id }}</S3CanonicalUserId>
      <Comment>{{ oai.comment }}</Comment>
    </CloudFrontOriginAccessIdentitySummary>
    {% endfor %}
  </Items>
  {% endif %}
</CloudFrontOriginAccessIdentityList>
"""


STREAMING_DIST_CONFIG_INNER = """
  <CallerReference>{{ dist.streaming_distribution_config.caller_reference }}</CallerReference>
  <S3Origin>
    <DomainName>{{ dist.streaming_distribution_config.s3_origin_dns_name }}</DomainName>
    <OriginAccessIdentity>{{ dist.streaming_distribution_config.s3_origin_access_identity }}</OriginAccessIdentity>
  </S3Origin>
  <Aliases>
    <Quantity>{{ dist.streaming_distribution_config.aliases|length }}</Quantity>
    {% if dist.streaming_distribution_config.aliases %}
    <Items>
      {% for alias in dist.streaming_distribution_config.aliases %}
      <CNAME>{{ alias }}</CNAME>
      {% endfor %}
    </Items>
    {% endif %}
  </Aliases>
  <Comment>{{ dist.streaming_distribution_config.comment }}</Comment>
  <Logging>
    <Enabled>{{ dist.streaming_distribution_config.logging.enabled }}</Enabled>
    <Bucket>{{ dist.streaming_distribution_config.logging.bucket }}</Bucket>
    <Prefix>{{ dist.streaming_distribution_config.logging.prefix }}</Prefix>
  </Logging>
  <TrustedSigners>
    <Enabled>{{ 'true' if dist.streaming_distribution_config.trusted_signers_enabled else 'false' }}</Enabled>
    <Quantity>{{ dist.streaming_distribution_config.trusted_signers|length }}</Quantity>
    {% if dist.streaming_distribution_config.trusted_signers %}
    <Items>
      {% for signer in dist.streaming_distribution_config.trusted_signers %}
      <AwsAccountNumber>{{ signer }}</AwsAccountNumber>
      {% endfor %}
    </Items>
    {% endif %}
  </TrustedSigners>
  <PriceClass>{{ dist.streaming_distribution_config.price_class }}</PriceClass>
  <Enabled>{{ dist.streaming_distribution_config.enabled }}</Enabled>
"""

STREAMING_DIST_TEMPLATE = (
    """<?xml version="1.0"?>
<StreamingDistribution>
  <Id>{{ dist.streaming_distribution_id }}</Id>
  <ARN>{{ dist.arn }}</ARN>
  <Status>{{ dist.status }}</Status>
  <LastModifiedTime>{{ dist.last_modified_time }}</LastModifiedTime>
  <DomainName>{{ dist.domain_name }}</DomainName>
  <ActiveTrustedSigners><Enabled>false</Enabled><Quantity>0</Quantity></ActiveTrustedSigners>
  <StreamingDistributionConfig>
"""
    + STREAMING_DIST_CONFIG_INNER
    + """
  </StreamingDistributionConfig>
</StreamingDistribution>
"""
)

STREAMING_DIST_CONFIG_TEMPLATE = (
    """<?xml version="1.0"?>
<StreamingDistributionConfig>
"""
    + STREAMING_DIST_CONFIG_INNER
    + """
</StreamingDistributionConfig>
"""
)

LIST_STREAMING_DISTS_TEMPLATE = (
    """<?xml version="1.0"?>
<StreamingDistributionList>
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ dists|length }}</Quantity>
  {% if dists %}
  <Items>
    {% for dist in dists %}
    <StreamingDistributionSummary>
      <Id>{{ dist.streaming_distribution_id }}</Id>
      <ARN>{{ dist.arn }}</ARN>
      <Status>{{ dist.status }}</Status>
      <LastModifiedTime>{{ dist.last_modified_time }}</LastModifiedTime>
      <DomainName>{{ dist.domain_name }}</DomainName>
"""
    + STREAMING_DIST_CONFIG_INNER
    + """
    </StreamingDistributionSummary>
    {% endfor %}
  </Items>
  {% endif %}
</StreamingDistributionList>
"""
)


ORIGIN_REQUEST_POLICY_TEMPLATE = """<?xml version="1.0"?>
<OriginRequestPolicy>
  <Id>{{ policy.id }}</Id>
  <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
  <OriginRequestPolicyConfig>
    <Name>{{ policy.name }}</Name>
    <Comment>{{ policy.comment }}</Comment>
    <HeadersConfig><HeaderBehavior>{{ policy.headers_config.get("HeaderBehavior", "none") }}</HeaderBehavior></HeadersConfig>
    <CookiesConfig><CookieBehavior>{{ policy.cookies_config.get("CookieBehavior", "none") }}</CookieBehavior></CookiesConfig>
    <QueryStringsConfig><QueryStringBehavior>{{ policy.query_strings_config.get("QueryStringBehavior", "none") }}</QueryStringBehavior></QueryStringsConfig>
  </OriginRequestPolicyConfig>
</OriginRequestPolicy>
"""

ORIGIN_REQUEST_POLICY_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<OriginRequestPolicyConfig>
  <Name>{{ policy.name }}</Name>
  <Comment>{{ policy.comment }}</Comment>
  <HeadersConfig><HeaderBehavior>{{ policy.headers_config.get("HeaderBehavior", "none") }}</HeaderBehavior></HeadersConfig>
  <CookiesConfig><CookieBehavior>{{ policy.cookies_config.get("CookieBehavior", "none") }}</CookieBehavior></CookiesConfig>
  <QueryStringsConfig><QueryStringBehavior>{{ policy.query_strings_config.get("QueryStringBehavior", "none") }}</QueryStringBehavior></QueryStringsConfig>
</OriginRequestPolicyConfig>
"""

LIST_ORIGIN_REQUEST_POLICIES_TEMPLATE = """<?xml version="1.0"?>
<OriginRequestPolicyList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ policies|length }}</Quantity>
  {% if policies %}
  <Items>
    {% for policy in policies %}
    <OriginRequestPolicySummary>
      <Type>custom</Type>
      <OriginRequestPolicy>
        <Id>{{ policy.id }}</Id>
        <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
        <OriginRequestPolicyConfig>
          <Name>{{ policy.name }}</Name>
          <Comment>{{ policy.comment }}</Comment>
        </OriginRequestPolicyConfig>
      </OriginRequestPolicy>
    </OriginRequestPolicySummary>
    {% endfor %}
  </Items>
  {% endif %}
</OriginRequestPolicyList>
"""


FIELD_LEVEL_ENCRYPTION_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryption>
  <Id>{{ fle.id }}</Id>
  <LastModifiedTime>{{ fle.last_modified_time }}</LastModifiedTime>
  <FieldLevelEncryptionConfig>
    <CallerReference>{{ fle.caller_reference }}</CallerReference>
    <Comment>{{ fle.comment }}</Comment>
  </FieldLevelEncryptionConfig>
</FieldLevelEncryption>
"""

FIELD_LEVEL_ENCRYPTION_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryptionConfig>
  <CallerReference>{{ fle.caller_reference }}</CallerReference>
  <Comment>{{ fle.comment }}</Comment>
</FieldLevelEncryptionConfig>
"""

LIST_FIELD_LEVEL_ENCRYPTION_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryptionList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ configs|length }}</Quantity>
  {% if configs %}
  <Items>
    {% for fle in configs %}
    <FieldLevelEncryptionSummary>
      <Id>{{ fle.id }}</Id>
      <LastModifiedTime>{{ fle.last_modified_time }}</LastModifiedTime>
      <Comment>{{ fle.comment }}</Comment>
    </FieldLevelEncryptionSummary>
    {% endfor %}
  </Items>
  {% endif %}
</FieldLevelEncryptionList>
"""


FLE_PROFILE_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryptionProfile>
  <Id>{{ profile.id }}</Id>
  <LastModifiedTime>{{ profile.last_modified_time }}</LastModifiedTime>
  <FieldLevelEncryptionProfileConfig>
    <Name>{{ profile.name }}</Name>
    <CallerReference>{{ profile.caller_reference }}</CallerReference>
    <Comment>{{ profile.comment }}</Comment>
  </FieldLevelEncryptionProfileConfig>
</FieldLevelEncryptionProfile>
"""

FLE_PROFILE_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryptionProfileConfig>
  <Name>{{ profile.name }}</Name>
  <CallerReference>{{ profile.caller_reference }}</CallerReference>
  <Comment>{{ profile.comment }}</Comment>
</FieldLevelEncryptionProfileConfig>
"""

LIST_FLE_PROFILES_TEMPLATE = """<?xml version="1.0"?>
<FieldLevelEncryptionProfileList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ profiles|length }}</Quantity>
  {% if profiles %}
  <Items>
    {% for profile in profiles %}
    <FieldLevelEncryptionProfileSummary>
      <Id>{{ profile.id }}</Id>
      <LastModifiedTime>{{ profile.last_modified_time }}</LastModifiedTime>
      <Name>{{ profile.name }}</Name>
      <Comment>{{ profile.comment }}</Comment>
    </FieldLevelEncryptionProfileSummary>
    {% endfor %}
  </Items>
  {% endif %}
</FieldLevelEncryptionProfileList>
"""


CDP_TEMPLATE = """<?xml version="1.0"?>
<ContinuousDeploymentPolicy>
  <Id>{{ policy.id }}</Id>
  <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
  <ContinuousDeploymentPolicyConfig>
    <StagingDistributionDnsNames><Quantity>0</Quantity></StagingDistributionDnsNames>
    <Enabled>{{ policy.enabled }}</Enabled>
  </ContinuousDeploymentPolicyConfig>
</ContinuousDeploymentPolicy>
"""

CDP_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<ContinuousDeploymentPolicyConfig>
  <StagingDistributionDnsNames><Quantity>0</Quantity></StagingDistributionDnsNames>
  <Enabled>{{ policy.enabled }}</Enabled>
</ContinuousDeploymentPolicyConfig>
"""

LIST_CDP_TEMPLATE = """<?xml version="1.0"?>
<ContinuousDeploymentPolicyList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ policies|length }}</Quantity>
  {% if policies %}
  <Items>
    {% for policy in policies %}
    <ContinuousDeploymentPolicySummary>
      <ContinuousDeploymentPolicy>
        <Id>{{ policy.id }}</Id>
        <LastModifiedTime>{{ policy.last_modified_time }}</LastModifiedTime>
        <ContinuousDeploymentPolicyConfig>
          <StagingDistributionDnsNames><Quantity>0</Quantity></StagingDistributionDnsNames>
          <Enabled>{{ policy.enabled }}</Enabled>
        </ContinuousDeploymentPolicyConfig>
      </ContinuousDeploymentPolicy>
    </ContinuousDeploymentPolicySummary>
    {% endfor %}
  </Items>
  {% endif %}
</ContinuousDeploymentPolicyList>
"""


MONITORING_SUB_TEMPLATE = """<?xml version="1.0"?>
<MonitoringSubscription>
  <RealtimeMetricsSubscriptionConfig>
    <RealtimeMetricsSubscriptionStatus>{{ sub.realtime_metrics_subscription_status }}</RealtimeMetricsSubscriptionStatus>
  </RealtimeMetricsSubscriptionConfig>
</MonitoringSubscription>
"""


REALTIME_LOG_CONFIG_INNER = """
  <RealtimeLogConfig>
    <ARN>{{ config.arn }}</ARN>
    <Name>{{ config.name }}</Name>
    <SamplingRate>{{ config.sampling_rate }}</SamplingRate>
    <EndPoints>
      {% for ep in config.end_points %}
      <member>
        <StreamType>{{ ep.get("StreamType", "Kinesis") }}</StreamType>
        <KinesisStreamConfig>
          <RoleARN>{{ ep.get("KinesisStreamConfig", {}).get("RoleARN", "") }}</RoleARN>
          <StreamARN>{{ ep.get("KinesisStreamConfig", {}).get("StreamARN", "") }}</StreamARN>
        </KinesisStreamConfig>
      </member>
      {% endfor %}
    </EndPoints>
    <Fields>
      {% for field in config.fields %}
      <member>{{ field }}</member>
      {% endfor %}
    </Fields>
  </RealtimeLogConfig>
"""

CREATE_REALTIME_LOG_CONFIG_RESULT = (
    """<?xml version="1.0"?><CreateRealtimeLogConfigResult>"""
    + REALTIME_LOG_CONFIG_INNER
    + """</CreateRealtimeLogConfigResult>"""
)

GET_REALTIME_LOG_CONFIG_RESULT = (
    """<?xml version="1.0"?><GetRealtimeLogConfigResult>"""
    + REALTIME_LOG_CONFIG_INNER
    + """</GetRealtimeLogConfigResult>"""
)

UPDATE_REALTIME_LOG_CONFIG_RESULT = (
    """<?xml version="1.0"?><UpdateRealtimeLogConfigResult>"""
    + REALTIME_LOG_CONFIG_INNER
    + """</UpdateRealtimeLogConfigResult>"""
)

# Keep for backward compat
REALTIME_LOG_CONFIG_TEMPLATE = CREATE_REALTIME_LOG_CONFIG_RESULT

LIST_REALTIME_LOG_CONFIGS_TEMPLATE = """<?xml version="1.0"?>
<RealtimeLogConfigs>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  {% if configs %}
  <Items>
    {% for config in configs %}
    <member>
      <ARN>{{ config.arn }}</ARN>
      <Name>{{ config.name }}</Name>
      <SamplingRate>{{ config.sampling_rate }}</SamplingRate>
    </member>
    {% endfor %}
  </Items>
  {% endif %}
</RealtimeLogConfigs>
"""


DISTRIBUTION_ID_LIST_TEMPLATE = """<?xml version="1.0"?>
<DistributionIdList>
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ dist_ids|length }}</Quantity>
  {% if dist_ids %}
  <Items>
    {% for dist_id in dist_ids %}
    <DistributionId>{{ dist_id }}</DistributionId>
    {% endfor %}
  </Items>
  {% endif %}
</DistributionIdList>
"""


CACHE_POLICY_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<CachePolicyConfig>
  <Name>{{ policy.name }}</Name>
  <Comment>{{ policy.comment }}</Comment>
  <DefaultTTL>{{ policy.default_ttl }}</DefaultTTL>
  <MaxTTL>{{ policy.max_ttl }}</MaxTTL>
  <MinTTL>{{ policy.min_ttl }}</MinTTL>
</CachePolicyConfig>
"""

KEY_GROUP_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<KeyGroupConfig>
  <Name>{{ group.name }}</Name>
  <Items>
    {% for item in group.items %}<PublicKey>{{ item }}</PublicKey>{% endfor %}
  </Items>
</KeyGroupConfig>
"""

OAC_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<OriginAccessControlConfig>
  <Name>{{ control.name }}</Name>
  {% if control.description %}
  <Description>{{ control.description }}</Description>
  {% endif %}
  <SigningProtocol>{{ control.signing_protocol }}</SigningProtocol>
  <SigningBehavior>{{ control.signing_behaviour }}</SigningBehavior>
  <OriginAccessControlOriginType>{{ control.origin_type }}</OriginAccessControlOriginType>
</OriginAccessControlConfig>
"""

PUBLIC_KEY_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<PublicKeyConfig>
  <CallerReference>{{ key.caller_ref }}</CallerReference>
  <Name>{{ key.name }}</Name>
  <EncodedKey>{{ key.encoded_key }}</EncodedKey>
  <Comment></Comment>
</PublicKeyConfig>
"""

RESPONSE_HEADERS_POLICY_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<ResponseHeadersPolicyConfig>
  <Name>{{ policy.name }}</Name>
  <Comment>{{ policy.comment }}</Comment>
</ResponseHeadersPolicyConfig>
"""


TEST_FUNCTION_TEMPLATE = """<?xml version="1.0"?>
<TestResult>
  <FunctionSummary>
    <Name>{{ result.FunctionSummary.Name }}</Name>
    <Status>{{ result.FunctionSummary.Status }}</Status>
  </FunctionSummary>
  <ComputeUtilization>{{ result.ComputeUtilization }}</ComputeUtilization>
  <FunctionExecutionLogs></FunctionExecutionLogs>
  <FunctionErrorMessage>{{ result.FunctionErrorMessage }}</FunctionErrorMessage>
  <FunctionOutput>{{ result.FunctionOutput }}</FunctionOutput>
</TestResult>
"""


CONFLICTING_ALIASES_TEMPLATE = """<?xml version="1.0"?>
<ConflictingAliasesList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ items|length }}</Quantity>
  {% if items %}
  <Items>
    {% for item in items %}
    <ConflictingAlias>
      <Alias>{{ item.Alias }}</Alias>
      <DistributionId>{{ item.DistributionId }}</DistributionId>
      <AccountId>{{ item.AccountId }}</AccountId>
    </ConflictingAlias>
    {% endfor %}
  </Items>
  {% endif %}
</ConflictingAliasesList>
"""

KEY_VALUE_STORE_TEMPLATE = """<?xml version="1.0"?>
<KeyValueStore>
  <Name>{{ name }}</Name>
  <Id>{{ kvs_id }}</Id>
  <Comment>{{ comment }}</Comment>
  <ARN>{{ arn }}</ARN>
  <Status>{{ status }}</Status>
  <LastModifiedTime>{{ last_modified }}</LastModifiedTime>
</KeyValueStore>
"""

LIST_KEY_VALUE_STORES_TEMPLATE = """<?xml version="1.0"?>
<KeyValueStoreList>
  <MaxItems>100</MaxItems>
  <Quantity>{{ stores|length }}</Quantity>
  {% if stores %}
  <Items>
    {% for s in stores %}
    <KeyValueStore>
      <Name>{{ s.name }}</Name>
      <Id>{{ s.id }}</Id>
      <Comment>{{ s.comment }}</Comment>
      <ARN>{{ s.arn }}</ARN>
      <Status>{{ s.status }}</Status>
      <LastModifiedTime>{{ s.last_modified_time }}</LastModifiedTime>
    </KeyValueStore>
    {% endfor %}
  </Items>
  {% endif %}
</KeyValueStoreList>
"""

VPC_ORIGIN_TEMPLATE = """<?xml version="1.0"?>
<VpcOrigin xmlns="{{ xmlns }}">
  <Id>{{ vo.id }}</Id>
  <Arn>{{ vo.arn }}</Arn>
  <AccountId>{{ vo.account_id }}</AccountId>
  <Status>{{ vo.status }}</Status>
  <CreatedTime>{{ vo.created_time }}</CreatedTime>
  <LastModifiedTime>{{ vo.last_modified_time }}</LastModifiedTime>
  <VpcOriginEndpointConfig>
    <Name>{{ vo.vpc_origin_endpoint_config.get('Name', '') }}</Name>
    <Arn>{{ vo.vpc_origin_endpoint_config.get('Arn', '') }}</Arn>
    <HTTPPort>{{ vo.vpc_origin_endpoint_config.get('HTTPPort', 80) }}</HTTPPort>
    <HTTPSPort>{{ vo.vpc_origin_endpoint_config.get('HTTPSPort', 443) }}</HTTPSPort>
    <OriginProtocolPolicy>{{ vo.vpc_origin_endpoint_config.get('OriginProtocolPolicy', 'https-only') }}</OriginProtocolPolicy>
    <OriginSslProtocols>
      <Quantity>0</Quantity>
      <Items/>
    </OriginSslProtocols>
  </VpcOriginEndpointConfig>
</VpcOrigin>
"""

LIST_VPC_ORIGINS_TEMPLATE = """<?xml version="1.0"?>
<VpcOriginList xmlns="{{ xmlns }}">
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ origins|length }}</Quantity>
  {% if origins %}
  <Items>
    {% for vo in origins %}
    <VpcOriginSummary>
      <Id>{{ vo.id }}</Id>
      <Name>{{ vo.vpc_origin_endpoint_config.get('Name', '') }}</Name>
      <Status>{{ vo.status }}</Status>
      <CreatedTime>{{ vo.created_time }}</CreatedTime>
      <LastModifiedTime>{{ vo.last_modified_time }}</LastModifiedTime>
      <Arn>{{ vo.arn }}</Arn>
      <AccountId>{{ vo.account_id }}</AccountId>
      <OriginEndpointArn>{{ vo.vpc_origin_endpoint_config.get('Arn', '') }}</OriginEndpointArn>
    </VpcOriginSummary>
    {% endfor %}
  </Items>
  {% endif %}
</VpcOriginList>
"""

TRUST_STORE_TEMPLATE = """<?xml version="1.0"?>
<TrustStore xmlns="{{ xmlns }}">
  <Id>{{ ts.id }}</Id>
  <Arn>{{ ts.arn }}</Arn>
  <Name>{{ ts.name }}</Name>
  <Status>{{ ts.status }}</Status>
  <NumberOfCaCertificates>{{ ts.number_of_ca_certificates }}</NumberOfCaCertificates>
  <LastModifiedTime>{{ ts.last_modified_time }}</LastModifiedTime>
</TrustStore>
"""

LIST_TRUST_STORES_TEMPLATE = """<?xml version="1.0"?>
<TrustStoreList xmlns="{{ xmlns }}">
  {% for ts in stores %}
  <TrustStoreSummary>
    <Id>{{ ts.id }}</Id>
    <Arn>{{ ts.arn }}</Arn>
    <Name>{{ ts.name }}</Name>
    <Status>{{ ts.status }}</Status>
    <LastModifiedTime>{{ ts.last_modified_time }}</LastModifiedTime>
  </TrustStoreSummary>
  {% endfor %}
</TrustStoreList>
"""

ANYCAST_IP_LIST_TEMPLATE = """<?xml version="1.0"?>
<AnycastIpList xmlns="{{ xmlns }}">
  <Id>{{ aip.id }}</Id>
  <Name>{{ aip.name }}</Name>
  <Status>{{ aip.status }}</Status>
  <Arn>{{ aip.arn }}</Arn>
  <AnycastIps/>
  <IpCount>{{ aip.ip_count }}</IpCount>
  <LastModifiedTime>{{ aip.last_modified_time }}</LastModifiedTime>
</AnycastIpList>
"""

LIST_ANYCAST_IP_LISTS_TEMPLATE = """<?xml version="1.0"?>
<AnycastIpLists xmlns="{{ xmlns }}">
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ lists|length }}</Quantity>
  {% if lists %}
  <Items>
    {% for a in lists %}
    <AnycastIpListSummary>
      <Id>{{ a.id }}</Id>
      <Name>{{ a.name }}</Name>
      <Status>{{ a.status }}</Status>
      <Arn>{{ a.arn }}</Arn>
      <IpCount>{{ a.ip_count }}</IpCount>
      <LastModifiedTime>{{ a.last_modified_time }}</LastModifiedTime>
    </AnycastIpListSummary>
    {% endfor %}
  </Items>
  {% endif %}
</AnycastIpLists>
"""

CONNECTION_GROUP_TEMPLATE = """<?xml version="1.0"?>
<ConnectionGroup xmlns="{{ xmlns }}">
  <Id>{{ cg.id }}</Id>
  <Name>{{ cg.name }}</Name>
  <Arn>{{ cg.arn }}</Arn>
  <CreatedTime>{{ cg.created_time }}</CreatedTime>
  <LastModifiedTime>{{ cg.last_modified_time }}</LastModifiedTime>
  <Status>{{ cg.status }}</Status>
  <Enabled>true</Enabled>
  <IsDefault>false</IsDefault>
</ConnectionGroup>
"""

LIST_CONNECTION_GROUPS_TEMPLATE = """<?xml version="1.0"?>
<ConnectionGroups xmlns="{{ xmlns }}">
  {% for cg in groups %}
  <ConnectionGroupSummary>
    <Id>{{ cg.id }}</Id>
    <Name>{{ cg.name }}</Name>
    <Arn>{{ cg.arn }}</Arn>
    <CreatedTime>{{ cg.created_time }}</CreatedTime>
    <LastModifiedTime>{{ cg.last_modified_time }}</LastModifiedTime>
    <Status>{{ cg.status }}</Status>
  </ConnectionGroupSummary>
  {% endfor %}
</ConnectionGroups>
"""

DISTRIBUTION_TENANT_TEMPLATE = """<?xml version="1.0"?>
<DistributionTenant xmlns="{{ xmlns }}">
  <Id>{{ dt.id }}</Id>
  <DistributionId>{{ dt.distribution_id }}</DistributionId>
  <Name>{{ dt.name }}</Name>
  <Arn>{{ dt.arn }}</Arn>
  <Status>{{ dt.status }}</Status>
  <Enabled>true</Enabled>
  <CreatedTime>{{ dt.created_time }}</CreatedTime>
  <LastModifiedTime>{{ dt.last_modified_time }}</LastModifiedTime>
</DistributionTenant>
"""

LIST_DISTRIBUTION_TENANTS_TEMPLATE = """<?xml version="1.0"?>
<DistributionTenantList xmlns="{{ xmlns }}">
  {% for dt in tenants %}
  <DistributionTenantSummary>
    <Id>{{ dt.id }}</Id>
    <Name>{{ dt.name }}</Name>
    <Arn>{{ dt.arn }}</Arn>
    <Status>{{ dt.status }}</Status>
  </DistributionTenantSummary>
  {% endfor %}
</DistributionTenantList>
"""

TENANT_INVALIDATION_TEMPLATE = """<?xml version="1.0"?>
<Invalidation xmlns="{{ xmlns }}">
  <Id>{{ inv_id }}</Id>
  <Status>COMPLETED</Status>
  <CreateTime>2021-01-01T00:00:00.000Z</CreateTime>
  <InvalidationBatch>
    <Paths><Quantity>0</Quantity></Paths>
    <CallerReference>ref</CallerReference>
  </InvalidationBatch>
</Invalidation>
"""

TENANT_INVALIDATION_LIST_TEMPLATE = """<?xml version="1.0"?>
<InvalidationList xmlns="{{ xmlns }}">
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>0</Quantity>
</InvalidationList>
"""

CONNECTION_FUNCTION_TEMPLATE = """<?xml version="1.0"?>
<ConnectionFunctionSummary xmlns="{{ xmlns }}">
  <Name>{{ cf.name }}</Name>
  <Id>{{ cf.id }}</Id>
  <ConnectionFunctionArn>{{ cf.connection_function_arn }}</ConnectionFunctionArn>
  <Status>{{ cf.status }}</Status>
  <Stage>{{ cf.stage }}</Stage>
  <CreatedTime>{{ cf.created_time }}</CreatedTime>
  <LastModifiedTime>{{ cf.last_modified_time }}</LastModifiedTime>
</ConnectionFunctionSummary>
"""

LIST_CONNECTION_FUNCTIONS_TEMPLATE = """<?xml version="1.0"?>
<ConnectionFunctions xmlns="{{ xmlns }}">
  {% for cf in funcs %}
  <ConnectionFunctionSummary>
    <Name>{{ cf.name }}</Name>
    <Id>{{ cf.id }}</Id>
    <ConnectionFunctionArn>{{ cf.connection_function_arn }}</ConnectionFunctionArn>
    <Status>{{ cf.status }}</Status>
    <Stage>{{ cf.stage }}</Stage>
    <CreatedTime>{{ cf.created_time }}</CreatedTime>
    <LastModifiedTime>{{ cf.last_modified_time }}</LastModifiedTime>
  </ConnectionFunctionSummary>
  {% endfor %}
</ConnectionFunctions>
"""

TEST_CONNECTION_FUNCTION_TEMPLATE = """<?xml version="1.0"?>
<TestResult xmlns="{{ xmlns }}">
  <FunctionOutput>{"response":{"statusCode":200}}</FunctionOutput>
  <ComputeUtilization>12</ComputeUtilization>
</TestResult>
"""

ERROR_TEMPLATE = """<?xml version="1.0"?>
<ErrorResponse xmlns="{{ xmlns }}">
  <Error>
    <Type>Sender</Type>
    <Code>{{ code }}</Code>
    <Message>{{ message }}</Message>
  </Error>
</ErrorResponse>
"""

RESOURCE_POLICY_TEMPLATE = """<?xml version="1.0"?>
<GetResourcePolicyResult xmlns="{{ xmlns }}">
</GetResourcePolicyResult>
"""

EMPTY_LIST_TEMPLATE = """<?xml version="1.0"?>
<{{ root_tag }} xmlns="{{ xmlns }}">
</{{ root_tag }}>
"""

MANAGED_CERTIFICATE_TEMPLATE = """<?xml version="1.0"?>
<ManagedCertificateDetails xmlns="{{ xmlns }}">
  <CertificateStatus>ISSUED</CertificateStatus>
</ManagedCertificateDetails>
"""

VERIFY_DNS_TEMPLATE = """<?xml version="1.0"?>
<VerifyDnsConfigurationResult xmlns="{{ xmlns }}">
</VerifyDnsConfigurationResult>
"""
