variable "aws_region" {
  description = "The AWS Region to use."
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "The application name."
  type        = string
  default     = "sandwich"
}

variable "ami_id" {
  description = "The AMI to use."
  type        = string
  default     = "ami-12c6146b"
}

variable "instance_type" {
  description = "The instance type to use."
  type        = string
  default     = "t2.nano"
}
