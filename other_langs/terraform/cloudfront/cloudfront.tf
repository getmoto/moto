resource "aws_s3_bucket" "bucket" {
  bucket = "test-bucket"
}

module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "3.2.1"

  default_cache_behavior = {
    target_origin_id       = "s3-bucket"
    viewer_protocol_policy = "allow-all"
  }

  origin = {
    s3-bucket = {
      domain_name = aws_s3_bucket.bucket.bucket_domain_name
    }
  }
}