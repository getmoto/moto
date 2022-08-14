"""Handles incoming signer requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import signer_backends, SignerBackend


class signerResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="signer")

    @property
    def signer_backend(self) -> SignerBackend:
        """Return backend instance specific for this region."""
        return signer_backends[self.current_account][self.region]

    def cancel_signing_profile(self):
        profile_name = self.path.split("/")[-1]
        self.signer_backend.cancel_signing_profile(profile_name=profile_name)
        return "{}"

    def get_signing_profile(self):
        profile_name = self.path.split("/")[-1]
        profile = self.signer_backend.get_signing_profile(profile_name=profile_name)
        return json.dumps(profile.to_dict())

    def put_signing_profile(self):
        params = json.loads(self.body)
        profile_name = self.path.split("/")[-1]
        signature_validity_period = params.get("signatureValidityPeriod")
        platform_id = params.get("platformId")
        tags = params.get("tags")
        profile = self.signer_backend.put_signing_profile(
            profile_name=profile_name,
            signature_validity_period=signature_validity_period,
            platform_id=platform_id,
            tags=tags,
        )
        return json.dumps(profile.to_dict(full=False))

    def list_signing_platforms(self):
        platforms = self.signer_backend.list_signing_platforms()
        return json.dumps(dict(platforms=platforms))
