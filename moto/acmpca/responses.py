"""Handles incoming acmpca requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import ACMPCABackend, acmpca_backends


class ACMPCAResponse(BaseResponse):
    """Handler for ACMPCA requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="acm-pca")
        self.automated_parameter_parsing = True

    @property
    def acmpca_backend(self) -> ACMPCABackend:
        """Return backend instance specific for this region."""
        return acmpca_backends[self.current_account][self.region]

    def create_certificate_authority(self) -> ActionResult:
        certificate_authority_configuration = self._get_param(
            "CertificateAuthorityConfiguration"
        )
        revocation_configuration = self._get_param("RevocationConfiguration")
        certificate_authority_type = self._get_param("CertificateAuthorityType")
        security_standard = self._get_param("KeyStorageSecurityStandard")
        tags = self._get_param("Tags")
        certificate_authority_arn = self.acmpca_backend.create_certificate_authority(
            certificate_authority_configuration=certificate_authority_configuration,
            revocation_configuration=revocation_configuration,
            certificate_authority_type=certificate_authority_type,
            security_standard=security_standard,
            tags=tags,
        )
        return ActionResult({"CertificateAuthorityArn": certificate_authority_arn})

    def describe_certificate_authority(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        certificate_authority = self.acmpca_backend.describe_certificate_authority(
            certificate_authority_arn=certificate_authority_arn,
        )
        return ActionResult({"CertificateAuthority": certificate_authority.to_json()})

    def get_certificate_authority_certificate(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        (
            certificate,
            certificate_chain,
        ) = self.acmpca_backend.get_certificate_authority_certificate(
            certificate_authority_arn=certificate_authority_arn,
        )
        response = {"Certificate": certificate.decode("utf-8")}
        if certificate_chain:
            response["CertificateChain"] = certificate_chain.decode("utf-8")
        return ActionResult(response)

    def get_certificate_authority_csr(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        csr = self.acmpca_backend.get_certificate_authority_csr(
            certificate_authority_arn=certificate_authority_arn,
        )
        return ActionResult({"Csr": csr.decode("utf-8").strip()})

    def list_tags(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        tags = self.acmpca_backend.list_tags(
            certificate_authority_arn=certificate_authority_arn
        )
        return ActionResult(tags)

    def update_certificate_authority(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        revocation_configuration = self._get_param("RevocationConfiguration")
        status = self._get_param("Status")
        self.acmpca_backend.update_certificate_authority(
            certificate_authority_arn=certificate_authority_arn,
            revocation_configuration=revocation_configuration,
            status=status,
        )
        return EmptyResult()

    def delete_certificate_authority(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        self.acmpca_backend.delete_certificate_authority(
            certificate_authority_arn=certificate_authority_arn
        )
        return EmptyResult()

    def issue_certificate(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        template_arn = self._get_param("TemplateArn")
        csr = self._get_param("Csr")
        certificate_arn = self.acmpca_backend.issue_certificate(
            certificate_authority_arn=certificate_authority_arn,
            csr=csr,
            template_arn=template_arn,
        )
        return ActionResult({"CertificateArn": certificate_arn})

    def get_certificate(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        certificate_arn = self._get_param("CertificateArn")
        certificate, certificate_chain = self.acmpca_backend.get_certificate(
            certificate_authority_arn=certificate_authority_arn,
            certificate_arn=certificate_arn,
        )

        response = {"Certificate": certificate.decode("utf-8").strip()}

        # Include CertificateChain if it exists (non-root certificates)
        if certificate_chain:
            response["CertificateChain"] = certificate_chain.decode("utf-8").strip()

        return ActionResult(response)

    def import_certificate_authority_certificate(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        certificate = self._get_param("Certificate")
        certificate_chain = self._get_param("CertificateChain")
        self.acmpca_backend.import_certificate_authority_certificate(
            certificate_authority_arn=certificate_authority_arn,
            certificate=certificate,
            certificate_chain=certificate_chain,
        )
        return EmptyResult()

    def revoke_certificate(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        certificate_serial = self._get_param("CertificateSerial")
        revocation_reason = self._get_param("RevocationReason")
        self.acmpca_backend.revoke_certificate(
            certificate_authority_arn=certificate_authority_arn,
            certificate_serial=certificate_serial,
            revocation_reason=revocation_reason,
        )
        return EmptyResult()

    def tag_certificate_authority(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        tags = self._get_param("Tags")
        self.acmpca_backend.tag_certificate_authority(
            certificate_authority_arn=certificate_authority_arn,
            tags=tags,
        )
        return EmptyResult()

    def untag_certificate_authority(self) -> ActionResult:
        certificate_authority_arn = self._get_param("CertificateAuthorityArn")
        tags = self._get_param("Tags")
        self.acmpca_backend.untag_certificate_authority(
            certificate_authority_arn=certificate_authority_arn,
            tags=tags,
        )
        return EmptyResult()

    def put_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self._get_param("Policy")
        self.acmpca_backend.put_policy(resource_arn=resource_arn, policy=policy)
        return EmptyResult()

    def get_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self.acmpca_backend.get_policy(resource_arn=resource_arn)
        return ActionResult({"Policy": policy})

    def delete_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        self.acmpca_backend.delete_policy(resource_arn=resource_arn)
        return EmptyResult()

    def list_certificate_authorities(self) -> ActionResult:
        """
        Handler for ListCertificateAuthorities API request
        """
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        resource_owner = self._get_param("ResourceOwner")

        # Get paginated results and next token from backend
        cas, next_token = self.acmpca_backend.list_certificate_authorities(
            max_results=max_results,
            next_token=next_token,
            resource_owner=resource_owner,
        )

        response = {
            "CertificateAuthorities": [ca.to_json() for ca in cas],
            "NextToken": next_token,
        }

        return ActionResult(response)
