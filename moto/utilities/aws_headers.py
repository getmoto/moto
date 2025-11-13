from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from typing_extensions import Protocol
else:
    Protocol = object

import binascii

TypeDec = TypeVar("TypeDec", bound=Callable[..., Any])


class GenericFunction(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


def gen_amz_crc32(response: Any, headerdict: Optional[dict[str, Any]] = None) -> int:
    if not isinstance(response, bytes):
        response = response.encode("utf-8")

    crc = binascii.crc32(response)

    if headerdict is not None and isinstance(headerdict, dict):
        headerdict.update({"x-amz-crc32": str(crc)})

    return crc


def gen_amzn_requestid_long(headerdict: Optional[dict[str, Any]] = None) -> str:
    from moto.moto_api._internal import mock_random as random

    req_id = random.get_random_string(length=52)

    if headerdict is not None and isinstance(headerdict, dict):
        headerdict.update({"x-amzn-requestid": req_id})

    return req_id


def amz_crc32(
    f: Optional[TypeDec] = None, *, skip_crc_check: Optional[Callable[[], bool]] = None
) -> GenericFunction:  # type: ignore[misc]
    """
    Decorator that adds x-amz-crc32 header to responses.

    Args:
        f: The function to wrap
        skip_crc_check: Optional callable that returns True if CRC32 should be skipped

    Usage:
        @amz_crc32
        def my_method(self): ...

        @amz_crc32(skip_crc_check=some_function)
        def my_method(self): ...
    """

    def _decorator(func: Callable[..., Any]) -> GenericFunction:
        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            response = func(*args, **kwargs)

            headers = {}
            status = 200

            if isinstance(response, str):
                body = response
            else:
                if len(response) == 2:
                    body, new_headers = response
                    status = new_headers.get("status", status)
                else:
                    status, new_headers, body = response
                headers.update(new_headers)
                # Cast status to string
                if "status" in headers:
                    headers["status"] = str(headers["status"])

            # Only add CRC32 if skip_crc_check is not provided or returns False
            if skip_crc_check is None or not skip_crc_check():
                gen_amz_crc32(body, headers)

            return status, headers, body

        return _wrapper  # type: ignore[return-value]

    # Support both @amz_crc32 and @amz_crc32(skip_crc_check=...)
    if f is None:
        return _decorator  # type: ignore[return-value]
    else:
        return _decorator(f)
