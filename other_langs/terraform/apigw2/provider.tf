provider "aws" {
  access_key = "moto"
  secret_key = "moto"
  region     = "us-east-2"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    apigatewayv2            = "http://localhost:5000"
    ec2                     = "http://localhost:5000"
    sts                     = "http://localhost:5000"
  }
}