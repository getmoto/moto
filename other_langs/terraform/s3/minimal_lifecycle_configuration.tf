resource "aws_s3_bucket" "bucket_with_minimal_lifecycle_configuration" {
  bucket = "test-bucket-with-minimal-lifecycle-configuration"
}

resource "aws_s3_bucket_lifecycle_configuration" "test_minimal_lifecycle_configuration" {
  bucket = aws_s3_bucket.bucket_with_minimal_lifecycle_configuration.id
  rule {
    id     = "MinimalRule"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }
}
