from moto.stepfunctions.parser.api import RoutingConfigurationListItem
from moto.stepfunctions.parser.backend.alias import Alias


def test_alias():
    alias = Alias(
        state_machine_arn="test",
        name="abc",
        description="test description",
        routing_configuration_list=[
            RoutingConfigurationListItem(
                stateMachineVersionArn="test",
                weight=1,
            )
        ],
    )
    assert alias.name == "abc"
    assert alias.state_machine_alias_arn == "test:abc"
    output = alias.to_description()
    assert output["description"] == "test description"
    assert alias.is_idempotent(alias)
