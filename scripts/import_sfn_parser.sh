#!/bin/bash

# Keep Moto-specific parts
mkdir tmp
mv moto/stepfunctions/parser/README.md tmp
mv moto/stepfunctions/parser/api.py tmp
mv moto/stepfunctions/parser/models.py tmp
mv moto/stepfunctions/parser/utils.py tmp
mv moto/stepfunctions/parser/asl/utils/boto_client.py tmp
mv moto/stepfunctions/parser/asl/component/state/exec/state_task/service/state_task_service_api_gateway.py tmp
mv moto/stepfunctions/parser/asl/component/state/exec/state_task/service/state_task_service_aws_sdk.py tmp
mv moto/stepfunctions/parser/asl/component/state/exec/state_task/lambda_eval_utils.py tmp
mv moto/stepfunctions/parser/backend/execution.py tmp

# Remove old implementation
rm -rf moto/stepfunctions/parser

# Copy implementation as is
cp -r ../../localstack/localstack/localstack-core/localstack/services/stepfunctions moto/stepfunctions/parser

# Remove parser/spec files that we don't need
rm -r moto/stepfunctions/parser/asl/antlr/.gitignore
rm -r moto/stepfunctions/parser/asl/antlr/Makefile

# Shorten paths, as they are too long for Windows implementations
mv moto/stepfunctions/parser/asl/component/state/state_choice moto/stepfunctions/parser/asl/component/state/choice
mv moto/stepfunctions/parser/asl/component/state/state_execution moto/stepfunctions/parser/asl/component/state/exec
mv moto/stepfunctions/parser/asl/component/state/state_fail moto/stepfunctions/parser/asl/component/state/fail
mv moto/stepfunctions/parser/asl/component/state/state_wait moto/stepfunctions/parser/asl/component/state/wait
mv moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/resource_eval moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval
mv moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/resource_output_transformer.py moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/transformer.py
mv moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/resource_output_transformer_csv.py moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/transformer_csv.py
mv moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/resource_output_transformer_factory.py moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/transformer_factory.py
mv moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/resource_output_transformer_json.py moto/stepfunctions/parser/asl/component/state/exec/state_map/item_reader/eval/resource_output_transformer/transformer_json.py

# Alter imports with shorter paths
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/state.state_execution/state.exec/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/state.state_choice/state.choice/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/state.state_fail/state.fail/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/state.state_wait/state.wait/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/item_reader.resource_eval.resource_eval/item_reader.eval.resource_eval/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/item_reader.resource_eval.resource_output_transformer/item_reader.eval.resource_output_transformer/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/eval.resource_output_transformer.resource_output_transformer/eval.resource_output_transformer.transformer/'

