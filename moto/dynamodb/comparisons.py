COMPARISON_FUNCS = {
    'EQ': lambda item_value, test_value: item_value == test_value,
    'GT': lambda item_value, test_value: item_value > test_value
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)

# class EQ(ConditionOneArg):

#     pass


# class NE(ConditionOneArg):

#     pass


# class LE(ConditionOneArg):

#     pass


# class LT(ConditionOneArg):

#     pass


# class GE(ConditionOneArg):

#     pass


# class GT(ConditionOneArg):

#     pass


# class NULL(ConditionNoArgs):

#     pass


# class NOT_NULL(ConditionNoArgs):

#     pass


# class CONTAINS(ConditionOneArg):

#     pass


# class NOT_CONTAINS(ConditionOneArg):

#     pass


# class BEGINS_WITH(ConditionOneArg):

#     pass


# class IN(ConditionOneArg):

#     pass


# class BEGINS_WITH(ConditionOneArg):

#     pass

# class BETWEEN(ConditionTwoArgs):

#     pass
