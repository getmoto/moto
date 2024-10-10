from moto.utilities.id_generator import (
    TAG_KEY_CUSTOM_ID,
    ExistingIds,
    ResourceIdentifier,
    Tags,
    moto_id,
)

ACCOUNT = "account"
REGION = "us-east-1"
RESOURCE_NAME = "my-resource"

CUSTOM_ID = "custom"
GENERATED_ID = "generated"
TAG_ID = "fromTag"
SERVICE = "test-service"
RESOURCE = "test-resource"


@moto_id
def generate_test_id(
    resource_identifier: ResourceIdentifier,
    existing_ids: ExistingIds = None,
    tags: Tags = None,
):
    return GENERATED_ID


class TestResourceIdentifier(ResourceIdentifier):
    service = SERVICE
    resource = RESOURCE

    def generate(self, existing_ids: ExistingIds = None, tags: Tags = None) -> str:
        return generate_test_id(
            resource_identifier=self, existing_ids=existing_ids, tags=tags
        )


def test_generate_with_no_resource_identifier():
    generated_id = generate_test_id(None)
    assert generated_id == GENERATED_ID


def test_generate_with_matching_resource_identifier(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    set_custom_id(resource_identifier, CUSTOM_ID)

    generated_id = generate_test_id(resource_identifier=resource_identifier)
    assert generated_id == CUSTOM_ID


def test_generate_with_non_matching_resource_identifier(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)
    resource_identifier_2 = TestResourceIdentifier(ACCOUNT, REGION, "non-matching")

    set_custom_id(resource_identifier, CUSTOM_ID)

    generated_id = generate_test_id(resource_identifier=resource_identifier_2)
    assert generated_id == GENERATED_ID


def test_generate_with_custom_id_tag():
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    generated_id = generate_test_id(
        resource_identifier=resource_identifier, tags={TAG_KEY_CUSTOM_ID: TAG_ID}
    )
    assert generated_id == TAG_ID


def test_generate_with_custom_id_tag_has_priority(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    set_custom_id(resource_identifier, CUSTOM_ID)
    generated_id = generate_test_id(
        resource_identifier=resource_identifier, tags={TAG_KEY_CUSTOM_ID: TAG_ID}
    )
    assert generated_id == TAG_ID


def test_generate_with_existing_id(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    set_custom_id(resource_identifier, CUSTOM_ID)
    generated_id = generate_test_id(
        resource_identifier=resource_identifier, existing_ids=[CUSTOM_ID]
    )
    assert generated_id == GENERATED_ID


def test_generate_with_tags_and_existing_id(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    generated_id = generate_test_id(
        resource_identifier=resource_identifier,
        existing_ids=[TAG_ID],
        tags={TAG_KEY_CUSTOM_ID: TAG_ID},
    )
    assert generated_id == GENERATED_ID


def test_generate_with_tags_fallback(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    set_custom_id(resource_identifier, CUSTOM_ID)
    generated_id = generate_test_id(
        resource_identifier=resource_identifier,
        existing_ids=[TAG_ID],
        tags={TAG_KEY_CUSTOM_ID: TAG_ID},
    )
    assert generated_id == CUSTOM_ID
