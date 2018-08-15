from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import base64
import datetime
import ipaddress

import six
import boto
import boto3
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError, EC2ResponseError
from botocore.exceptions import ClientError
from freezegun import freeze_time
import sure  # noqa
from numpy import isin

from moto import mock_ec2
from tests.helpers import requires_boto_gte


@mock_ec2
def test_reserved_instances_invalid_instance_type():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid instance type
    instance_type_test = "m5.xxlarge"

    with assert_raises(ClientError) as err:
            client.describe_reserved_instances_offerings(InstanceType=instance_type_test, ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_invalid_instance_type_invalid_family_format():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid instance type
    instance_type_test = "m5.xx.large"

    with assert_raises(ClientError) as err:
            client.describe_reserved_instances_offerings(InstanceType=instance_type_test, ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_invalid_instance_type_not_on_hash_table():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid instance type
    instance_type_test = "t6P.nano"

    with assert_raises(ClientError) as err:
            client.describe_reserved_instances_offerings(InstanceType=instance_type_test, ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")



@mock_ec2
def test_reserved_instances_valid_instance_type():
    client = boto3.client("ec2", region_name="us-east-2")

    instance_type_test = "m5.xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=instance_type_test, ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(instance_type_test)

@mock_ec2
def test_reserved_instances_invalid_offering_class():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because standard and convertible are the only options
    offering_class_test = "All Upfront"

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass=offering_class_test,
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")

@mock_ec2
def test_reserved_instances_valid_offering_class():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because standard and convertible are the only options
    offering_class_test = "standard"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass=offering_class_test,
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["OfferingClass"].should.equal(offering_class_test)


@mock_ec2
def test_reserved_instances_valid_offering_class_convertible():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because standard and convertible are the only options
    offering_class_test = "convertible"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass=offering_class_test,
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["OfferingClass"].should.equal(offering_class_test)


@mock_ec2
def test_reserved_instances_valid_offering_class_convertible():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because standard and convertible are the only options
    offering_class_test = "convertible"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass=offering_class_test,
                    OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["OfferingClass"].should.equal(offering_class_test)


@mock_ec2
def test_reserved_instances_invalid_offering_type():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because all,partial, no upfront are the only options
    offering_type_test = "standard"

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType=offering_type_test, MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_valid_offering_type():
    client = boto3.client("ec2", region_name="us-east-2")

    offering_type_test = "All Upfront"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType=offering_type_test, MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["OfferingType"].should.equal(offering_type_test)


@mock_ec2
def test_reserved_instances_invalid_instance_tenancy():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because there is a different api call for host ri offerings
    instance_tenancy_test = "host"

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy=instance_tenancy_test, OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_valid_instance_tenancy():
    client = boto3.client("ec2", region_name="us-east-2")

    instance_tenancy_test = "default"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy=instance_tenancy_test, OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["InstanceTenancy"].should.equal(instance_tenancy_test)


@mock_ec2
def test_reserved_instances_invalid_max_duration():
    client = boto3.client("ec2", region_name="us-east-2")

    # invalid because 1 year and 3 years are only options
    max_duration_test = 12345678

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=max_duration_test, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_valid_max_duration():
    client = boto3.client("ec2", region_name="us-east-2")

    max_duration_test = 94608000

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=max_duration_test, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["Duration"].should.equal(max_duration_test)


@mock_ec2
def test_reserved_instances_invalid_product_description():
    client = boto3.client("ec2", region_name="us-east-2")

    # without sql server is invalid
    test_product_description = "Windows without SQL Server Web"

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_valid_product_description():
    client = boto3.client("ec2", region_name="us-east-2")

    test_product_description = "Windows with SQL Server Web"

    offerings = client.describe_reserved_instances_offerings(InstanceType="m5.large", ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)


@mock_ec2
def test_reserved_instances_valid_product_description_un_specified():
    client = boto3.client("ec2", region_name="us-east-2")

    offerings = client.describe_reserved_instances_offerings(InstanceType="m5.large",
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    pd = offerings["ReservedInstancesOfferings"][0]["ProductDescription"]
    test_true = pd in ["Linux/UNIX", "SUSE Linux", "Red Hat Enterprise Linux",
        "Windows", "Windows with SQL Server Standard", "Windows with SQL Server Web",
        "Windows with SQL Server Enterprise", "Windows BYOL", "Linux with SQL Server Web",
        "Linux with SQL Server Standard", "Linux with SQL Server Enterprise"]
    test_true.should.equal(True)


@mock_ec2
def test_reserved_instances_valid_product_description_sql_server():
    client = boto3.client("ec2", region_name="ap-south-1")

    test_product_description = "Windows with SQL Server Enterprise"
    test_instance_type = "r4.8xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_valid_product_description_red_hat_linux():
    client = boto3.client("ec2", region_name="ap-south-1")

    test_product_description = "Red Hat Enterprise Linux"
    test_instance_type = "r4.4xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_valid_product_description_linux_with_sql_server():
    client = boto3.client("ec2", region_name="ap-south-1")

    test_product_description = "Linux with SQL Server Enterprise"
    test_instance_type = "r4.4xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_valid_product_description_windows_byol():
    client = boto3.client("ec2", region_name="eu-west-1")

    test_product_description = "Windows BYOL"
    test_instance_type = "t2.nano"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_valid_product_description_suse_linux():
    client = boto3.client("ec2", region_name="eu-west-1")

    test_product_description = "SUSE Linux"
    test_instance_type = "x1.16xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_valid_product_description_linux():
    client = boto3.client("ec2", region_name="eu-central-1")

    test_product_description = "Linux/UNIX"
    test_instance_type = "c5.4xlarge"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard", OfferingType="All Upfront")

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_reserved_instances_number_of_offerings():
    client = boto3.client("ec2", region_name="us-east-2")

    offerings = client.describe_reserved_instances_offerings(InstanceType="m5.large", ProductDescription="Windows",
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])

    # You can purchase reserved instances in two availability zones out of 3 plus an additional regional one.
    # This could change if they increase the number of availability zones in Ohio
    number_of_offerings.should.equal(3)


@mock_ec2
def test_reserved_instances_no_offering_available():
    client = boto3.client("ec2", region_name="us-east-2")

    offerings = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Red Hat Enterprise Linux",
        InstanceTenancy="dedicated", OfferingClass="standard",
        OfferingType="Partial Upfront", MaxDuration=94608000, MinDuration=94608000)

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])

    # Currently AWS does not offer reserved instances with these criteria, so it should return an empty set.

    number_of_offerings.should.equal(0)


