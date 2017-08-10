require 'aws-sdk'

sqs = Aws::SQS::Resource.new(region: 'us-west-2', endpoint: 'http://localhost:5000')
my_queue = sqs.create_queue(queue_name: 'my-bucket')

puts sqs.client.list_queues()
