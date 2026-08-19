import hashlib
import json

import boto3
import pytest
from botocore import xform_name
from botocore.exceptions import ClientError
from botocore.session import Session
from cryptography import x509
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers.algorithms import AES

from moto import mock_aws
from moto.paymentcryptography.models import PaymentCryptographyControlPlaneBackend
from moto.paymentcryptography.responses import PaymentCryptographyControlPlaneResponse

ATTRIBUTES = {
    "KeyUsage": "TR31_D0_SYMMETRIC_DATA_ENCRYPTION_KEY",
    "KeyClass": "SYMMETRIC_KEY",
    "KeyAlgorithm": "AES_128",
    "KeyModesOfUse": {"Encrypt": True, "Decrypt": True},
}

PUBLIC_ATTRIBUTES = {
    "KeyUsage": "TR31_K2_TR34_ASYMMETRIC_KEY",
    "KeyClass": "PUBLIC_KEY",
    "KeyAlgorithm": "RSA_2048",
    "KeyModesOfUse": {"Verify": True},
}

PAIR_ATTRIBUTES = {
    "KeyUsage": "TR31_S0_ASYMMETRIC_KEY_FOR_DIGITAL_SIGNATURE",
    "KeyClass": "ASYMMETRIC_KEY_PAIR",
    "KeyAlgorithm": "RSA_2048",
    "KeyModesOfUse": {"Sign": True, "Verify": True},
}

WRAPPING_ATTRIBUTES = {
    "KeyUsage": "TR31_K0_KEY_ENCRYPTION_KEY",
    "KeyClass": "SYMMETRIC_KEY",
    "KeyAlgorithm": "AES_128",
    "KeyModesOfUse": {"Wrap": True, "Unwrap": True},
}


def client(region: str = "us-east-1"):
    return boto3.client("payment-cryptography", region_name=region)


def test_all_botocore_operations_are_implemented():
    service = Session().get_service_model("payment-cryptography")
    operations = {xform_name(name) for name in service.operation_names}
    assert len(operations) == 32
    assert not {
        operation
        for operation in operations
        if not hasattr(PaymentCryptographyControlPlaneBackend, operation)
    }
    assert not {
        operation
        for operation in operations
        if not hasattr(PaymentCryptographyControlPlaneResponse, operation)
    }


@mock_aws
def test_key_alias_lifecycle_and_pagination():
    pc = client()
    first = pc.create_key(
        KeyAttributes=ATTRIBUTES,
        Exportable=True,
        Enabled=True,
        Tags=[{"Key": "team", "Value": "payments"}],
    )["Key"]
    second = pc.create_key(KeyAttributes=ATTRIBUTES, Exportable=False)["Key"]

    page = pc.list_keys(MaxResults=1)
    assert len(page["Keys"]) == 1
    assert len(pc.list_keys(MaxResults=1, NextToken=page["NextToken"])["Keys"]) == 1
    assert pc.get_key(KeyIdentifier=first["KeyArn"])["Key"] == first

    alias = pc.create_alias(AliasName="alias/current", KeyArn=first["KeyArn"])["Alias"]
    assert pc.get_alias(AliasName="alias/current")["Alias"] == alias
    pc.update_alias(AliasName="alias/current", KeyArn=second["KeyArn"])
    assert (
        pc.list_aliases(KeyArn=second["KeyArn"])["Aliases"][0]["AliasName"]
        == "alias/current"
    )
    pc.delete_alias(AliasName="alias/current")
    assert pc.list_aliases()["Aliases"] == []

    stopped = pc.stop_key_usage(KeyIdentifier=first["KeyArn"])["Key"]
    assert stopped["Enabled"] is False
    assert pc.start_key_usage(KeyIdentifier=first["KeyArn"])["Key"]["Enabled"] is True
    assert (
        pc.delete_key(KeyIdentifier=first["KeyArn"], DeleteKeyInDays=8)["Key"][
            "KeyState"
        ]
        == "DELETE_PENDING"
    )
    assert (
        pc.restore_key(KeyIdentifier=first["KeyArn"])["Key"]["KeyState"]
        == "CREATE_COMPLETE"
    )


@mock_aws
def test_tags_and_resource_policy():
    pc = client()
    arn = pc.create_key(KeyAttributes=ATTRIBUTES, Exportable=True)["Key"]["KeyArn"]
    pc.tag_resource(
        ResourceArn=arn, Tags=[{"Key": "a", "Value": "1"}, {"Key": "b", "Value": "2"}]
    )
    assert len(pc.list_tags_for_resource(ResourceArn=arn, MaxResults=1)["Tags"]) == 1
    pc.untag_resource(ResourceArn=arn, TagKeys=["a"])
    assert pc.list_tags_for_resource(ResourceArn=arn)["Tags"] == [
        {"Key": "b", "Value": "2"}
    ]

    policy = json.dumps({"Version": "2012-10-17", "Statement": []})
    assert pc.put_resource_policy(ResourceArn=arn, Policy=policy)["Policy"] == policy
    assert pc.get_resource_policy(ResourceArn=arn)["Policy"] == policy
    pc.delete_resource_policy(ResourceArn=arn)
    assert pc.get_resource_policy(ResourceArn=arn)["Policy"] == "{}"


