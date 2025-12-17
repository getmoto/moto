resource "aws_iam_policy" "policy" {
  name        = "test_policy"
  path        = "/"
  description = "My test policy"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:Describe*",
        ]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })

  tags = {
    t1 = "v1"
  }
}

resource "aws_iam_saml_provider" "this" {
  name                   = "sso-test"
  saml_metadata_document = file("${path.module}/sample-metadata.xml")
}
