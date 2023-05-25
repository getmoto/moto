from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from py_partiql_parser import QueryMetadata


def query(
    statement: str, source_data: Dict[str, str], parameters: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from py_partiql_parser import DynamoDBStatementParser

    return DynamoDBStatementParser(source_data).parse(statement, parameters)


def get_query_metadata(statement: str) -> "QueryMetadata":
    from py_partiql_parser import DynamoDBStatementParser

    return DynamoDBStatementParser.get_query_metadata(query=statement)
