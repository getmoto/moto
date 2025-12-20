resource "aws_dsql_cluster" "example" {
  deletion_protection_enabled = false
  tags = {"foo":"bar"}
}
