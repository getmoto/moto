import hashlib
import random

# Manifests Spec: https://docs.docker.com/registry/spec/manifest-v2-2/


def _generate_random_sha():
    random_sha = hashlib.sha256(f"{random.randint(0,100)}".encode("utf-8")).hexdigest()
    return f"sha256:{random_sha}"


def _create_image_layers(n):
    layers = []
    for _ in range(n):
        layers.append(
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": random.randint(100, 1000),
                "digest": _generate_random_sha(),
            }
        )
    return layers


def _create_image_digest(layers):
    layer_digests = "".join([layer["digest"] for layer in layers])
    summed_digest = hashlib.sha256(f"{layer_digests}".encode("utf-8")).hexdigest()
    return f"sha256:{summed_digest}"


def _create_image_manifest(image_digest=None):
    layers = _create_image_layers(5)
    if image_digest is None:
        image_digest = _create_image_digest(layers)
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": sum([layer["size"] for layer in layers]),
            "digest": image_digest,
        },
        "layers": layers,
    }


def _create_manifest_list_distribution(
    image_manifest: dict, architecture: str = "amd64", os: str = "linux"
):
    return {
        "mediaType": image_manifest["config"]["mediaType"],
        "digest": image_manifest["config"]["digest"],
        "size": image_manifest["config"]["size"],
        "platform": {"architecture": architecture, "os": os},
    }


def _create_image_manifest_list():
    arm_image_manifest = _create_image_manifest()
    amd_image_manifest = _create_image_manifest()
    arm_distribution = _create_manifest_list_distribution(
        arm_image_manifest, architecture="arm64"
    )
    amd_distribution = _create_manifest_list_distribution(
        amd_image_manifest, architecture="amd64"
    )
    manifest_list = {
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "schemaVersion": 2,
        "manifests": [arm_distribution, amd_distribution],
    }

    return {
        "image_manifests": [arm_image_manifest, amd_image_manifest],
        "manifest_list": manifest_list,
    }
