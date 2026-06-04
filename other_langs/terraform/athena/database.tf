resource "aws_s3_bucket" "athena_results" {
  bucket = "athena-query-results"
}

resource "aws_athena_database" "example" {
  name   = "example_db"
  bucket = aws_s3_bucket.athena_results.id
}
