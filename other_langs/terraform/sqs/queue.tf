resource "aws_sqs_queue" "queue" {
  name                        = "test-queue"
  fifo_queue                  = false
  delay_seconds               = 0
  max_message_size            = 16384
  message_retention_seconds   = 86400
  visibility_timeout_seconds  = 30
  receive_wait_time_seconds   = 0
  redrive_policy              = null
  content_based_deduplication = false
  sqs_managed_sse_enabled     = true
}