@mock_ec2
def test_reserved_instances_invalid_ri_offering():
    client = boto3.client("ec2", region_name="us-east-1")

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=["3239c57-8a19-48ca-ad88-f2399942b1"])

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_no_offering_for_id():
    client = boto3.client("ec2", region_name="us-east-1")

    offerings = client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=["00000000-8a19-48ca-ad88-f2399942b18f"])

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])

    number_of_offerings.should.equal(0)


@mock_ec2
def test_reserved_instances_valid_offering_id():
    client = boto3.client("ec2", region_name="eu-central-1")

    offering_id = "efa1c780-e056-48c1-97c3-7bd90d3686c2"

    offerings = client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=[offering_id])

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])

    number_of_offerings.should.equal(1)

    offerings["ReservedInstancesOfferings"][0]["Duration"].should.equal(94608000)
    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal("Windows with SQL Server Standard")
    offerings["ReservedInstancesOfferings"][0]["InstanceTenancy"].should.equal("default")
    offerings["ReservedInstancesOfferings"][0]["OfferingClass"].should.equal("standard")
    offerings["ReservedInstancesOfferings"][0]["OfferingType"].should.equal("All Upfront")
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal("m4.large")
    offerings["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"].should.equal(offering_id)


@mock_ec2
def test_reserved_instances_offering_special_instance_type():
    client = boto3.client("ec2", region_name="us-east-1")
    test_product_description = "Linux/UNIX"
    test_instance_type = "c5d.large"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    offerings["ReservedInstancesOfferings"][0]["ProductDescription"].should.equal(test_product_description)
    offerings["ReservedInstancesOfferings"][0]["InstanceType"].should.equal(test_instance_type)


