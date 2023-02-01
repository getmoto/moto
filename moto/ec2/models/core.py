from typing import Any, Dict, List, Optional
from moto.core import BaseModel

from ..exceptions import FilterNotImplementedError


class TaggedEC2Resource(BaseModel):
    def get_tags(self) -> List[Dict[str, str]]:
        tags = []
        if self.id:  # type: ignore[attr-defined]
            tags = self.ec2_backend.describe_tags(filters={"resource-id": [self.id]})  # type: ignore[attr-defined]
        return tags

    def add_tag(self, key: str, value: str) -> None:
        self.ec2_backend.create_tags([self.id], {key: value})  # type: ignore[attr-defined]

    def add_tags(self, tag_map: Dict[str, str]) -> None:
        for key, value in tag_map.items():
            self.ec2_backend.create_tags([self.id], {key: value})  # type: ignore[attr-defined]

    def get_filter_value(
        self, filter_name: str, method_name: Optional[str] = None
    ) -> Any:
        tags = self.get_tags()

        if filter_name.startswith("tag:"):
            tagname = filter_name.replace("tag:", "", 1)
            for tag in tags:
                if tag["key"] == tagname:
                    return tag["value"]

            return None
        elif filter_name == "tag-key":
            return [tag["key"] for tag in tags]
        elif filter_name == "tag-value":
            return [tag["value"] for tag in tags]

        value = getattr(self, filter_name.lower().replace("-", "_"), None)
        if value is not None:
            return value

        raise FilterNotImplementedError(filter_name, method_name)
