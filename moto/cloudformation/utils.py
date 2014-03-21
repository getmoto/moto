import uuid


def generate_stack_id(stack_name):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:us-east-1:123456789:stack/{}/{}".format(stack_name, random_id)
