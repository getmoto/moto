import hashlib
import random


def _generate_random_sha():
    return hashlib.sha256(f"{random.randint(0,100)}".encode("utf-8")).hexdigest()


def _create_image_layers(n):
    layers = []
    for _ in range(n):
        layers.append(
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": random.randint(100, 1000),
                "digest": f"sha256:{_generate_random_sha()}",
            }
        )
    return layers


def _create_image_digest(layers):
    layer_digests = "".join([layer["digest"] for layer in layers])
    return hashlib.sha256(f"{layer_digests}".encode("utf-8")).hexdigest()


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