@mock_aws
def test_default_and_per_key_replication():
    east = client()
    assert east.enable_default_key_replication_regions(
        ReplicationRegions=["us-west-2"]
    )["EnabledReplicationRegions"] == ["us-west-2"]
    assert east.get_default_key_replication_regions()["EnabledReplicationRegions"] == [
        "us-west-2"
    ]
    default_key = east.create_key(KeyAttributes=ATTRIBUTES, Exportable=True)["Key"]
    assert default_key["UsingDefaultReplicationRegions"] is True

    east.disable_default_key_replication_regions(ReplicationRegions=["us-west-2"])
    key = east.create_key(KeyAttributes=ATTRIBUTES, Exportable=True)["Key"]
    primary = east.add_key_replication_regions(
        KeyIdentifier=key["KeyArn"], ReplicationRegions=["us-west-2"]
    )["Key"]
    assert primary["ReplicationStatus"]["us-west-2"]["Status"] == "SYNCHRONIZED"
    key_id = key["KeyArn"].rsplit("/", 1)[1]
    replica_arn = f"arn:aws:payment-cryptography:us-west-2:123456789012:key/{key_id}"
    assert (
        client("us-west-2").get_key(KeyIdentifier=replica_arn)["Key"][
            "MultiRegionKeyType"
        ]
        == "REPLICA"
    )
    east.stop_key_usage(KeyIdentifier=key["KeyArn"])
    assert (
        client("us-west-2").get_key(KeyIdentifier=replica_arn)["Key"]["Enabled"]
        is False
    )
    east.start_key_usage(KeyIdentifier=key["KeyArn"])
    east.delete_key(KeyIdentifier=key["KeyArn"])
    assert (
        client("us-west-2").get_key(KeyIdentifier=replica_arn)["Key"]["KeyState"]
        == "DELETE_PENDING"
    )
    east.restore_key(KeyIdentifier=key["KeyArn"])
    east.remove_key_replication_regions(
        KeyIdentifier=key["KeyArn"], ReplicationRegions=["us-west-2"]
    )
    with pytest.raises(ClientError):
        client("us-west-2").get_key(KeyIdentifier=replica_arn)


@mock_aws
def test_import_export_certificates_and_token_reuse():
    pc = client()
    import_parameters = pc.get_parameters_for_import(
        KeyMaterialType="ROOT_PUBLIC_KEY_CERTIFICATE", WrappingKeyAlgorithm="RSA_2048"
    )
    reused = pc.get_parameters_for_import(
        KeyMaterialType="ROOT_PUBLIC_KEY_CERTIFICATE",
        WrappingKeyAlgorithm="RSA_2048",
        ReuseLastGeneratedToken=True,
    )
    assert reused["ImportToken"] == import_parameters["ImportToken"]

    imported = pc.import_key(
        KeyMaterial={
            "RootCertificatePublicKey": {
                "KeyAttributes": PUBLIC_ATTRIBUTES,
                "PublicKeyCertificate": import_parameters["WrappingKeyCertificate"],
            }
        },
        Enabled=True,
    )["Key"]
    certificate = pc.get_public_key_certificate(KeyIdentifier=imported["KeyArn"])
    assert certificate["KeyCertificate"].startswith("-----BEGIN CERTIFICATE-----")
    signing_key = pc.create_key(KeyAttributes=PAIR_ATTRIBUTES, Exportable=False)["Key"]
    csr = pc.get_certificate_signing_request(
        KeyIdentifier=signing_key["KeyArn"],
        SigningAlgorithm="SHA256",
        CertificateSubject={"CommonName": "moto.example", "Country": "US"},
    )["CertificateSigningRequest"]
    assert csr.startswith("-----BEGIN CERTIFICATE REQUEST-----")

    export_parameters = pc.get_parameters_for_export(
        KeyMaterialType="TR34_KEY_BLOCK", SigningKeyAlgorithm="RSA_2048"
    )
    assert (
        pc.get_parameters_for_export(
            KeyMaterialType="TR34_KEY_BLOCK",
            SigningKeyAlgorithm="RSA_2048",
            ReuseLastGeneratedToken=True,
        )["ExportToken"]
        == export_parameters["ExportToken"]
    )
    exportable = pc.create_key(KeyAttributes=ATTRIBUTES, Exportable=True)["Key"]
    wrapping = pc.create_key(KeyAttributes=WRAPPING_ATTRIBUTES, Exportable=True)["Key"]
    wrapped = pc.export_key(
        KeyMaterial={"Tr31KeyBlock": {"WrappingKeyIdentifier": wrapping["KeyArn"]}},
        ExportKeyIdentifier=exportable["KeyArn"],
    )["WrappedKey"]
    assert wrapped["WrappedKeyMaterialFormat"] == "TR31_KEY_BLOCK"
    reimported = pc.import_key(
        KeyMaterial={
            "Tr31KeyBlock": {
                "WrappingKeyIdentifier": wrapping["KeyArn"],
                "WrappedKeyBlock": wrapped["KeyMaterial"],
            }
        }
    )["Key"]
    assert reimported["KeyAttributes"] == exportable["KeyAttributes"]
    assert reimported["KeyCheckValue"] == exportable["KeyCheckValue"]


