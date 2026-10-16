provider "aws" {
  region = var.aws_region

  # default_tags are stamped on every taggable resource the provider creates,
  # so I can find (and bill, and destroy) everything that belongs to this
  # project with one tag filter in the console / Cost Explorer.
  default_tags {
    tags = merge(
      {
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform"
        Owner       = "om-malviya"
      },
      var.tags,
    )
  }
}
