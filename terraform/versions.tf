terraform {
  # 1.7+ gives me `terraform test`, provider-defined functions and the lock-file
  # behaviour I rely on; the machine I validated on runs 1.16.
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state. I keep it commented out so that a fresh clone validates without
  # any AWS resources existing yet; once the bucket + lock table are created I
  # uncomment this block and run `terraform init -migrate-state`.
  # backend "s3" {
  #   bucket         = "expense-tracker-tfstate-<account-id>"
  #   key            = "eks/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "expense-tracker-tfstate-lock"
  #   encrypt        = true
  # }
}
