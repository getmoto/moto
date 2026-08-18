"""Models for the AWS Payment Cryptography control plane."""

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from cryptography import x509
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives import cmac, hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.x509.oid import NameOID

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.utils import utcnow

from .exceptions import (
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)


def _id() -> str:
    return uuid.uuid4().hex[:16]


def _default_kcv_algorithm(algorithm: str) -> str:
    if algorithm.startswith("AES"):
        return "CMAC"
    if algorithm.startswith("HMAC"):
        return "HMAC"
    if algorithm.startswith("TDES"):
        return "ANSI_X9_24"
    return "SHA_1"


def _material_size(algorithm: str) -> int:
    sizes = {
        "AES_128": 16,
        "AES_192": 24,
        "AES_256": 32,
        "TDES_2KEY": 16,
        "TDES_3KEY": 24,
        "HMAC_SHA256": 32,
        "HMAC_SHA384": 48,
        "HMAC_SHA512": 64,
    }
    return sizes.get(algorithm, 32)


def _private_key(algorithm: str) -> Any:
    rsa_sizes = {"RSA_2048": 2048, "RSA_3072": 3072, "RSA_4096": 4096}
    curves = {
        "ECC_NIST_P256": ec.SECP256R1,
        "ECC_NIST_P384": ec.SECP384R1,
        "ECC_NIST_P521": ec.SECP521R1,
    }
    if algorithm in rsa_sizes:
        return rsa.generate_private_key(
            public_exponent=65537, key_size=rsa_sizes[algorithm]
        )
    if algorithm in curves:
        return ec.generate_private_key(curves[algorithm]())
    return None


def _calculate_kcv(
    material: bytes, algorithm: str, kcv_algorithm: str, private_key: Any = None
) -> str:
    if algorithm.startswith("AES") and kcv_algorithm == "CMAC":
        cmac_calculator = cmac.CMAC(AES(material))
        cmac_calculator.update(bytes(16))
        return cmac_calculator.finalize()[:3].hex().upper()
    if algorithm.startswith("TDES") and kcv_algorithm == "ANSI_X9_24":
        encryptor = Cipher(TripleDES(material), modes.ECB()).encryptor()
        return encryptor.update(bytes(8))[:3].hex().upper()
    if algorithm.startswith("HMAC") and kcv_algorithm == "HMAC":
        digest = {
            "HMAC_SHA224": hashes.SHA224,
            "HMAC_SHA256": hashes.SHA256,
            "HMAC_SHA384": hashes.SHA384,
            "HMAC_SHA512": hashes.SHA512,
        }.get(algorithm, hashes.SHA256)
        digest_algorithm = digest()
        hmac_calculator = hmac.HMAC(material, digest_algorithm)
        hmac_calculator.update(bytes(digest_algorithm.digest_size))
        return hmac_calculator.finalize()[:3].hex().upper()
    if private_key is not None:
        material = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    return hashlib.sha1(material).hexdigest().upper()[:6]  # noqa: S324


