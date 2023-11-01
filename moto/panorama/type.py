from typing_extensions import Literal

DEVICE_AGGREGATED_STATUS_TYPE = Literal[
        "ERROR",
        "AWAITING_PROVISIONING",
        "PENDING",
        "FAILED",
        "DELETING",
        "ONLINE",
        "OFFLINE",
        "LEASE_EXPIRED",
        "UPDATE_NEEDED",
        "REBOOTING",
    ]

PROVISIONING_STATUS_TYPE = Literal["AWAITING_PROVISIONING", "PENDING", "SUCCEEDED", "FAILED", "ERROR", "DELETING"]
