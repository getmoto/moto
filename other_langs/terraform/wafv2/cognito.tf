# Create a Cognito User Pool (this assumes you need a new one)
resource "aws_cognito_user_pool" "example" {
  name = "example-user-pool"
}

# Create a WAFv2 Web ACL
resource "aws_wafv2_web_acl" "example" {
  name        = "example-web-acl"
  description = "Example WAFv2 Web ACL for Cognito User Pool"
  scope       = "REGIONAL" # Since Cognito is a regional service
  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "exampleWebACL"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "block-bad-ips"
    priority = 1

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.example.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "blockBadIps"
      sampled_requests_enabled   = true
    }
  }
}

# Create an IP Set for the WAFv2 rule
resource "aws_wafv2_ip_set" "example" {
  name        = "example-ip-set"
  description = "Example IP Set for bad actors"
  scope       = "REGIONAL"

  ip_address_version = "IPV4"

  addresses = [
    "192.0.2.0/24",  # Example IP addresses to block
    "198.51.100.0/24"
  ]
}

# Associate the WAFv2 Web ACL with the Cognito User Pool
resource "aws_wafv2_web_acl_association" "example" {
  resource_arn = aws_cognito_user_pool.example.arn
  web_acl_arn  = aws_wafv2_web_acl.example.arn
}