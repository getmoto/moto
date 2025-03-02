resource "aws_apigatewayv2_api" "example" {
  name          = "minimal-example"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "example" {
  api_id = aws_apigatewayv2_api.example.id
  name   = "example-stage"
}

resource "aws_security_group" "this" {
  name        = "testsg"
  vpc_id      = data.aws_vpc.this.id
}

resource "aws_apigatewayv2_vpc_link" "example" {
  name               = "example"
  security_group_ids = [aws_security_group.this.id]
  subnet_ids         = data.aws_subnets.this.ids

  tags = {
    Usage = "example"
  }
}