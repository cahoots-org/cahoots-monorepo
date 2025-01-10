terraform {
  backend "s3" {
    # These values will be overridden by backend config files
    bucket         = "ai-dev-team-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "ai-dev-team-terraform-locks"
    encrypt        = true
  }
} 