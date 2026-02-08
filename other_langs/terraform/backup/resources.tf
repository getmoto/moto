resource "aws_backup_vault" "example" {
  name        = "example_backup_vault"
}

resource "aws_backup_plan" "example" {
  name = "tf_example_backup_plan"

  rule {
    rule_name         = "tf_example_backup_rule"
    target_vault_name = aws_backup_vault.example.name
    schedule          = "cron(0 12 * * ? *)"

    lifecycle {
      delete_after = 14
    }
  }

  advanced_backup_setting {
    backup_options = {
      WindowsVSS = "enabled"
    }
    resource_type = "EC2"
  }
}

resource "aws_backup_report_plan" "test" {
  name = "test_plan"
  report_delivery_channel {
    s3_bucket_name = aws_s3_bucket.simple_bucket.id
    formats = ["CSV", "JSON"]
    s3_key_prefix = "test_prefix"
  }
  report_setting {
    report_template = "BACKUP_JOB_REPORT"
  }
}

resource "aws_s3_bucket" "simple_bucket" {
  bucket = "simple-test-bucket"
}
