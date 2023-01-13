from typing import Dict, Tuple, TypeVar, Union


TYPE_RESPONSE = Tuple[int, Dict[str, str], Union[str, bytes]]
TYPE_IF_NONE = TypeVar("TYPE_IF_NONE")
