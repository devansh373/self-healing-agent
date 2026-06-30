terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_lambda_function" "healer_demo" {
  function_name = "self-healing-demo-fn"
  filename      = "function.zip"
  handler       = "index.handler"
  runtime       = "python3.12"
  # NOTE: "role" is a required argument for aws_lambda_function and is
  # intentionally omitted here — this is the bug Phase 1 exists to catch and fix.
  # Every Lambda function needs an IAM execution role ARN.
  #
  # Why not "runtime" (as the original spec suggested)?
  # AWS provider ~> 5.0 made "runtime" optional (Lambda now supports container
  # images via image_uri, where runtime is irrelevant). So terraform validate
  # no longer catches a missing "runtime" at schema level. The "role" argument
  # remains unconditionally required across all provider versions.
}
