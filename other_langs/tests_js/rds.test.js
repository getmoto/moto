import { CreateDBInstanceCommand, DescribeDBInstancesCommand, RDSClient } from '@aws-sdk/client-rds'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'

const client = new RDSClient({region: 'us-east-1', endpoint:'http://localhost:5000'});
const create_command = new CreateDBInstanceCommand(
    {
        DBInstanceClass: "dbic",
        DBInstanceIdentifier: "dbii",
        Engine: "mysql",
        DBName: "dbn"
    }
);

await client.send(create_command);

const command = new DescribeDBInstancesCommand({});
const res = await client.send(command);
