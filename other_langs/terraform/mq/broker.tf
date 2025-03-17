resource "aws_mq_broker" "broker" {
  broker_name = "example"

  engine_type        = "RabbitMQ"
  engine_version     = "3.13"
  host_instance_type = "mq.t3.micro"

  user {
    username = "ExampleUser"
    password = "Th3P@ssw0rd!"
  }
}