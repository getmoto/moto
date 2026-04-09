resource "aws_s3_bucket" "bucket_with_lifecycle_configuration" {
  bucket = "test-bucket-with-lifecycle-configuration"
}

resource "aws_s3_bucket_lifecycle_configuration" "test_lifecycle_configuration" {
  bucket = aws_s3_bucket.bucket_with_lifecycle_configuration.id
  rule {
    id     = "OptimizeData"
    status = "Enabled"

    filter {
      prefix = "test-logs/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