class Key:
    def __init__(
        self,
        account_id: str,
        region: str,
        attributes: dict[str, Any],
        exportable: bool,
        enabled: bool = True,
        kcv_algorithm: str | None = None,
        origin: str = "AWS_PAYMENT_CRYPTOGRAPHY",
        material: bytes | None = None,
        derive_key_usage: str | None = None,
        key_id: str | None = None,
    ):
        self.key_id = key_id or _id()
        self.account_id = account_id
        self.region = region
        self.arn = (
            f"arn:aws:payment-cryptography:{region}:{account_id}:key/{self.key_id}"
        )
        self.attributes = attributes
        self.exportable = exportable
        self.enabled = enabled
        self.origin = origin
        algorithm = attributes.get("KeyAlgorithm", "")
        expected_class = (
            "ASYMMETRIC_KEY_PAIR"
            if algorithm.startswith(("RSA", "ECC"))
            and origin == "AWS_PAYMENT_CRYPTOGRAPHY"
            else None
        )
        if expected_class and attributes.get("KeyClass") != expected_class:
            raise ValidationException(
                f"{algorithm} requires KeyClass {expected_class} when creating a key"
            )
        self.private_key: Any = _private_key(algorithm) if material is None else None
        if material is not None:
            self.material = material
        elif self.private_key is not None:
            self.material = self.private_key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        else:
            self.material = os.urandom(_material_size(algorithm))
        self.kcv_algorithm = kcv_algorithm or _default_kcv_algorithm(
            attributes.get("KeyAlgorithm", "")
        )
        expected_kcv = _default_kcv_algorithm(algorithm)
        if self.kcv_algorithm != expected_kcv:
            raise ValidationException(
                f"{self.kcv_algorithm} is not valid for {algorithm}; expected {expected_kcv}"
            )
        self.kcv = _calculate_kcv(
            self.material, algorithm, self.kcv_algorithm, self.private_key
        )
        self.state = "CREATE_COMPLETE"
        self.created = utcnow()
        self.usage_start = self.created if enabled else None
        self.usage_stop = self.created if not enabled else None
        self.delete_pending: datetime | None = None
        self.delete_timestamp: datetime | None = None
        self.derive_key_usage = derive_key_usage
        self.multi_region_type: str | None = None
        self.primary_region: str | None = None
        self.replication_status: dict[str, dict[str, str]] | None = None
        self.using_defaults: bool | None = None
        self.public_certificate: str | None = None
        self.mpa_status: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "KeyArn": self.arn,
            "KeyAttributes": self.attributes,
            "KeyCheckValue": self.kcv,
            "KeyCheckValueAlgorithm": self.kcv_algorithm,
            "Enabled": self.enabled,
            "Exportable": self.exportable,
            "KeyState": self.state,
            "KeyOrigin": self.origin,
            "CreateTimestamp": self.created,
        }
        optional = {
            "UsageStartTimestamp": self.usage_start,
            "UsageStopTimestamp": self.usage_stop,
            "DeletePendingTimestamp": self.delete_pending,
            "DeleteTimestamp": self.delete_timestamp,
            "DeriveKeyUsage": self.derive_key_usage,
            "MultiRegionKeyType": self.multi_region_type,
            "PrimaryRegion": self.primary_region,
            "ReplicationStatus": self.replication_status,
            "UsingDefaultReplicationRegions": self.using_defaults,
            "MpaStatus": self.mpa_status,
        }
        result.update({k: v for k, v in optional.items() if v is not None})
        return result


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of Payment Cryptography control-plane APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.keys: dict[str, Key] = {}
        self.aliases: dict[str, str | None] = {}
        self.tags: dict[str, dict[str, str]] = {}
        self.policies: dict[str, str] = {}
        self.default_replication_regions: list[str] = []
        self.import_tokens: dict[str, dict[str, Any]] = {}
        self.export_tokens: dict[str, dict[str, Any]] = {}
        self.last_import_token: str | None = None
        self.last_export_token: str | None = None
        self.mpa_associations: dict[str, dict[str, Any]] = {}

    def _resolve(self, identifier: str) -> Key:
        if identifier.startswith("alias/"):
            identifier = self.aliases.get(identifier) or ""
        for key in self.keys.values():
            if identifier in (key.arn, key.key_id):
                return key
        raise ResourceNotFoundException(f"Key {identifier} was not found")

    def _related_keys(self, key: Key) -> list[Key]:
        related = []
        for backend in paymentcryptography_backends[self.account_id].values():
            for candidate in backend.keys.values():
                if candidate.key_id == key.key_id:
                    related.append(candidate)
        return related

    def _update_related(self, key: Key, **values: Any) -> None:
        for related in self._related_keys(key):
            for name, value in values.items():
                setattr(related, name, value)

    def _require_mode(self, identifier: str, mode: str) -> Key:
        key = self._resolve(identifier)
        if not key.enabled or key.state != "CREATE_COMPLETE":
            raise ConflictException("The wrapping key is not enabled")
        modes_of_use = key.attributes.get("KeyModesOfUse", {})
        if not (modes_of_use.get(mode) or modes_of_use.get("NoRestrictions")):
            raise ValidationException(f"The key does not permit {mode.lower()}")
        return key

    def _paginate(
        self, values: list[Any], token: str | None, limit: int | None
    ) -> tuple[list[Any], str | None]:
        try:
            start = (
                int(base64.urlsafe_b64decode(token.encode()).decode()) if token else 0
            )
        except Exception:
            raise ValidationException("Invalid pagination token")
        size = limit or 100
        end = start + size
        next_token = (
            base64.urlsafe_b64encode(str(end).encode()).decode()
            if end < len(values)
            else None
        )
        return values[start:end], next_token

    def _replicate(
        self, key: Key, regions: list[str], using_defaults: bool = False
    ) -> None:
        key.multi_region_type = "PRIMARY"
        key.primary_region = self.region_name
        key.replication_status = key.replication_status or {}
        key.using_defaults = using_defaults
        for region in regions:
            if region == self.region_name:
                raise ValidationException(
                    "A key cannot be replicated to its primary region"
                )
            target = paymentcryptography_backends[self.account_id][region]
            replica = Key(
                self.account_id,
                region,
                key.attributes.copy(),
                key.exportable,
                key.enabled,
                key.kcv_algorithm,
                key.origin,
                key.material,
                key.derive_key_usage,
                key.key_id,
            )
            replica.created = key.created
            replica.kcv = key.kcv
            replica.multi_region_type = "REPLICA"
            replica.primary_region = self.region_name
            replica.public_certificate = key.public_certificate
            replica.private_key = key.private_key
            target.keys[replica.arn] = replica
            target.tags[replica.arn] = self.tags.get(key.arn, {}).copy()
            key.replication_status[region] = {"Status": "SYNCHRONIZED"}

    def create_key(self, **kwargs: Any) -> dict[str, Any]:
        key = Key(
            self.account_id,
            self.region_name,
            kwargs["key_attributes"],
            kwargs["exportable"],
            kwargs.get("enabled", True),
            kwargs.get("key_check_value_algorithm"),
            derive_key_usage=kwargs.get("derive_key_usage"),
        )
        self.keys[key.arn] = key
        self.tags[key.arn] = {t["Key"]: t["Value"] for t in kwargs.get("tags") or []}
        regions = kwargs.get("replication_regions")
        using_defaults = regions is None and bool(self.default_replication_regions)
        regions = self.default_replication_regions if regions is None else regions
        if regions:
            self._replicate(key, regions, using_defaults)
        return key.to_dict()

    def get_key(self, key_identifier: str) -> dict[str, Any]:
        return self._resolve(key_identifier).to_dict()

    def list_keys(
        self, key_state: str | None, next_token: str | None, max_results: int | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        values = sorted(self.keys.values(), key=lambda k: k.arn)
        if key_state:
            values = [k for k in values if k.state == key_state]
        page, token = self._paginate(values, next_token, max_results)
        return [k.to_dict() for k in page], token

    def delete_key(self, key_identifier: str, days: int | None) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        if key.state == "DELETE_PENDING":
            raise ConflictException("The key is already pending deletion")
        usage_stop = utcnow()
        delete_pending = usage_stop + timedelta(days=days or 7)
        self._update_related(
            key,
            enabled=False,
            state="DELETE_PENDING",
            usage_stop=usage_stop,
            delete_pending=delete_pending,
        )
        return key.to_dict()

    def restore_key(self, key_identifier: str) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        if key.state != "DELETE_PENDING":
            raise ConflictException("Only a key pending deletion can be restored")
        self._update_related(key, state="CREATE_COMPLETE", delete_pending=None)
        return key.to_dict()

    def start_key_usage(self, key_identifier: str) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        if key.state == "DELETE_PENDING":
            raise ConflictException("A key pending deletion cannot be enabled")
        if not key.enabled:
            self._update_related(key, enabled=True, usage_start=utcnow())
        return key.to_dict()

    def stop_key_usage(self, key_identifier: str) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        if key.state == "DELETE_PENDING":
            raise ConflictException("A key pending deletion cannot be disabled")
        if key.enabled:
            self._update_related(key, enabled=False, usage_stop=utcnow())
        return key.to_dict()

    def create_alias(self, alias_name: str, key_arn: str | None) -> dict[str, Any]:
        if alias_name in self.aliases:
            raise ConflictException(f"Alias {alias_name} already exists")
        if key_arn:
            key_arn = self._resolve(key_arn).arn
        self.aliases[alias_name] = key_arn
        return self._alias(alias_name)

    def _alias(self, name: str) -> dict[str, Any]:
        result: dict[str, Any] = {"AliasName": name}
        if self.aliases[name]:
            result["KeyArn"] = self.aliases[name]
        return result

    def get_alias(self, alias_name: str) -> dict[str, Any]:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(f"Alias {alias_name} was not found")
        return self._alias(alias_name)

    def list_aliases(
        self, key_arn: str | None, next_token: str | None, max_results: int | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        names = sorted(self.aliases)
        if key_arn:
            key_arn = self._resolve(key_arn).arn
            names = [n for n in names if self.aliases[n] == key_arn]
        page, token = self._paginate(names, next_token, max_results)
        return [self._alias(n) for n in page], token

    def update_alias(self, alias_name: str, key_arn: str | None) -> dict[str, Any]:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(f"Alias {alias_name} was not found")
        self.aliases[alias_name] = self._resolve(key_arn).arn if key_arn else None
        return self._alias(alias_name)

    def delete_alias(self, alias_name: str) -> None:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(f"Alias {alias_name} was not found")
        del self.aliases[alias_name]

    def tag_resource(self, resource_arn: str, tags: list[dict[str, str]]) -> None:
        key = self._resolve(resource_arn)
        current = self.tags.setdefault(key.arn, {})
        current.update({t["Key"]: t["Value"] for t in tags})

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        key = self._resolve(resource_arn)
        for name in tag_keys:
            self.tags.setdefault(key.arn, {}).pop(name, None)

    def list_tags_for_resource(
        self, resource_arn: str, next_token: str | None, max_results: int | None
    ) -> tuple[list[dict[str, str]], str | None]:
        key = self._resolve(resource_arn)
        values = [
            {"Key": k, "Value": v}
            for k, v in sorted(self.tags.get(key.arn, {}).items())
        ]
        return self._paginate(values, next_token, max_results)

    def put_resource_policy(self, resource_arn: str, policy: str) -> dict[str, str]:
        arn = self._resolve(resource_arn).arn
        try:
            json.loads(policy)
        except ValueError:
            raise ValidationException("The resource policy is not valid JSON")
        self.policies[arn] = policy
        return {"ResourceArn": arn, "Policy": policy}

    def get_resource_policy(self, resource_arn: str) -> dict[str, str]:
        arn = self._resolve(resource_arn).arn
        return {"ResourceArn": arn, "Policy": self.policies.get(arn, "{}")}

    def delete_resource_policy(self, resource_arn: str) -> None:
        arn = self._resolve(resource_arn).arn
        self.policies.pop(arn, None)

    def enable_default_key_replication_regions(self, regions: list[str]) -> list[str]:
        self.default_replication_regions = sorted(
            set(self.default_replication_regions + regions)
        )
        return self.default_replication_regions

    def disable_default_key_replication_regions(self, regions: list[str]) -> list[str]:
        self.default_replication_regions = [
            r for r in self.default_replication_regions if r not in regions
        ]
        return self.default_replication_regions

    def get_default_key_replication_regions(self) -> list[str]:
        return self.default_replication_regions

    def add_key_replication_regions(
        self, key_identifier: str, regions: list[str]
    ) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        if key.multi_region_type == "REPLICA":
            raise ConflictException(
                "Replication regions can only be changed on a primary key"
            )
        self._replicate(key, regions)
        return key.to_dict()

    def remove_key_replication_regions(
        self, key_identifier: str, regions: list[str]
    ) -> dict[str, Any]:
        key = self._resolve(key_identifier)
        for region in regions:
            paymentcryptography_backends[self.account_id][region].keys.pop(
                f"arn:aws:payment-cryptography:{region}:{self.account_id}:key/{key.key_id}",
                None,
            )
            if key.replication_status:
                key.replication_status.pop(region, None)
        return key.to_dict()

    def _certificate(self, algorithm: str, common_name: str) -> tuple[Any, str]:
        private = _private_key(algorithm)
        if private is None:
            raise ValidationException(f"{algorithm} is not an asymmetric key algorithm")
        subject = issuer = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(utcnow())
            .not_valid_after(utcnow() + timedelta(days=365))
            .sign(private, hashes.SHA256())
        )
        return private, cert.public_bytes(serialization.Encoding.PEM).decode()

    def _parameters(
        self, kind: str, material_type: str, algorithm: str, reuse: bool
    ) -> dict[str, Any]:
        store = self.import_tokens if kind == "Import" else self.export_tokens
        last = self.last_import_token if kind == "Import" else self.last_export_token
        if (
            reuse
            and last
            and store[last]["expires"] > utcnow()
            and store[last]["algorithm"] == algorithm
            and store[last]["material_type"] == material_type
        ):
            token = last
            item = store[token]
        else:
            token = f"{kind.lower()}-token-{uuid.uuid4().hex}"
            _, certificate = self._certificate(
                algorithm, f"Moto Payment Cryptography {kind}"
            )
            item = {
                "certificate": certificate,
                "algorithm": algorithm,
                "material_type": material_type,
                "expires": utcnow() + timedelta(days=30),
            }
            store[token] = item
            if kind == "Import":
                self.last_import_token = token
            else:
                self.last_export_token = token
        prefix = "Wrapping" if kind == "Import" else "Signing"
        return {
            f"{prefix}KeyCertificate": item["certificate"],
            f"{prefix}KeyCertificateChain": item["certificate"],
            f"{prefix}KeyAlgorithm": item["algorithm"],
            f"{kind}Token": token,
            "ParametersValidUntilTimestamp": item["expires"],
        }

    def _validate_token(
        self, token: str, kind: str, expected_material_type: str
    ) -> dict[str, Any]:
        store = self.import_tokens if kind == "Import" else self.export_tokens
        if token not in store:
            raise ValidationException(f"The {kind.lower()} token is not valid")
        item = store[token]
        if item["expires"] <= utcnow():
            raise ValidationException(f"The {kind.lower()} token has expired")
        if item["material_type"] != expected_material_type:
            raise ValidationException(
                f"The {kind.lower()} token is not valid for {expected_material_type}"
            )
        return item

    def _wrapped_payload(self, key: Key, variant: str) -> str:
        payload = json.dumps(
            {
                "attributes": key.attributes,
                "derive_key_usage": key.derive_key_usage,
                "exportable": key.exportable,
                "material": base64.b64encode(key.material).decode(),
            },
            separators=(",", ":"),
        ).encode()
        if variant in {"Tr31KeyBlock", "DiffieHellmanTr31KeyBlock"}:
            return "MOTO1" + base64.b32encode(payload).decode().rstrip("=")
        return payload.hex().upper()

    def _decode_wrapped_payload(
        self, variant: str, value: dict[str, Any]
    ) -> dict[str, Any] | None:
        wrapped = value.get("WrappedKeyBlock") or value.get("WrappedKeyCryptogram")
        if not wrapped:
            return None
        try:
            if variant in {"Tr31KeyBlock", "DiffieHellmanTr31KeyBlock"}:
                if not wrapped.startswith("MOTO1"):
                    return None
                encoded = wrapped[5:]
                encoded += "=" * (-len(encoded) % 8)
                raw = base64.b32decode(encoded)
            else:
                raw = bytes.fromhex(wrapped)
            payload = json.loads(raw)
            if not {"attributes", "exportable", "material"}.issubset(payload):
                return None
            return payload
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def get_parameters_for_import(
        self, material_type: str, algorithm: str, reuse: bool
    ) -> dict[str, Any]:
        return self._parameters("Import", material_type, algorithm, reuse)

    def get_parameters_for_export(
        self, material_type: str, algorithm: str, reuse: bool
    ) -> dict[str, Any]:
        return self._parameters("Export", material_type, algorithm, reuse)

    def import_key(self, key_material: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        variant, value = next(iter(key_material.items()))
        material_types = {
            "Tr31KeyBlock": "TR31_KEY_BLOCK",
            "DiffieHellmanTr31KeyBlock": "TR31_KEY_BLOCK",
            "Tr34KeyBlock": "TR34_KEY_BLOCK",
            "KeyCryptogram": "KEY_CRYPTOGRAM",
        }
        token = value.get("ImportToken")
        if token:
            self._validate_token(token, "Import", material_types.get(variant, ""))
        elif variant == "KeyCryptogram":
            raise ValidationException("ImportToken is required for KeyCryptogram")
        wrapping_identifier = value.get("WrappingKeyIdentifier")
        if wrapping_identifier:
            self._require_mode(wrapping_identifier, "Unwrap")
        payload = self._decode_wrapped_payload(variant, value)
        attrs = payload["attributes"] if payload else value.get("KeyAttributes")
        exportable = (
            payload["exportable"] if payload else value.get("Exportable", False)
        )
        if attrs is None and variant == "As2805KeyCryptogram":
            attrs = {
                "KeyUsage": value["As2805KeyVariant"],
                "KeyClass": "SYMMETRIC_KEY",
                "KeyAlgorithm": value["KeyAlgorithm"],
                "KeyModesOfUse": value["KeyModesOfUse"],
            }
            exportable = value["Exportable"]
        if attrs is None:
            attrs = {
                "KeyUsage": "TR31_K0_KEY_ENCRYPTION_KEY",
                "KeyClass": "SYMMETRIC_KEY",
                "KeyAlgorithm": "TDES_3KEY",
                "KeyModesOfUse": {"NoRestrictions": True},
            }
        public_certificate = value.get("PublicKeyCertificate")
        if payload:
            raw = base64.b64decode(payload["material"])
        elif public_certificate:
            try:
                certificate = x509.load_pem_x509_certificate(
                    public_certificate.encode()
                )
                raw = certificate.public_key().public_bytes(
                    serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            except ValueError:
                raise ValidationException(
                    "PublicKeyCertificate is not a valid certificate"
                )
        else:
            wrapped = value.get("WrappedKeyBlock") or value.get("WrappedKeyCryptogram")
            if not wrapped:
                raise ValidationException("KeyMaterial does not contain key material")
            raw = hashlib.sha256(wrapped.encode()).digest()[
                : _material_size(attrs["KeyAlgorithm"])
            ]
        key = Key(
            self.account_id,
            self.region_name,
            attrs,
            exportable,
            kwargs.get("enabled", True),
            kwargs.get("key_check_value_algorithm"),
            "EXTERNAL",
            raw,
            derive_key_usage=(payload or {}).get("derive_key_usage"),
        )
        if public_certificate:
            key.public_certificate = public_certificate
        self.keys[key.arn] = key
        self.tags[key.arn] = {t["Key"]: t["Value"] for t in kwargs.get("tags") or []}
        if kwargs.get("replication_regions"):
            self._replicate(key, kwargs["replication_regions"])
        return key.to_dict()

    def export_key(
        self,
        key_material: dict[str, Any],
        identifier: str,
        export_attributes: dict[str, Any] | None,
    ) -> dict[str, Any]:
        key = self._resolve(identifier)
        if not key.exportable:
            raise ConflictException("The key is not exportable")
        variant, spec = next(iter(key_material.items()))
        if variant == "Tr34KeyBlock" and spec.get("ExportToken"):
            self._validate_token(spec["ExportToken"], "Export", "TR34_KEY_BLOCK")
        wrapping_identifier = (
            spec.get("WrappingKeyIdentifier")
            or spec.get("CertificateAuthorityPublicKeyIdentifier")
            or identifier
        )
        if spec.get("WrappingKeyIdentifier"):
            wrapping_arn = self._require_mode(wrapping_identifier, "Wrap").arn
        else:
            wrapping_arn = self._resolve(wrapping_identifier).arn
        formats = {
            "Tr31KeyBlock": "TR31_KEY_BLOCK",
            "Tr34KeyBlock": "TR34_KEY_BLOCK",
            "KeyCryptogram": "KEY_CRYPTOGRAM",
            "DiffieHellmanTr31KeyBlock": "TR31_KEY_BLOCK",
            "As2805KeyCryptogram": "KEY_CRYPTOGRAM",
        }
        return {
            "WrappingKeyArn": wrapping_arn,
            "WrappedKeyMaterialFormat": formats[variant],
            "KeyMaterial": self._wrapped_payload(key, variant),
            "KeyCheckValue": key.kcv,
            "KeyCheckValueAlgorithm": (export_attributes or {}).get(
                "KeyCheckValueAlgorithm", key.kcv_algorithm
            ),
        }

    def get_public_key_certificate(self, identifier: str) -> dict[str, str]:
        key = self._resolve(identifier)
        if key.attributes.get("KeyClass") not in {
            "ASYMMETRIC_KEY_PAIR",
            "PUBLIC_KEY",
        }:
            raise ValidationException("The key must be an asymmetric key")
        if not key.public_certificate:
            if key.private_key is None:
                raise ConflictException(
                    "No public certificate is available for this key"
                )
            subject = issuer = x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, key.key_id)]
            )
            certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(utcnow())
                .not_valid_after(utcnow() + timedelta(days=365))
                .sign(key.private_key, hashes.SHA256())
            )
            key.public_certificate = certificate.public_bytes(
                serialization.Encoding.PEM
            ).decode()
        return {
            "KeyCertificate": key.public_certificate,
            "KeyCertificateChain": key.public_certificate,
        }

    def get_certificate_signing_request(
        self, identifier: str, signing_algorithm: str, subject: dict[str, str]
    ) -> str:
        key = self._resolve(identifier)
        if key.attributes.get("KeyClass") != "ASYMMETRIC_KEY_PAIR":
            raise ValidationException("The key must be an asymmetric key pair")
        if key.private_key is None:
            raise ConflictException("The private key is not available")
        names = {
            "CommonName": NameOID.COMMON_NAME,
            "OrganizationUnit": NameOID.ORGANIZATIONAL_UNIT_NAME,
            "Organization": NameOID.ORGANIZATION_NAME,
            "City": NameOID.LOCALITY_NAME,
            "Country": NameOID.COUNTRY_NAME,
            "StateOrProvince": NameOID.STATE_OR_PROVINCE_NAME,
            "EmailAddress": NameOID.EMAIL_ADDRESS,
        }
        csr_subject = x509.Name(
            [x509.NameAttribute(names[k], v) for k, v in subject.items() if k in names]
        )
        signing_hash: Any = {
            "SHA224": hashes.SHA224,
            "SHA256": hashes.SHA256,
            "SHA384": hashes.SHA384,
            "SHA512": hashes.SHA512,
        }[signing_algorithm]()
        return (
            x509.CertificateSigningRequestBuilder()
            .subject_name(csr_subject)
            .sign(key.private_key, signing_hash)
            .public_bytes(serialization.Encoding.PEM)
            .decode()
        )

    def associate_mpa_team(
        self, action: str, team_arn: str, comment: str | None
    ) -> dict[str, Any]:
        if action in self.mpa_associations:
            raise ConflictException(f"An MPA team is already associated with {action}")
        association = {
            "Action": action,
            "MpaTeamArn": team_arn,
            "AssociationState": "ACTIVE",
        }
        self.mpa_associations[action] = association
        return association

    def get_mpa_team_association(self, action: str) -> dict[str, Any]:
        if action not in self.mpa_associations:
            raise ResourceNotFoundException(f"No MPA team is associated with {action}")
        return self.mpa_associations[action]

    def disassociate_mpa_team(self, action: str, comment: str | None) -> dict[str, Any]:
        association = self.get_mpa_team_association(action).copy()
        association["AssociationState"] = "DELETE_PENDING"
        self.mpa_associations[action] = association
        return association


paymentcryptography_backends = BackendDict(
    PaymentCryptographyControlPlaneBackend,
    "payment-cryptography",
    additional_regions=[
        "af-south-1",
        "ap-east-1",
        "ap-east-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-south-1",
        "ap-south-2",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-southeast-3",
        "ap-southeast-4",
        "ap-southeast-5",
        "ap-southeast-6",
        "ap-southeast-7",
        "ca-central-1",
        "ca-west-1",
        "eu-central-1",
        "eu-central-2",
        "eu-north-1",
        "eu-south-1",
        "eu-south-2",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "il-central-1",
        "me-central-1",
        "me-south-1",
        "mx-central-1",
        "sa-east-1",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ],
)
