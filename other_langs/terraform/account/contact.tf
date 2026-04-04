resource "aws_account_alternate_contact" "this" {
  title                  = "Title test"
  alternate_contact_type = "SECURITY"
  email_address          = "testemail@test.com"
  name                   = "contact name"
  phone_number           = "+9876-321"
}