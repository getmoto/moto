from typing import Any, Dict
from moto.core.responses import BaseResponse
from ..exceptions import EmptyTagSpecError
from ..utils import convert_tag_spec


class EC2BaseResponse(BaseResponse):
    @property
    def ec2_backend(self) -> Any:  # type: ignore[misc]
        from moto.ec2.models import ec2_backends

        return ec2_backends[self.current_account][self.region]

    def _filters_from_querystring(self) -> Dict[str, str]:
        # [{"Name": x1, "Value": y1}, ..]
        _filters = self._get_multi_param("Filter.")
        # return {x1: y1, ...}
        return {f["Name"]: f["Value"] for f in _filters}

    def _parse_tag_specification(self) -> Dict[str, Dict[str, str]]:
        # [{"ResourceType": _type, "Tag": [{"Key": k, "Value": v}, ..]}]
        tag_spec_set = self._get_multi_param("TagSpecification")
        if not tag_spec_set:
            tag_spec_set = self._get_multi_param("TagSpecifications")
        # If we do not pass any Tags, this method will convert this to [_type] instead
        if isinstance(tag_spec_set, list) and any(
            [isinstance(spec, str) for spec in tag_spec_set]
        ):
            raise EmptyTagSpecError
        # {_type: {k: v, ..}}
        return convert_tag_spec(tag_spec_set)