@mock_aws
def test_kcv_matches_aes_cmac():
    pc = client()
    wrapped = "00" * 16
    token = pc.get_parameters_for_import(
        KeyMaterialType="KEY_CRYPTOGRAM", WrappingKeyAlgorithm="RSA_2048"
    )["ImportToken"]
    key = pc.import_key(
        KeyMaterial={
            "KeyCryptogram": {
                "KeyAttributes": ATTRIBUTES,
                "Exportable": True,
                "WrappedKeyCryptogram": wrapped,
                "ImportToken": token,
            }
        }
    )["Key"]
    material = hashlib.sha256(wrapped.encode()).digest()[:16]
    calculator = cmac.CMAC(AES(material))
    calculator.update(bytes(16))
    assert key["KeyCheckValue"] == calculator.finalize()[:3].hex().upper()


@mock_aws
def test_import_token_is_bound_to_material_type():
    pc = client()
    token = pc.get_parameters_for_import(
        KeyMaterialType="TR31_KEY_BLOCK", WrappingKeyAlgorithm="RSA_2048"
    )["ImportToken"]
    with pytest.raises(ClientError) as error:
        pc.import_key(
            KeyMaterial={
                "KeyCryptogram": {
                    "KeyAttributes": ATTRIBUTES,
                    "Exportable": True,
                    "WrappedKeyCryptogram": "00" * 16,
                    "ImportToken": token,
                }
            }
        )
    assert error.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_csr_uses_requested_key_size_and_hash():
    pc = client()
    attributes = {**PAIR_ATTRIBUTES, "KeyAlgorithm": "RSA_3072"}
    key = pc.create_key(KeyAttributes=attributes, Exportable=False)["Key"]
    pem = pc.get_certificate_signing_request(
        KeyIdentifier=key["KeyArn"],
        SigningAlgorithm="SHA384",
        CertificateSubject={"CommonName": "moto.example"},
    )["CertificateSigningRequest"]
    csr = x509.load_pem_x509_csr(pem.encode())
    assert csr.public_key().key_size == 3072
    assert csr.signature_hash_algorithm.name == "sha384"


@mock_aws
def test_mpa_team_association_lifecycle():
    pc = client()
    action = "IMPORT_ROOT_PUBLIC_KEY_CERTIFICATE"
    team = "arn:aws:mpa:us-east-1:123456789012:approval-team/moto"
    association = pc.associate_mpa_team(Action=action, MpaTeamArn=team)[
        "MpaTeamAssociation"
    ]
    assert association["AssociationState"] == "ACTIVE"
    assert (
        pc.get_mpa_team_association(Action=action)["MpaTeamAssociation"] == association
    )
    removed = pc.disassociate_mpa_team(Action=action)["MpaTeamAssociation"]
    assert removed["AssociationState"] == "DELETE_PENDING"
    assert pc.get_mpa_team_association(Action=action)["MpaTeamAssociation"] == removed


@mock_aws
def test_missing_key_raises_resource_not_found():
    with pytest.raises(ClientError) as exc:
        client().get_key(KeyIdentifier="0000000000000000")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_control_plane_validation_errors():
    pc = client()
    key = pc.create_key(KeyAttributes=ATTRIBUTES, Exportable=True)["Key"]

    pc.create_alias(AliasName="alias/duplicate", KeyArn=key["KeyArn"])
    with pytest.raises(ClientError) as error:
        pc.create_alias(AliasName="alias/duplicate", KeyArn=key["KeyArn"])
    assert error.value.response["Error"]["Code"] == "ConflictException"

    with pytest.raises(ClientError) as error:
        pc.list_keys(NextToken="not-a-pagination-token")
    assert error.value.response["Error"]["Code"] == "ValidationException"

    with pytest.raises(ClientError) as error:
        pc.put_resource_policy(ResourceArn=key["KeyArn"], Policy="not-json")
    assert error.value.response["Error"]["Code"] == "ValidationException"

    with pytest.raises(ClientError) as error:
        pc.get_public_key_certificate(KeyIdentifier=key["KeyArn"])
    assert error.value.response["Error"]["Code"] == "ValidationException"
