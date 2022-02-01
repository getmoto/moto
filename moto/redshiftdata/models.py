import re
import uuid
from datetime import datetime
import random

from moto.core import BaseBackend
from moto.core.utils import BackendDict, iso_8601_datetime_without_milliseconds
from moto.redshiftdata.exceptions import ValidationException, ResourceNotFoundException


class Statement:
    def __init__(
        self,
        cluster_identifier,
        database,
        db_user,
        query_parameters,
        query_string,
        secret_arn,
    ):
        now = iso_8601_datetime_without_milliseconds(datetime.now())

        self.Id = str(uuid.uuid4())
        self.ClusterIdentifier = cluster_identifier
        self.CreatedAt = now
        self.Database = database
        self.DbUser = db_user
        self.Duration = 0
        self.HasResultSet = False
        self.QueryParameters = query_parameters
        self.QueryString = query_string
        self.RedshiftPid = random.randint(0, 99999)
        self.RedshiftQueryId = random.randint(0, 99999)
        self.ResultRows = -1
        self.ResultSize = -1
        self.SecretArn = secret_arn
        self.Status = 'STARTED'
        self.SubStatements = []
        self.UpdatedAt = now


class StatementResult:
    def __init__(
        self,
        column_metadata,
        records,
        total_number_rows,
        next_token=None,
    ):
        self.ColumnMetadata = column_metadata
        self.Records = records
        self.NextToken = next_token
        self.TotalNumberRows = total_number_rows


class ColumnMetadata:
    def __init__(
        self,
        column_default,
        is_case_sensitive,
        is_signed,
        name,
        nullable
    ):
        self.columnDefault = column_default
        self.isCaseSensitive = is_case_sensitive
        self.isSigned = is_signed
        self.name = name
        self.nullable = nullable


class Record:
    def __init__(
        self,
        **kwargs,
    ):
        if "long_value" in kwargs:
            self.longValue = kwargs["long_value"]
        elif "string_value" in kwargs:
            self.stringValue = kwargs["string_value"]


class RedshiftDataAPIServiceBackend(BaseBackend):

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.statements = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def cancel_statement(self, statement_id):
        _validate_uuid(statement_id)

        try:
            # Statement exists
            statement = self.statements[statement_id]

            if statement.Status != "STARTED":
                raise ValidationException(
                    "Could not cancel a query that is already in %s state with ID: %s"
                    % (statement.Status, statement_id)
                )

            statement.Status = "ABORTED"
            self.statements[statement_id] = statement
        except KeyError:
            # Statement does not exist.
            raise ResourceNotFoundException()

        return True

    def describe_statement(self, statement_id):
        _validate_uuid(statement_id)

        try:
            # Statement exists
            return self.statements[statement_id]
        except KeyError:
            # Statement does not exist.
            raise ResourceNotFoundException()

    def execute_statement(
        self,
        cluster_identifier,
        database,
        db_user,
        parameters,
        secret_arn,
        sql,
    ):
        statement = Statement(
            cluster_identifier=cluster_identifier,
            database=database,
            db_user=db_user,
            query_parameters=parameters,
            query_string=sql,
            secret_arn=secret_arn
        )
        self.statements[statement.Id] = statement
        return statement

    def get_statement_result(self, statement_id):
        _validate_uuid(statement_id)

        if statement_id not in self.statements:
            raise ResourceNotFoundException()

        # Return static statement result
        # StatementResult cannot be mocked because it's the result of the SQL query passed as parameter
        return StatementResult(
            [
                vars(ColumnMetadata(None, False, True, "Number", False)),
                vars(ColumnMetadata(None, True, False, "Street", False)),
                vars(ColumnMetadata(None, True, False, "City", False)),
            ],
            [
                [
                    vars(Record(long_value=10)),
                    vars(Record(string_value="Alpha st")),
                    vars(Record(string_value="Vancouver"))
                ],
                [
                    vars(Record(long_value=50)),
                    vars(Record(string_value="Beta st")),
                    vars(Record(string_value="Toronto"))
                ],
                [
                    vars(Record(long_value=100)),
                    vars(Record(string_value="Gamma av")),
                    vars(Record(string_value="Seattle"))
                ]
            ],
            3,
        )


def _validate_uuid(uuid):
    match = re.search(r'^[a-z0-9]{8}(-[a-z0-9]{4}){3}-[a-z0-9]{12}(:\d+)?$', uuid)
    if not match:
        raise ValidationException("id must satisfy regex pattern: ^[a-z0-9]{8}(-[a-z0-9]{4}){3}-[a-z0-9]{12}(:\\d+)?$")


# For unknown reasons I cannot use the service name "redshift-data" as I should
# It seems boto3 is unable to get the list of available regions for "redshift-data"
# See code here https://github.com/spulec/moto/blob/master/moto/core/utils.py#L407
# sess.get_available_regions("redshift-data") returns an empty list
# Then I use the service redshift since they share the same regions
# See https://docs.aws.amazon.com/general/latest/gr/redshift-service.html
redshiftdata_backends = BackendDict(RedshiftDataAPIServiceBackend, "redshift")
