from moto.utilities.id_generator import (
    TAG_KEY_CUSTOM_ID,
    ExistingIds,
    ResourceIdentifier,
    Tags,
    moto_id,
    moto_id_manager,
)

ACCOUNT = "account"
REGION = "us-east-1"
RESOURCE_NAME = "my-resource"

CUSTOM_ID = "custom"
GENERIC_ID = "generated"
TAG_ID = "fromTag"
SERVICE = "test-service"
RESOURCE = "test-resource"


@moto_id
def generate_test_id(
    resource_identifier: ResourceIdentifier,
    existing_ids: ExistingIds = None,
    tags: Tags = None,
):
    return GENERIC_ID


class TestResourceIdentifier(ResourceIdentifier):
    __test__ = False  # Prevent pytest discovery

    service = SERVICE
    resource = RESOURCE

    def generate(self, existing_ids: ExistingIds = None, tags: Tags = None) -> str:
        return generate_test_id(
            resource_identifier=self, existing_ids=existing_ids, tags=tags
        )


def test_generate_with_no_resource_identifier():
    generated_id = generate_test_id(None)
    assert generated_id == GENERIC_ID


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
    assert generated_id == GENERIC_ID


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
    assert generated_id == GENERIC_ID


def test_generate_with_tags_and_existing_id(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    generated_id = generate_test_id(
        resource_identifier=resource_identifier,
        existing_ids=[TAG_ID],
        tags={TAG_KEY_CUSTOM_ID: TAG_ID},
    )
    assert generated_id == GENERIC_ID


def test_generate_with_tags_fallback(set_custom_id):
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    set_custom_id(resource_identifier, CUSTOM_ID)
    generated_id = generate_test_id(
        resource_identifier=resource_identifier,
        existing_ids=[TAG_ID],
        tags={TAG_KEY_CUSTOM_ID: TAG_ID},
    )
    assert generated_id == CUSTOM_ID


def test_set_custom_id_lifecycle():
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, RESOURCE_NAME)

    moto_id_manager.set_custom_id(resource_identifier, CUSTOM_ID)

    found_id = moto_id_manager.get_custom_id(resource_identifier)
    assert found_id == CUSTOM_ID

    moto_id_manager.unset_custom_id(resource_identifier)

    found_id = moto_id_manager.get_custom_id(resource_identifier)
    assert found_id is None


def test_set_custom_id_name_is_not_set():
    resource_identifier = TestResourceIdentifier(ACCOUNT, REGION, None)
    moto_id_manager.set_custom_id(resource_identifier, CUSTOM_ID)

    assert moto_id_manager._custom_ids == {}
