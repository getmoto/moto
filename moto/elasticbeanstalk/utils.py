def make_arn(region, account_id, resource_type, resource_path):
    arn_template = (
        "arn:aws:elasticbeanstalk:{region}:{account_id}:{resource_type}/{resource_path}"
    )
    arn = arn_template.format(
        region=region,
        account_id=account_id,
        resource_type=resource_type,
        resource_path=resource_path,
    )
    return arn
