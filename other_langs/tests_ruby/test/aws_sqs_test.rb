require 'aws-sdk-sqs'
require 'minitest/autorun'

class AwsSqsTest < Minitest::Test
  def test_all_sqs_actions
    region = 'us-east-1'

    sqs_client = Aws::SQS::Client.new(region: region)

    sqs_client.list_queues

    sqs_client.create_queue(queue_name: "q1")

    sqs_client.list_queues

    queue_url = sqs_client.get_queue_url(queue_name: "q1").queue_url

    sqs_client.add_permission({queue_url: queue_url, label: "String", aws_account_ids: ["String"], actions: ["GetQueueUrl"]})

    sqs_client.send_message(
      queue_url: queue_url,
      message_body: "message_body"
    )

    sqs_client.remove_permission({queue_url: queue_url, label: "String"})

    sqs_client.set_queue_attributes({queue_url: queue_url, attributes: {"All" => "DelaySeconds"}})

    sqs_client.receive_message(
      queue_url: queue_url,
      max_number_of_messages: 10,
      attribute_names: ['All'],
      message_attribute_names: ['All']
    ).messages

    sqs_client.purge_queue({queue_url: queue_url})

    sqs_client.delete_queue(queue_url: queue_url)
  end
end