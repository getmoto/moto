def create_cloudformation_stack_from_template(
    account_id: str, stack_name: str, region_name: str, template: str
):
    from moto.cloudformation import models as cloudformation_models

    cf_backend = cloudformation_models.cloudformation_backends[account_id][region_name]
    stack = cf_backend.create_stack(name=stack_name, template=template, parameters={})

    return stack
