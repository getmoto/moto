terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
   autoscaling = "http://localhost:5000"
    ec2        = "http://localhost:5000"
    sts        = "http://localhost:5000"
  }

  access_key = "my-access-key"
  secret_key = "my-access-key"
}
