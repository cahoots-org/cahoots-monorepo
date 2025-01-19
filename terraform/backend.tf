terraform {
  backend "s3" {
    # These values will be overridden by backend config files
    bucket         = "cahoots-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "cahoots-terraform-locks"
    encrypt        = true
  }
} 