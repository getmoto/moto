data "aws_iam_policy_document" "assume_firehose_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "firehose_role" {
  name               = "firehose-role"
  assume_role_policy = data.aws_iam_policy_document.assume_firehose_policy.json
}

resource "aws_s3_bucket" "bucket" {
  bucket = "test-bucket"
}

resource "aws_kinesis_firehose_delivery_stream" "firehose" {
  name        = "firehose-stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = aws_s3_bucket.bucket.arn
  }
}