terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # version = "5.18.1" # with this line uncommented, the destroy works
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3         = "http://localhost:5000"
    cloudfront = "http://localhost:5000"
  }

  access_key = "my-access-key"
  secret_key = "my-secret-key"
}