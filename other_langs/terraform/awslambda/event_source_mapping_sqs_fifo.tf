resource "aws_sqs_queue" "esm_fifo_queue" {
  name                        = "testfifoqueue.fifo"
  fifo_queue                  = true
}


resource "aws_lambda_event_source_mapping" "esm_to_sqs_fifo_queue" {
  event_source_arn = aws_sqs_queue.esm_fifo_queue.arn
  function_name    = aws_lambda_function.test_lambda.arn
  batch_size       = 10
}