import { EC2Client, RunInstancesCommand } from '@aws-sdk/client-ec2'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'

const client = new EC2Client({endpoint:'http://localhost:5000', region: 'us-east-1'});

const command = new RunInstancesCommand({
    InstanceType: 't2.nano',
    ImageId: 'ami-0001',
    MinCount: 1,
    MaxCount: 1,
});

const { Instances } = await client.send(command);
