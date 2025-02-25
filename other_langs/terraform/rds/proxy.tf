data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "random_string" "this" {
  length  = 20
  special = true
  upper   = true
}

resource "aws_secretsmanager_secret" "test" {
  name = "rds/test/test_admin"
}

resource "aws_secretsmanager_secret_version" "test" {
  secret_id = aws_secretsmanager_secret.test.id
  secret_string = jsonencode({
    username = "test_admin"
    password = "${random_string.this.result}"
  })
}

data "aws_iam_policy_document" "rds_trust_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }

    actions = [
      "sts:AssumeRole",
    ]
  }
}

resource "aws_iam_role" "proxy" {
  assume_role_policy = data.aws_iam_policy_document.rds_trust_policy.json
  name               = "rds-proxy-${aws_db_instance.test.db_name}"
}

resource "aws_db_instance" "test" {
  allocated_storage   = 10
  db_name             = "testdb"
  engine              = "postgres"
  engine_version      = "15"
  instance_class      = "db.t3.micro"
  username            = "test"
  password            = random_string.this.result
  skip_final_snapshot = true
}

resource "aws_db_proxy" "main" {
  name                   = aws_db_instance.test.db_name
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = aws_iam_role.proxy.arn
  vpc_security_group_ids = []
  vpc_subnet_ids         = data.aws_subnets.all.ids

  auth {
    auth_scheme = "SECRETS"
    description = "Secrets through IAM Authentication"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_secretsmanager_secret.test.arn
  }
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    connection_borrow_timeout    = 120
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    session_pinning_filters      = ["EXCLUDE_VARIABLE_SETS"]
  }
}

resource "aws_db_proxy_target" "main" {
  db_instance_identifier = aws_db_instance.test.identifier
  db_proxy_name          = aws_db_proxy.main.name
  target_group_name      = aws_db_proxy_default_target_group.main.name
}
