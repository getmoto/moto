output "saml_provider_create_date" {
  value = data.aws_iam_saml_provider.this.create_date
}

output "saml_provider_create_name" {
  value = data.aws_iam_saml_provider.this.name
}

output "saml_provider_saml_metadata_document" {
  value = data.aws_iam_saml_provider.this.saml_metadata_document
}