# Allow for Python 3.8
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/NotRequired/Optional/'
find moto/stepfunctions/parser -type f -name "*.py" | xargs sed -i 's/Union\[str, json\]/Any/'
find moto/stepfunctions/parser -type f -name "*.py" | xargs sed -i '1s/^/from typing import Any, List\n/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i  's/: list\[/: List\[/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i  's/\[list\[/\[List\[/'

# Remove custom LS logic
find moto/stepfunctions/parser/ -type f -name "*.py" | xargs sed -i 's/from localstack.utils.aws.arns/from moto.utilities.arns/'
find moto/stepfunctions/parser/ -type f -name "*.py" | xargs sed -i 's/from localstack.utils.objects/from moto.stepfunctions.parser.utils/'
find moto/stepfunctions/parser/ -type f -name "*.py" | xargs sed -i 's/from localstack.utils.strings/from moto.stepfunctions.parser.utils/'
find moto/stepfunctions/parser/ -type f -name "*.py" | xargs sed -i 's/from localstack.utils.common/from moto.stepfunctions.parser.utils/'
find moto/stepfunctions/parser/ -type f -name "*.py" | xargs sed -i 's/from localstack.utils.threads/from moto.stepfunctions.parser.utils/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/ArnData,//'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/: ArnData//'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/arn_data["region"]/arn_data.region/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/arn_data["region"]/arn_data.region/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/arn_data.get("region")/arn_data.region/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/arn_data.get("account")/arn_data.account/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/arn_data.get("resource")/arn_data.resource_id/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/except InvalidArnException/except IndexError/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/List\[InputLogEvent\]/List\[Any\]/'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/from localstack.aws.api.logs import InputLogEvent//'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/from localstack.aws.connect import connect_to//'

find moto/stepfunctions/parser/asl/component/state/exec/state_task -type f -name "*.py" | xargs sed -i 's/InvocationType.RequestResponse/"RequestResponse"/'
find moto/stepfunctions/parser/asl/component/state/exec/state_task -type f -name "*.py" | xargs sed -i '/InvocationType/d'
find moto/stepfunctions/parser/asl/component/state/exec/state_task -type f -name "*.py" | xargs sed -i 's/InvocationRequest/dict/'

rm moto/stepfunctions/parser/asl/jsonata/packages.py
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i '/jsonata_package/d'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i '/singleton_factory/d'
find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/_JSONataJVMBridge.get().eval\_jsonata/None/'

find moto/stepfunctions/parser/asl -type f -name "*.py" | xargs sed -i 's/localstack.utils.collections/moto.utilities.collections/'

# Fix wildcard imports
find moto/stepfunctions/parser/asl/antlr -type f -name "*.py" | xargs sed -i  's/from antlr4 import \*/from antlr4 import DFA,ATNDeserializer,NoViableAltException,Parser,ParserATNSimulator,ParserRuleContext,ParseTreeListener,ParseTreeVisitor,PredictionContextCache,RecognitionException,Token,TokenStream,Lexer,LexerATNSimulator/'
find moto/stepfunctions/parser/asl/antlr -type f -name "*.py" | xargs sed -i  's/if sys.version_info[1] > 5://'
find moto/stepfunctions/parser/asl/antlr -type f -name "*.py" | xargs sed -i  's/from typing import TextIO\nelse://'

# Alter import paths as appropriate
find moto/stepfunctions/parser -type f | xargs sed -i  's/from localstack.services.stepfunctions/from moto.stepfunctions.parser/'
find moto/stepfunctions/parser -type f | xargs sed -i  's/from localstack.aws.api.stepfunctions import/from moto.stepfunctions.parser.api import/'
find moto/stepfunctions/parser/asl -type f | xargs sed -i  's/from localstack.utils.strings import long_uid/from uuid import uuid4 as long_uid/'

# Fix some typo's
mv moto/stepfunctions/parser/asl/component/intrinsic/functionname/state_fuinction_name_types.py moto/stepfunctions/parser/asl/component/intrinsic/functionname/state_function_name_types.py
find moto/stepfunctions/parser -type f -name "*.py" | xargs sed -i  's/from moto.stepfunctions.parser.asl.component.intrinsic.functionname.state_fuinction_name_types/from moto.stepfunctions.parser.asl.component.intrinsic.functionname.state_function_name_types/'

mv tmp/README.md moto/stepfunctions/parser/
mv tmp/api.py moto/stepfunctions/parser/
mv tmp/models.py moto/stepfunctions/parser/
mv tmp/utils.py moto/stepfunctions/parser/
mv tmp/boto_client.py moto/stepfunctions/parser/asl/utils/
mv tmp/state_task_service_api_gateway.py moto/stepfunctions/parser/asl/component/state/exec/state_task/service/
mv tmp/state_task_service_aws_sdk.py moto/stepfunctions/parser/asl/component/state/exec/state_task/service/
mv tmp/lambda_eval_utils.py moto/stepfunctions/parser/asl/component/state/exec/state_task/
mv tmp/execution.py moto/stepfunctions/parser/backend/
cp api.py moto/stepfunctions/parser/

rmdir tmp

# Format files as appropriate
ruff check --fix moto/stepfunctions/parser
ruff format moto/stepfunctions/parser
