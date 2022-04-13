import yaml

with open("tests/terraformtests/terraform-tests.success.txt") as f:
    dct = yaml.load(f, Loader=yaml.FullLoader)
    print(list(dct.keys()))
