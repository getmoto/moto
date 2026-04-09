from importlib.util import find_spec

from botocore.compat import HAS_CRT as BOTOCORE_HAS_CRT_CHECK

HAS_CRT = BOTOCORE_HAS_CRT_CHECK
HAS_CRC32C = find_spec("crc32c") is not None