@mock_ec2
def test_multiple_ri_offerings():
    client = boto3.client("ec2", region_name="ca-central-1")
    test_offering_ids = ["37090450-1f56-45cc-8d8a-c06ec2f2b11f", "10f99c79-bf18-43ec-be00-4eca1a83f8cf"]

    offerings = client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=test_offering_ids)

    len(offerings["ReservedInstancesOfferings"]).should.equal(2)
    for offering in offerings["ReservedInstancesOfferings"]:
        if offering["ReservedInstancesOfferingId"] == "10f99c79-bf18-43ec-be00-4eca1a83f8cf":
            offering["InstanceType"].should.equal("c5d.2xlarge")
        if offering["ReservedInstancesOfferingId"] == "37090450-1f56-45cc-8d8a-c06ec2f2b11f":
            offering["InstanceType"].should.equal("d2.4xlarge")


@mock_ec2
def test_multiple_tenancies():
    client = boto3.client("ec2", region_name="ap-south-1")

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows with SQL Server Standard", OfferingClass="standard", OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)
    # without tenancy specified there are 6 possibilities (1 region + 2 availability zone)*2 = 6
    len(offerings["ReservedInstancesOfferings"]).should.equal(6)


@mock_ec2
def test_multiple_offering_classes():
    client = boto3.client("ec2", region_name="ap-south-1")

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows with SQL Server Standard", InstanceTenancy="dedicated", OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)
    # without offering class there are 6 possibilities (1 region + 2 az)*2 = 6. only standard and convertible
    len(offerings["ReservedInstancesOfferings"]).should.equal(6)


@mock_ec2
def test_multiple_offering_types():
    client = boto3.client("ec2", region_name="ap-south-1")

    offerings = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows with SQL Server Standard", InstanceTenancy="dedicated", OfferingClass="standard", MaxDuration=94608000, MinDuration=94608000)

    len(offerings["ReservedInstancesOfferings"]).should.equal(9)


@mock_ec2
def test_max_duration_less_than_min_duration():
    client = boto3.client("ec2", region_name="ap-south-1")

    # invalid because max duration is less than min duration
    test_max_duration = 31536000
    test_min_duration = 94608000

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=test_max_duration, MinDuration=test_min_duration)
    # I think technically AWS will allow this and just return [], but that is a pain to get exact
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_invalid_min_duration():
    client = boto3.client("ec2", region_name="ap-south-1")

    # invalid because max duration is less than min duration
    test_min_duration = 54608000

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    InstanceTenancy="dedicated", OfferingClass="standard",
                    OfferingType="All Upfront", MinDuration=test_min_duration)

    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_reserved_instances_no_instance_type_in_region():
    client = boto3.client("ec2", region_name="eu-central-1")

    test_product_description = "Linux/UNIX"
    test_instance_type = "c5d.large"

    offerings = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description,
                    InstanceTenancy="default", OfferingClass="standard",
                    OfferingType="All Upfront", MaxDuration=94608000, MinDuration=94608000)

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])
    number_of_offerings.should.equal(0)


@mock_ec2
def test_reserved_instance_offering_id_invalid_region():
    client = boto3.client("ec2", region_name="us-east-1")

    offerings = client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=["3818be01-41a1-4ed2-8f2c-75cbd0abf7cc"])

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])
    number_of_offerings.should.equal(0)


@mock_ec2
def test_reserved_instance_offering_id_valid_region():
    client = boto3.client("ec2", region_name="eu-central-1")

    offerings = client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=["3818be01-41a1-4ed2-8f2c-75cbd0abf7cc"])

    number_of_offerings = len(offerings["ReservedInstancesOfferings"])
    number_of_offerings.should.equal(1)


@mock_ec2
def test_purchase_reserved_instances():
    client = boto3.client("ec2", region_name="eu-central-1")

    reserved_instance = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)

    len(reserved_instance["ReservedInstancesId"]).should.equal(36)


@mock_ec2
def test_purchase_invalid_reserved_instance_id():
    client = boto3.client("ec2", region_name="eu-central-1")
    
    with assert_raises(ClientError) as err:
        client.purchase_reserved_instances_offering(ReservedInstancesOfferingId="9818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidReservedInstancesOfferingId")


@mock_ec2
def test_purchase_invalid_reserved_instance_in_wrong_region():
    client = boto3.client("ec2", region_name="us-east-1")
    
    with assert_raises(ClientError) as err:
        client.purchase_reserved_instances_offering(ReservedInstancesOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidReservedInstancesOfferingId")


@mock_ec2
def test_describe_reserved_instance():
    client = boto3.client("ec2", region_name="eu-central-1")

    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)

    reserved_instance = client.describe_reserved_instances()

    len(reserved_instance["ReservedInstances"]).should.equal(1)
    reserved_instance["ReservedInstances"][0]["InstanceCount"].should.equal(1)


