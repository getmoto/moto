resource "aws_lambda_function_event_invoke_config" "test" {
  function_name                = aws_lambda_function.test_lambda.function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 21600
}