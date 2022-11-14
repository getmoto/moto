def make_arn_for_load_balancer(account_id, name, region_name):
    return f"arn:aws:elasticloadbalancing:{region_name}:{account_id}:loadbalancer/app/{name}/50dc6c495c0c9188"


def make_arn_for_target_group(account_id, name, region_name):
    return f"arn:aws:elasticloadbalancing:{region_name}:{account_id}:targetgroup/{name}/50dc6c495c0c9188"
