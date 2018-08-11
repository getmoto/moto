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
    client = boto3.client("ec2", region_name="us-west-1")

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
        client.describe_reserved_instances_offerings(ReservedInstancesOfferingIds=["36239c57-8a19-48ca-ad88-f2399942b1"])

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

    reserved_instance = client.purchase_reserved_instances_offering(ReservedInstanceOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)

    len(reserved_instance["ReservedInstancesId"]).should.equal(36)


@mock_ec2
def test_purchase_invalid_reserved_instance_id():
    client = boto3.client("ec2", region_name="eu-central-1")
    
    with assert_raises(ClientError) as err:
        client.purchase_reserved_instances_offering(ReservedInstanceOfferingId="9818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidReservedInstancesOfferingId")


@mock_ec2
def test_purchase_invalid_reserved_instance_in_wrong_region():
    client = boto3.client("ec2", region_name="us-east-1")
    
    with assert_raises(ClientError) as err:
        client.purchase_reserved_instances_offering(ReservedInstanceOfferingId="3818be01-41a1-4ed2-8f2c-75cbd0abf7cc", InstanceCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidReservedInstancesOfferingId")
