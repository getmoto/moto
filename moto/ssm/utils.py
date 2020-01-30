ACCOUNT_ID = "1234567890"


def parameter_arn(region, parameter_name):
    if parameter_name[0] == "/":
        parameter_name = parameter_name[1:]
    return "arn:aws:ssm:{0}:{1}:parameter/{2}".format(
        region, ACCOUNT_ID, parameter_name
    )
