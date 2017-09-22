import boto
import boto3
from boto.ec2.cloudwatch.alarm import MetricAlarm
import sure  # noqa
import datetime

from moto import mock_cloudwatch_deprecated, mock_cloudwatch
from moto.core import BaseBackend, BaseModel
import moto.cloudwatch.models


def testdata_fixture():
    test_data = [
        {
            'MetricName': 'test_metric_1',
            'Dimensions': [
                {
                    'Name': 'test_dimension_1',
                    'Value': 'test_val_1'
                },
                {
                    'Name': 'test_dimension_2',
                    'Value': 'test_val_2'
                },
            ],
            'StatisticValues': {
                'SampleCount': 20,
                'Sum': 40,
                'Minimum': 60,
                'Maximum': 80
            },
            'Timestamp': datetime.datetime(2015, 1, 1),
            'Value': 20,
            'Unit': 'Seconds',
            'StorageResolution': 123,
        },
    ]
    return test_data


def testdata_fixture_nulltimestamp():
    test_data = [
        {
            'MetricName': 'test_metric_1',
            'Dimensions': [
                {
                    'Name': 'test_dimension_2',
                    'Value': 'test_val_2'
                },
            ],
            'Value': 20,
            'Unit': 'Seconds',
        },
    ]
    return test_data


@mock_cloudwatch
def test_metricdatumv2_namespace_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.Namespace == 'test_namespace'


@mock_cloudwatch
def test_metricdatumv2_metricname_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.MetricData[0].MetricName == 'test_metric_1'


@mock_cloudwatch
def test_metricdatumv2_dimensions_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)

    assert test_datum.MetricData[0].Dimensions[0].name == 'test_dimension_1'
    assert test_datum.MetricData[0].Dimensions[0].value == 'test_val_1'

    assert test_datum.MetricData[0].Dimensions[1].name == 'test_dimension_2'
    assert test_datum.MetricData[0].Dimensions[1].value == 'test_val_2'


@mock_cloudwatch
def test_metricdatumv2_timestamp_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.MetricData[0].Timestamp == datetime.datetime(2015, 1, 1)


@mock_cloudwatch
def test_metricdatumv2_null_timestamp_parse():
    test_data = testdata_fixture_nulltimestamp()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert hasattr(test_datum.MetricData[0], 'Timestamp') is False


@mock_cloudwatch
def test_metricdatumv2_value_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.MetricData[0].Value == 20


@mock_cloudwatch
def test_metricdatumv2_statistics_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)

    assert test_datum.MetricData[0].StatisticValues.SampleCount == 20
    assert test_datum.MetricData[0].StatisticValues.Sum == 40
    assert test_datum.MetricData[0].StatisticValues.Minimum == 60
    assert test_datum.MetricData[0].StatisticValues.Maximum == 80


@mock_cloudwatch
def test_metricdatumv2_resolution_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.MetricData[0].StorageResolution == 123


@mock_cloudwatch
def test_metricdatumv2_unit_parse():
    test_data = testdata_fixture()

    test_datum = moto.cloudwatch.models.MetricDatumv2(
        'test_namespace', test_data)
    assert test_datum.MetricData[0].Unit == 'Seconds'
