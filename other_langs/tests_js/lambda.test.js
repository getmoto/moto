import { LambdaClient, ListFunctionsCommand } from '@aws-sdk/client-lambda'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'

const client_ = new LambdaClient({ endpoint: 'http://localhost:5000', region: 'us-east-1'});

await client_.send(new ListFunctionsCommand());
