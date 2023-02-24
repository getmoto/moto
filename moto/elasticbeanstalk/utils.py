def make_arn(
    region: str, account_id: str, resource_type: str, resource_path: str
) -> str:
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
