data "aws_cloudwatch_event_bus" "default" {
  name = "default"
}

resource "aws_sqs_queue" "queue" {
  name = "queue"
}

resource "aws_iam_role" "pipe_role" {
  name = "pipe-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "pipes.amazonaws.com"
      }
    }]
  })
}

resource "aws_pipes_pipe" "pipe" {
  name     = "pipe-name"
  role_arn = aws_iam_role.pipe_role.arn
  source   = data.aws_cloudwatch_event_bus.default.arn
  target   = aws_sqs_queue.queue.arn
  source_parameters {
    filter_criteria {
      filter {
        pattern = jsonencode({
          source        = ["aws.s3"]
          "detail-type" = ["Object Created"]
        })
      }
    }
  }
}
