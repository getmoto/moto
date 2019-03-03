from moto.core import BaseModel


class StateMachine(BaseModel):

    def __init__(self, name, definition=None, role_arn=None):
        super(StateMachine, self).__init__()
        self.name = name
        self.role_arn = role_arn
        self.status = 'ACTIVE'
        self.definition = definition or '{}'

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        props = cloudformation_json['Properties']
        name = props.get('StateMachineName') or resource_name
        definition = props.get('DefinitionString')
        role_arn = props.get('RoleArn')
        # TODO: create backend implementation and keep a reference to this StateMachine instance
        return StateMachine(name, definition=definition, role_arn=role_arn)
