from moto.core.responses import BaseResponse
from ..exceptions import EmptyTagSpecError
from ..utils import convert_tag_spec


class EC2BaseResponse(BaseResponse):
    def _filters_from_querystring(self):
        # [{"Name": x1, "Value": y1}, ..]
        _filters = self._get_multi_param("Filter.")
        # return {x1: y1, ...}
        return {f["Name"]: f["Value"] for f in _filters}

    def _parse_tag_specification(self):
        # [{"ResourceType": _type, "Tag": [{"Key": k, "Value": v}, ..]}]
        tag_spec_set = self._get_multi_param("TagSpecification")
        # If we do not pass any Tags, this method will convert this to [_type] instead
        if isinstance(tag_spec_set, list) and any(
            [isinstance(spec, str) for spec in tag_spec_set]
        ):
            raise EmptyTagSpecError
        # {_type: {k: v, ..}}
        return convert_tag_spec(tag_spec_set)
