import { CreateQueueCommand, GetQueueUrlCommand, SQSClient } from '@aws-sdk/client-sqs'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'


const client = new SQSClient({
  region:'us-east-1',
  endpoint: 'http://localhost:5000',
});
const queueName = "test-queue-" + Math.floor(Math.random() * 10000);
console.log(queueName);
console.log("----")

const createQueueCommand = new CreateQueueCommand({
    QueueName: queueName,
    Attributes: {
      DelaySeconds: "60",
      MessageRetentionPeriod: "86400",
    },
});

await client.send(createQueueCommand);

const getUrlCommand = new GetQueueUrlCommand({ QueueName: queueName });

const response = await client.send(getUrlCommand);
console.log(response);
