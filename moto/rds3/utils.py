from __future__ import unicode_literals

import json

import boto3
from pkg_resources import resource_filename

from .parsers import CloudFormationPropertiesParser, QueryStringParametersParser


metadata = json.load(open(resource_filename(__name__, "resources/metadata.json"), "r"))

VALID_DB_ENGINES = [e for e in metadata["db_engines"]]
VALID_DB_CLUSTER_ENGINES = [e for e in metadata["db_engines"] if e.startswith("aurora")]
VALID_DB_INSTANCE_ENGINES = [e for e in metadata["db_engines"]]

db_engine_data = metadata["db_engine_data"]
db_engine_defaults = metadata["db_engine_defaults"]
default_db_cluster_parameter_groups = metadata["default_db_cluster_parameter_groups"]
default_db_parameter_groups = metadata["default_db_parameter_groups"]
default_option_groups = metadata["default_option_groups"]
option_group_options = metadata["option_group_options"]


def create_backends(service, backend_cls):
    session = boto3.session.Session()
    backends = {}
    partitions = session.get_available_partitions()
    for partition in partitions:
        regions = session.get_available_regions(service, partition_name=partition)
        for region in regions:
            # TODO: Partition should be part of the backend
            # Or we should just create the client and pass that in...
            # Then the backend can just proxy stuff like getting the
            # region or partition to the client
            # and we'd have access to the operation model and all that
            backends[region] = backend_cls(region)
    return backends


def parse_cf_properties(operation, properties):
    # TODO: This should just be a method on the parser, no?
    client = boto3.client("rds", region_name="us-east-1")
    operation_model = client.meta.service_model.operation_model(operation)
    deserializer = CloudFormationPropertiesParser()
    deserialized = deserializer.parse(properties, operation_model.input_shape)
    return deserialized


def parse_query_parameters(operation, query_parameters):
    # TODO: This should just be a method on the parser, no?
    client = boto3.client("rds", region_name="us-east-1")
    operation_model = client.meta.service_model.operation_model(operation)
    parser = QueryStringParametersParser()
    parsed = parser.parse(query_parameters, operation_model.input_shape)
    return parsed


def valid_engine_versions(engine_name):
    return [
        engine["EngineVersion"]
        for engine in db_engine_data
        if engine["Engine"] == engine_name
    ]


def valid_major_engine_versions(engine_name):
    # FIXME: This doesn't work for anything other than version like 9.6.1 or 5.7.2
    return set(
        [
            engine["EngineVersion"][:3]
            for engine in db_engine_data
            if engine["Engine"] == engine_name
        ]
    )


def default_engine_version(engine_name):
    defaults = get_engine_defaults(engine_name)
    return defaults["EngineVersion"]


def default_engine_port(engine_name):
    # TODO: Move this to metadata
    # Have this be a lookup table and in metadata actually have all the engines listed...
    # We could add 'Port' to the Engine defaults metadata.
    default_engine_ports = {
        "aurora": 3306,
        "aurora-postgresql": 5432,
        "mariadb": 3306,
        "mysql": 3306,
        "oracle": 1521,
        "postgres": 5432,
        "sqlserver": 1433,
    }
    default_port = default_engine_ports.get(engine_name)
    if default_port is None:
        for engine in default_engine_ports:
            if engine_name.startswith(engine):
                default_port = default_engine_ports[engine]
    return default_port or "123"


def default_option_group_name(engine_name, engine_version):
    try:
        option_group = next(
            og
            for og in default_option_groups
            if og["EngineName"] == engine_name
            and og["MajorEngineVersion"]
            == engine_version[: len(og["MajorEngineVersion"])]
        )
    except StopIteration:
        option_group = {
            "OptionGroupName": "default:{}-{}".format(
                engine_name, engine_version.replace(".", "-")
            )
        }
    return option_group["OptionGroupName"]


def default_db_cluster_parameter_group_name(engine_name):
    defaults = get_engine_defaults(engine_name)
    param_group_family = defaults["DBParameterGroupFamily"]
    param_group = next(
        item
        for item in default_db_cluster_parameter_groups
        if item["DBParameterGroupFamily"] == param_group_family
    )
    return param_group["DBClusterParameterGroupName"]


def default_db_parameter_group_name(engine_name, engine_version):
    parameter_group_name = None
    for i in range(len(engine_version), 1, -1):
        try:
            param_group = next(
                item
                for item in default_db_parameter_groups
                if str(item["DBParameterGroupFamily"]).startswith(engine_name)
                and str(item["DBParameterGroupFamily"]).endswith(engine_version[0:i])
            )
            parameter_group_name = param_group["DBParameterGroupName"]
        except StopIteration:
            pass
    return parameter_group_name or "default.{}".format(engine_version)


def get_engine_defaults(engine_name):
    defaults = next(
        item for item in db_engine_defaults if item["Engine"] == engine_name
    )
    return defaults
