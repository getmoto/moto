resource "aws_vpc" "example" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "example1" {
  vpc_id     = aws_vpc.example.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_subnet" "example2" {
  vpc_id     = aws_vpc.example.id
  cidr_block = "10.0.2.0/24"
}

resource "aws_security_group" "example1" {
  name        = "sg name"
  description = "Desc"
  vpc_id      = aws_vpc.example.id
}

resource "aws_security_group" "example2" {
  name        = "sg name 2"
  description = "Desc"
  vpc_id      = aws_vpc.example.id
}

resource "aws_s3_bucket" "example" {
  bucket = "example"
}

resource "aws_s3_bucket_acl" "example" {
  bucket = aws_s3_bucket.example.id
  acl    = "private"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "example" {
  name               = "example"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "example" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeDhcpOptions",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeSubnets",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeVpcs",
    ]

    resources = ["*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["ec2:CreateNetworkInterfacePermission"]
    resources = ["arn:aws:ec2:us-east-1:123456789012:network-interface/*"]

    condition {
      test     = "StringEquals"
      variable = "ec2:Subnet"

      values = [
        aws_subnet.example1.arn,
        aws_subnet.example2.arn,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "ec2:AuthorizedService"
      values   = ["codebuild.amazonaws.com"]
    }
  }

  statement {
    effect  = "Allow"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.example.arn,
      "${aws_s3_bucket.example.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "example" {
  role   = aws_iam_role.example.name
  policy = data.aws_iam_policy_document.example.json
}

resource "aws_codebuild_project" "example" {
  name          = "test-project"
  description   = "test_codebuild_project"
  build_timeout = 5
  service_role  = aws_iam_role.example.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = aws_s3_bucket.example.bucket
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "SOME_KEY1"
      value = "SOME_VALUE1"
    }

    environment_variable {
      name  = "SOME_KEY2"
      value = "SOME_VALUE2"
      type  = "PARAMETER_STORE"
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "log-group"
      stream_name = "log-stream"
    }

    s3_logs {
      status   = "ENABLED"
      location = "${aws_s3_bucket.example.id}/build-log"
    }
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/mitchellh/packer.git"
    git_clone_depth = 1

    git_submodules_config {
      fetch_submodules = true
    }
  }

  source_version = "master"

  vpc_config {
    vpc_id = aws_vpc.example.id

    subnets = [
      aws_subnet.example1.id,
      aws_subnet.example2.id,
    ]

    security_group_ids = [
      aws_security_group.example1.id,
      aws_security_group.example2.id,
    ]
  }

  tags = {
    Environment = "Test"
  }
}

resource "aws_codebuild_project" "project-with-cache" {
  name           = "test-project-cache"
  description    = "test_codebuild_project_cache"
  build_timeout  = 5
  queued_timeout = 5

  service_role = aws_iam_role.example.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type  = "LOCAL"
    modes = ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE"]
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "SOME_KEY1"
      value = "SOME_VALUE1"
    }
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/mitchellh/packer.git"
    git_clone_depth = 1
  }

  tags = {
    Environment = "Test"
  }
}