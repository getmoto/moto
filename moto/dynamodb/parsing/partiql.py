from typing import Any, Dict, List


def query(
    statement: str, source_data: Dict[str, str], parameters: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from py_partiql_parser import DynamoDBStatementParser

    return DynamoDBStatementParser(source_data).parse(statement, parameters)


def get_query_metadata(statement: str) -> Any:
    from py_partiql_parser import DynamoDBStatementParser

    return DynamoDBStatementParser.get_query_metadata(query=statement)
