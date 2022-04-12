import yaml
import sys


def print_test_names(service):
    with open("tests/terraformtests/terraform-tests.success.txt") as f:
        dct = yaml.load(f, Loader=yaml.FullLoader)
        x = dct.get(service)
        print(" ".join(x))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("")
    else:
        print_test_names(service=sys.argv[1])
