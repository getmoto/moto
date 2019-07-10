def make_arn_for_load_balancer(account_id, name, region_name):
    return "arn:aws:elasticloadbalancing:{}:{}:loadbalancer/{}/50dc6c495c0c9188".format(
        region_name, account_id, name
    )


def make_arn_for_target_group(account_id, name, region_name):
    return "arn:aws:elasticloadbalancing:{}:{}:targetgroup/{}/50dc6c495c0c9188".format(
        region_name, account_id, name
    )
