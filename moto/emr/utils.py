from __future__ import unicode_literals
import random
import string
from moto.core.utils import camelcase_to_underscores

import six


def random_id(size=13):
    chars = list(range(10)) + list(string.ascii_uppercase)
    return "".join(six.text_type(random.choice(chars)) for x in range(size))


def random_cluster_id(size=13):
    return "j-{0}".format(random_id())


def random_step_id(size=13):
    return "s-{0}".format(random_id())


def random_instance_group_id(size=13):
    return "i-{0}".format(random_id())


def steps_from_query_string(querystring_dict):
    steps = []
    for step in querystring_dict:
        step["jar"] = step.pop("hadoop_jar_step._jar")
        step["properties"] = dict(
            (o["Key"], o["Value"]) for o in step.get("properties", [])
        )
        step["args"] = []
        idx = 1
        keyfmt = "hadoop_jar_step._args.member.{0}"
        while keyfmt.format(idx) in step:
            step["args"].append(step.pop(keyfmt.format(idx)))
            idx += 1
        steps.append(step)
    return steps


class Unflattener:
    @staticmethod
    def unflatten_complex_params(input_dict, param_name):
        """Function to unflatten (portions of) dicts with complex keys.  The moto request parser flattens the incoming
        request bodies, which is generally helpful, but for nested dicts/lists can result in a hard-to-manage
        parameter exposion.  This function allows one to selectively unflatten a set of dict keys, replacing them
        with a deep dist/list structure named identically to the root component in the complex name.

        Complex keys are composed of multiple components
        separated by periods. Components may be prefixed with _, which is stripped.  Lists indexes are represented
        with two components, 'member' and the index number."""
        items_to_process = {}
        for k in input_dict.keys():
            if k.startswith(param_name):
                items_to_process[k] = input_dict[k]
        if len(items_to_process) == 0:
            return

        for k in items_to_process.keys():
            del input_dict[k]

        for k in items_to_process.keys():
            Unflattener._set_deep(k, input_dict, items_to_process[k])

    @staticmethod
    def _set_deep(complex_key, container, value):
        keys = complex_key.split(".")
        keys.reverse()

        while len(keys) > 0:
            if len(keys) == 1:
                key = keys.pop().strip("_")
                Unflattener._add_to_container(container, key, value)
            else:
                key = keys.pop().strip("_")
                if keys[-1] == "member":
                    keys.pop()
                    if not Unflattener._key_in_container(container, key):
                        container = Unflattener._add_to_container(container, key, [])
                    else:
                        container = Unflattener._get_child(container, key)
                else:
                    if not Unflattener._key_in_container(container, key):
                        container = Unflattener._add_to_container(container, key, {})
                    else:
                        container = Unflattener._get_child(container, key)

    @staticmethod
    def _add_to_container(container, key, value):
        if type(container) is dict:
            container[key] = value
        elif type(container) is list:
            i = int(key)
            while len(container) < i:
                container.append(None)
            container[i - 1] = value
        return value

    @staticmethod
    def _get_child(container, key):
        if type(container) is dict:
            return container[key]
        elif type(container) is list:
            i = int(key)
            return container[i - 1]

    @staticmethod
    def _key_in_container(container, key):
        if type(container) is dict:
            return key in container
        elif type(container) is list:
            i = int(key)
            return len(container) >= i


class CamelToUnderscoresWalker:
    """A class to convert the keys in dict/list hierarchical data structures from CamelCase to snake_case (underscores)"""

    @staticmethod
    def parse(x):
        if isinstance(x, dict):
            return CamelToUnderscoresWalker.parse_dict(x)
        elif isinstance(x, list):
            return CamelToUnderscoresWalker.parse_list(x)
        else:
            return CamelToUnderscoresWalker.parse_scalar(x)

    @staticmethod
    def parse_dict(x):
        temp = {}
        for key in x.keys():
            temp[camelcase_to_underscores(key)] = CamelToUnderscoresWalker.parse(x[key])
        return temp

    @staticmethod
    def parse_list(x):
        temp = []
        for i in x:
            temp.append(CamelToUnderscoresWalker.parse(i))
        return temp

    @staticmethod
    def parse_scalar(x):
        return x
