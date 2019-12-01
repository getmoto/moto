def parameter_arn(region, parameter_name):
    if parameter_name[0] == "/":
        parameter_name = parameter_name[1:]
    return "arn:aws:ssm:{0}:1234567890:parameter/{1}".format(region, parameter_name)
