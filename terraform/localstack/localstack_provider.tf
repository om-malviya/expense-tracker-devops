# LocalStack provider override (source file) - FOR AN OFFLINE `terraform plan` ONLY. NEVER USE FOR A REAL DEPLOYMENT.
#
# plan.sh copies this file into ../ as `zz_localstack_override.tf` (git-ignored via
# `*_override.tf`) for the duration of one plan and deletes it again. Terraform merges
# an *_override.tf provider block on top of providers.tf, so the region, default_tags
# and everything else stay as they are; only the credentials and the API endpoints are
# redirected to the LocalStack container on localhost:4566.
#
# Why I need this at all: `terraform plan` is not purely offline. Before it can show
# the diff it has to read data sources (caller identity, partition, IAM session
# context, EKS add-on versions ...), and those are real API calls. Without an AWS
# account they fail with "no valid credential sources". Pointing the provider at a
# local AWS emulator lets me prove the configuration plans end-to-end on my laptop.
provider "aws" {
  # LocalStack accepts any non-empty key pair; these are the documented dummies.
  access_key = "test"
  secret_key = "test"
  region     = "ap-south-1"

  # The emulator has no real account, so skip every check that would phone home.
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true

  # LocalStack serves buckets under http://localhost:4566/<bucket>, not <bucket>.localhost.
  s3_use_path_style = true

  endpoints {
    ec2            = "http://localhost:4566"
    iam            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    eks            = "http://localhost:4566"
    kms            = "http://localhost:4566"
    logs           = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    autoscaling    = "http://localhost:4566"
    s3             = "http://localhost:4566"
    ssm            = "http://localhost:4566"
    elb            = "http://localhost:4566"
    elbv2          = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
  }
}
