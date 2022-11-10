def parameter_arn(account_id, region, parameter_name):
    if parameter_name[0] == "/":
        parameter_name = parameter_name[1:]
    return f"arn:aws:ssm:{region}:{account_id}:parameter/{parameter_name}"


def convert_to_tree(parameters):
    """
    Convert input into a smaller, less redundant data set in tree form
    Input: [{"Name": "/a/b/c", "Value": "af-south-1", ...}, ..]
    Output: {"a": {"b": {"c": {"Value": af-south-1}, ..}, ..}, ..}
    """
    tree_dict = {}
    for p in parameters:
        current_level = tree_dict
        for path in p["Name"].split("/"):
            if path == "":
                continue
            if path not in current_level:
                current_level[path] = {}
            current_level = current_level[path]
        current_level["Value"] = p["Value"]
    return tree_dict


def convert_to_params(tree):
    """
    Inverse of 'convert_to_tree'
    """

    def m(tree, params, current_path=""):
        for key, value in tree.items():
            if key == "Value":
                params.append({"Name": current_path, "Value": value})
            else:
                m(value, params, current_path + "/" + key)

    params = []
    m(tree, params)
    return params
