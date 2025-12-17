data "aws_caller_identity" "this" {}

data "aws_iam_policy_document" "this" {
  statement {
    actions = ["sts:AssumeRoleWithSAML"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_saml_provider.this.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "SAML:aud"
      values   = ["https://signin.aws.amazon.com/saml"]
    }
  }
}

data "aws_iam_saml_provider" "this" {
  arn = aws_iam_saml_provider.this.arn
}
