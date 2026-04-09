terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true

  endpoints {
    ec2          = "http://localhost:5000"
    codebuild    = "http://localhost:5000"
    iam          = "http://localhost:5000"
    logs         = "http://localhost:5000"
    s3           = "http://localhost:5000"
    s3control    = "http://localhost:5000"
  }

  access_key = "my-access-key"
  secret_key = "my-secret-key"
}