@mock_ec2
def test_describe_reserved_instance_multiple_instane_count():
    client = boto3.client("ec2", region_name="eu-central-1")

    test_instance_count = 5

    purchase_ri = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=test_instance_count)
    ri_id = purchase_ri["ReservedInstancesId"]

    reserved_instance = client.describe_reserved_instances()

    len(reserved_instance["ReservedInstances"]).should.equal(1)
    reserved_instance["ReservedInstances"][0]["InstanceCount"].should.equal(test_instance_count)
    reserved_instance["ReservedInstances"][0]["ReservedInstancesId"].should.equal(ri_id)


@mock_ec2
def test_describe_reserved_instance_multiple_reserved_instances():
    client = boto3.client("ec2", region_name="us-west-2")

    offering1 = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Windows",
                    OfferingType="All Upfront", OfferingClass="standard", InstanceTenancy="default")
    
    offering2 = client.describe_reserved_instances_offerings(InstanceType="m4.large", ProductDescription="Windows",
                    OfferingType="No Upfront", OfferingClass="convertible", InstanceTenancy="dedicated")
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering1["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering2["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances = client.describe_reserved_instances()

    len(reserved_instances["ReservedInstances"]).should.equal(2)
    reserved_instances["ReservedInstances"][0]["ProductDescription"].should.equal("Windows")


@mock_ec2
def test_describe_reserved_instance_instance_attributes():
    client = boto3.client("ec2", region_name="us-east-2")

    test_instance_type = "r4.4xlarge"
    test_product_description = "Red Hat Enterprise Linux"
    test_instance_tenancy = "default"


    offering = client.describe_reserved_instances_offerings(InstanceType=test_instance_type, ProductDescription=test_product_description, InstanceTenancy=test_instance_tenancy)

    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances = client.describe_reserved_instances()

    reserved_instances["ReservedInstances"][0]["InstanceType"].should.equal(test_instance_type)
    reserved_instances["ReservedInstances"][0]["ProductDescription"].should.equal(test_product_description)
    reserved_instances["ReservedInstances"][0]["InstanceTenancy"].should.equal(test_instance_tenancy)


@mock_ec2
def test_describe_reserved_instance_offering_options():
    client = boto3.client("ec2", region_name="eu-west-1")

    test_offering_class = "standard"
    test_offering_type = "No Upfront"

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass=test_offering_class, OfferingType=test_offering_type)

    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances = client.describe_reserved_instances()

    reserved_instances["ReservedInstances"][0]["OfferingClass"].should.equal(test_offering_class)
    reserved_instances["ReservedInstances"][0]["OfferingType"].should.equal(test_offering_type)


