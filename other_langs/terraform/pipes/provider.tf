provider "aws" {
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    events = "http://localhost:5000"
    iam    = "http://localhost:5000"
    pipes  = "http://localhost:5000"
    sqs    = "http://localhost:5000"
  }

  access_key = "my-access-key"
  secret_key = "my-secret-key"
}
