import six

from moto.dynamodb2.comparisons import get_comparison_func
from moto.dynamodb2.exceptions import InvalidUpdateExpression
from moto.dynamodb2.models.utilities import attribute_is_list, bytesize


class DynamoType(object):
    """
    http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataModel.html#DataModelDataTypes
    """

    def __init__(self, type_as_dict):
        if type(type_as_dict) == DynamoType:
            self.type = type_as_dict.type
            self.value = type_as_dict.value
        else:
            self.type = list(type_as_dict)[0]
            self.value = list(type_as_dict.values())[0]
        if self.is_list():
            self.value = [DynamoType(val) for val in self.value]
        elif self.is_map():
            self.value = dict((k, DynamoType(v)) for k, v in self.value.items())

    def get(self, key):
        if not key:
            return self
        else:
            key_head = key.split(".")[0]
            key_tail = ".".join(key.split(".")[1:])
            if key_head not in self.value:
                self.value[key_head] = DynamoType({"NONE": None})
            return self.value[key_head].get(key_tail)

    def set(self, key, new_value, index=None):
        if index:
            index = int(index)
            if type(self.value) is not list:
                raise InvalidUpdateExpression
            if index >= len(self.value):
                self.value.append(new_value)
            # {'L': [DynamoType, ..]} ==> DynamoType.set()
            self.value[min(index, len(self.value) - 1)].set(key, new_value)
        else:
            attr = (key or "").split(".").pop(0)
            attr, list_index = attribute_is_list(attr)
            if not key:
                # {'S': value} ==> {'S': new_value}
                self.type = new_value.type
                self.value = new_value.value
            else:
                if attr not in self.value:  # nonexistingattribute
                    type_of_new_attr = "M" if "." in key else new_value.type
                    self.value[attr] = DynamoType({type_of_new_attr: {}})
                # {'M': {'foo': DynamoType}} ==> DynamoType.set(new_value)
                self.value[attr].set(
                    ".".join(key.split(".")[1:]), new_value, list_index
                )

    def delete(self, key, index=None):
        if index:
            if not key:
                if int(index) < len(self.value):
                    del self.value[int(index)]
            elif "." in key:
                self.value[int(index)].delete(".".join(key.split(".")[1:]))
            else:
                self.value[int(index)].delete(key)
        else:
            attr = key.split(".")[0]
            attr, list_index = attribute_is_list(attr)

            if list_index:
                self.value[attr].delete(".".join(key.split(".")[1:]), list_index)
            elif "." in key:
                self.value[attr].delete(".".join(key.split(".")[1:]))
            else:
                self.value.pop(key)

    def filter(self, projection_expressions):
        nested_projections = [
            expr[0 : expr.index(".")] for expr in projection_expressions if "." in expr
        ]
        if self.is_map():
            expressions_to_delete = []
            for attr in self.value:
                if (
                    attr not in projection_expressions
                    and attr not in nested_projections
                ):
                    expressions_to_delete.append(attr)
                elif attr in nested_projections:
                    relevant_expressions = [
                        expr[len(attr + ".") :]
                        for expr in projection_expressions
                        if expr.startswith(attr + ".")
                    ]
                    self.value[attr].filter(relevant_expressions)
            for expr in expressions_to_delete:
                self.value.pop(expr)

    def __hash__(self):
        return hash((self.type, self.value))

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value

    def __ne__(self, other):
        return self.type != other.type or self.value != other.value

    def __lt__(self, other):
        return self.cast_value < other.cast_value

    def __le__(self, other):
        return self.cast_value <= other.cast_value

    def __gt__(self, other):
        return self.cast_value > other.cast_value

    def __ge__(self, other):
        return self.cast_value >= other.cast_value

    def __repr__(self):
        return "DynamoType: {0}".format(self.to_json())

    @property
    def cast_value(self):
        if self.is_number():
            try:
                return int(self.value)
            except ValueError:
                return float(self.value)
        elif self.is_set():
            sub_type = self.type[0]
            return set([DynamoType({sub_type: v}).cast_value for v in self.value])
        elif self.is_list():
            return [DynamoType(v).cast_value for v in self.value]
        elif self.is_map():
            return dict([(k, DynamoType(v).cast_value) for k, v in self.value.items()])
        else:
            return self.value

    def child_attr(self, key):
        """
        Get Map or List children by key. str for Map, int for List.

        Returns DynamoType or None.
        """
        if isinstance(key, six.string_types) and self.is_map():
            if "." in key and key.split(".")[0] in self.value:
                return self.value[key.split(".")[0]].child_attr(
                    ".".join(key.split(".")[1:])
                )
            elif "." not in key and key in self.value:
                return DynamoType(self.value[key])

        if isinstance(key, int) and self.is_list():
            idx = key
            if 0 <= idx < len(self.value):
                return DynamoType(self.value[idx])

        return None

    def size(self):
        if self.is_number():
            value_size = len(str(self.value))
        elif self.is_set():
            sub_type = self.type[0]
            value_size = sum([DynamoType({sub_type: v}).size() for v in self.value])
        elif self.is_list():
            value_size = sum([v.size() for v in self.value])
        elif self.is_map():
            value_size = sum(
                [bytesize(k) + DynamoType(v).size() for k, v in self.value.items()]
            )
        elif type(self.value) == bool:
            value_size = 1
        else:
            value_size = bytesize(self.value)
        return value_size

    def to_json(self):
        return {self.type: self.value}

    def compare(self, range_comparison, range_objs):
        """
        Compares this type against comparison filters
        """
        range_values = [obj.cast_value for obj in range_objs]
        comparison_func = get_comparison_func(range_comparison)
        return comparison_func(self.cast_value, *range_values)

    def is_number(self):
        return self.type == "N"

    def is_set(self):
        return self.type == "SS" or self.type == "NS" or self.type == "BS"

    def is_list(self):
        return self.type == "L"

    def is_map(self):
        return self.type == "M"

    def same_type(self, other):
        return self.type == other.type