@mock_ec2
def test_describe_reserved_instances_start_and_end_time_one_year():
    client = boto3.client("ec2", region_name="ap-northeast-1")

    offering1 = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)

    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering1["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances = client.describe_reserved_instances()

    current_time = datetime.datetime.utcnow()

    reserved_instances["ReservedInstances"][0]["Start"].year.should.equal(current_time.year)
    reserved_instances["ReservedInstances"][0]["Start"].month.should.equal(current_time.month)
    reserved_instances["ReservedInstances"][0]["Start"].day.should.equal(current_time.day)
    reserved_instances["ReservedInstances"][0]["End"].year.should.equal(current_time.year+1)
    reserved_instances["ReservedInstances"][0]["End"].month.should.equal(current_time.month)


@mock_ec2
def test_describe_reserved_instances_start_and_end_time_three_years():
    client = boto3.client("ec2", region_name="ap-northeast-1")

    offering2 = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=94608000, MinDuration=94608000)

    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering2["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances = client.describe_reserved_instances()

    current_time = datetime.datetime.utcnow()

    reserved_instances["ReservedInstances"][0]["Start"].year.should.equal(current_time.year)
    reserved_instances["ReservedInstances"][0]["Start"].month.should.equal(current_time.month)
    reserved_instances["ReservedInstances"][0]["Start"].day.should.equal(current_time.day)
    reserved_instances["ReservedInstances"][0]["End"].year.should.equal(current_time.year+3)
    reserved_instances["ReservedInstances"][0]["End"].month.should.equal(current_time.month)


@mock_ec2
def test_describe_reserved_instance_variable_offering_class():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(OfferingClass="standard")
    reserved_instances3 = client.describe_reserved_instances(OfferingClass="convertible")

    len(reserved_instances1["ReservedInstances"]).should.equal(1)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(0)


@mock_ec2
def test_describe_reserved_instance_variable_offering_type():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(OfferingType="No Upfront")
    reserved_instances3 = client.describe_reserved_instances(OfferingType="All Upfront")

    len(reserved_instances1["ReservedInstances"]).should.equal(1)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(0)


@mock_ec2
def test_describe_reserved_instance_variable_offering_class_and_type():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(OfferingClass="standard", OfferingType="No Upfront")
    reserved_instances3 = client.describe_reserved_instances(OfferingClass="standard", OfferingType="All Upfront")
    reserved_instances4 = client.describe_reserved_instances(OfferingClass="convertible", OfferingType="No Upfront")
    reserved_instances5 = client.describe_reserved_instances(OfferingClass="convertible", OfferingType="All Upfront")

    len(reserved_instances1["ReservedInstances"]).should.equal(1)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(0)
    len(reserved_instances4["ReservedInstances"]).should.equal(0)
    len(reserved_instances5["ReservedInstances"]).should.equal(0)


@mock_ec2
def test_describe_reserved_instance_invalid_offering_class():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances(OfferingClass="standarddd")
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_describe_reserved_instance_invalid_offering_type():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances(OfferingType="Alll Upfront")
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_describe_reserved_instance_invalid_reserved_instance_id():
    client = boto3.client("ec2", region_name="eu-west-1")

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass="standard", OfferingType="No Upfront", MaxDuration=31536000, MinDuration=31536000)
    
    client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    with assert_raises(ClientError) as err:
        client.describe_reserved_instances(ReservedInstancesIds=["0000000000000"])
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_describe_reserved_instance_variable_offering_class_and_type_and_ri_id():
    client = boto3.client("ec2", region_name="eu-west-1")

    real_offering_type = "No Upfront"
    fake_offering_type = "All Upfront"

    real_offering_class = "standard"
    fake_offering_class = "convertible"

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass=real_offering_class, OfferingType=real_offering_type, MaxDuration=31536000, MinDuration=31536000)
    
    purchase_ri = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    real_ri_id = purchase_ri["ReservedInstancesId"]
    fake_ri_id = "f3506846-a02e-41bd-b113-4b39fb943127"

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(OfferingClass=real_offering_class, OfferingType=real_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances3 = client.describe_reserved_instances(OfferingClass=real_offering_class, OfferingType=real_offering_type, ReservedInstancesIds=[fake_ri_id])
    reserved_instances4 = client.describe_reserved_instances(OfferingClass=real_offering_class, OfferingType=fake_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances5 = client.describe_reserved_instances(OfferingClass=real_offering_class, OfferingType=fake_offering_type, ReservedInstancesIds=[fake_ri_id])
    reserved_instances6 = client.describe_reserved_instances(OfferingClass=fake_offering_class, OfferingType=real_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances7 = client.describe_reserved_instances(OfferingClass=fake_offering_class, OfferingType=real_offering_type, ReservedInstancesIds=[fake_ri_id])
    reserved_instances8 = client.describe_reserved_instances(OfferingClass=fake_offering_class, OfferingType=fake_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances9 = client.describe_reserved_instances(OfferingClass=fake_offering_class, OfferingType=fake_offering_type, ReservedInstancesIds=[fake_ri_id])

    len(reserved_instances1["ReservedInstances"]).should.equal(1)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(0)
    len(reserved_instances4["ReservedInstances"]).should.equal(0)
    len(reserved_instances5["ReservedInstances"]).should.equal(0)
    len(reserved_instances6["ReservedInstances"]).should.equal(0)
    len(reserved_instances7["ReservedInstances"]).should.equal(0)
    len(reserved_instances8["ReservedInstances"]).should.equal(0)
    len(reserved_instances9["ReservedInstances"]).should.equal(0)
    reserved_instances1["ReservedInstances"][0]["ReservedInstancesId"].should.equal(real_ri_id)
    reserved_instances2["ReservedInstances"][0]["ReservedInstancesId"].should.equal(real_ri_id)


@mock_ec2
def test_describe_reserved_instance_variable_offering_class_and_type_and_ri_id2():
    client = boto3.client("ec2", region_name="eu-west-1")

    real_offering_type = "No Upfront"
    fake_offering_type = "All Upfront"

    real_offering_class = "standard"
    fake_offering_class = "convertible"

    offering = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Linux/UNIX", InstanceTenancy="default",
                            OfferingClass=real_offering_class, OfferingType=real_offering_type, MaxDuration=31536000, MinDuration=31536000)
    
    purchase_ri = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offering["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)

    real_ri_id = purchase_ri["ReservedInstancesId"]
    fake_ri_id = "f3506846-a02e-41bd-b113-4b39fb943127"

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(OfferingClass=real_offering_class, ReservedInstancesIds=[real_ri_id])
    reserved_instances3 = client.describe_reserved_instances(OfferingClass=real_offering_class, ReservedInstancesIds=[fake_ri_id])
    reserved_instances4 = client.describe_reserved_instances(OfferingClass=fake_offering_class, ReservedInstancesIds=[real_ri_id])
    reserved_instances5 = client.describe_reserved_instances(OfferingType=real_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances6 = client.describe_reserved_instances(OfferingType=real_offering_type, ReservedInstancesIds=[fake_ri_id])
    reserved_instances7 = client.describe_reserved_instances(OfferingType=fake_offering_type, ReservedInstancesIds=[real_ri_id])
    reserved_instances8 = client.describe_reserved_instances(OfferingType=fake_offering_type, ReservedInstancesIds=[fake_ri_id])

    len(reserved_instances1["ReservedInstances"]).should.equal(1)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(0)
    len(reserved_instances4["ReservedInstances"]).should.equal(0)
    len(reserved_instances5["ReservedInstances"]).should.equal(1)
    len(reserved_instances6["ReservedInstances"]).should.equal(0)
    len(reserved_instances7["ReservedInstances"]).should.equal(0)
    len(reserved_instances8["ReservedInstances"]).should.equal(0)
    reserved_instances1["ReservedInstances"][0]["ReservedInstancesId"].should.equal(real_ri_id)
    reserved_instances2["ReservedInstances"][0]["ReservedInstancesId"].should.equal(real_ri_id)
    reserved_instances5["ReservedInstances"][0]["ReservedInstancesId"].should.equal(real_ri_id)


@mock_ec2
def test_describe_reserved_instance_multiple_ris():
    client = boto3.client("ec2", region_name="eu-west-1")

    offerings1 = client.describe_reserved_instances_offerings(InstanceType="t2.nano", ProductDescription="Windows",
                        OfferingType="No Upfront", OfferingClass="standard", InstanceTenancy="default")

    offerings2 = client.describe_reserved_instances_offerings(InstanceType="c5.large", ProductDescription="Linux/UNIX",
                        OfferingType="Partial Upfront", OfferingClass="convertible", InstanceTenancy="default")

    purchase_ri1 = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offerings1["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=1)
    purchase_ri2 = client.purchase_reserved_instances_offering(ReservedInstancesOfferingId=offerings2["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"], InstanceCount=3)

    ri_id1 = purchase_ri1["ReservedInstancesId"]
    ri_id2 = purchase_ri2["ReservedInstancesId"]

    reserved_instances1 = client.describe_reserved_instances()
    reserved_instances2 = client.describe_reserved_instances(ReservedInstancesIds=[ri_id1])
    reserved_instances3 = client.describe_reserved_instances(ReservedInstancesIds=[ri_id2])
    reserved_instances4 = client.describe_reserved_instances(ReservedInstancesIds=[ri_id1, ri_id2])

    len(reserved_instances1["ReservedInstances"]).should.equal(2)
    len(reserved_instances2["ReservedInstances"]).should.equal(1)
    len(reserved_instances3["ReservedInstances"]).should.equal(1)
    len(reserved_instances4["ReservedInstances"]).should.equal(2)

    reserved_instances2["ReservedInstances"][0]["InstanceType"].should.equal("t2.nano")
    reserved_instances2["ReservedInstances"][0]["ProductDescription"].should.equal("Windows")
    reserved_instances3["ReservedInstances"][0]["InstanceType"].should.equal("c5.large")
    reserved_instances3["ReservedInstances"][0]["ProductDescription"].should.equal("Linux/UNIX")
