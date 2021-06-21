import fnmatch
import re
def make_arn_for_load_balancer(account_id, name, region_name):
    return "arn:aws:elasticloadbalancing:{}:{}:loadbalancer/{}/50dc6c495c0c9188".format(
        region_name, account_id, name
    )


def make_arn_for_target_group(account_id, name, region_name):
    return "arn:aws:elasticloadbalancing:{}:{}:targetgroup/{}/50dc6c495c0c9188".format(
        region_name, account_id, name
    )

def simple_aws_filter_to_re(filter_string):
    tmp_filter = filter_string.replace(r"\?", "[?]")
    tmp_filter = tmp_filter.replace(r"\*", "[*]")
    tmp_filter = fnmatch.translate(tmp_filter)
    return tmp_filter

def filters_from_querystring(querystring_dict):
    response_values = {}
    last_tag_key = None
    for key, value in sorted(querystring_dict.items()):
        match = re.search(r"Filter.(\d).Name", key)
        if match:
            filter_index = match.groups()[0]
            value_prefix = "Filter.{0}.Value".format(filter_index)
            filter_values = [
                filter_value[0]
                for filter_key, filter_value in querystring_dict.items()
                if filter_key.startswith(value_prefix)
            ]
            if value[0] == "tag-key":
                last_tag_key = "tag:" + filter_values[0]
            elif last_tag_key and value[0] == "tag-value":
                response_values[last_tag_key] = filter_values
            response_values[value[0]] = filter_values
    return response_values
