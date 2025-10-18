from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from moto.dynamodb.exceptions import MockValidationException, ResourceNotFoundException

if TYPE_CHECKING:
    from py_partiql_parser import QueryMetadata


def query(
    statement: str, source_data: Dict[str, list[Any]], parameters: List[Dict[str, Any]]
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]],
]:
    from py_partiql_parser import DynamoDBStatementParser
    from py_partiql_parser.exceptions import DocumentNotFoundException

    try:
        return DynamoDBStatementParser(source_data).parse(statement, parameters)
    except DocumentNotFoundException as dnfe:
        if "." in dnfe.name:
            table_name = dnfe.name.split(".")[0]
            if table_name in source_data:
                raise MockValidationException(
                    message="The table does not have the specified index"
                )
        raise ResourceNotFoundException()


def get_query_metadata(statement: str) -> "QueryMetadata":
    from py_partiql_parser import DynamoDBStatementParser

    return DynamoDBStatementParser.get_query_metadata(query=statement)
