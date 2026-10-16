variable "aws_region" {
  description = "AWS region for every resource. ap-south-1 (Mumbai) is the closest region to me."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project slug used in resource names and the Project tag"
  type        = string
  default     = "expense-tracker"
}

variable "environment" {
  description = "Environment name (dev / staging / prod) used in names and tags"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.30.0.0/16"
}

variable "azs" {
  description = "Availability zones to spread the subnets across. EKS needs at least two."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.azs) >= 2
    error_message = "EKS requires subnets in at least two availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs (one per AZ) - internet-facing load balancers and the NAT gateway live here"
  type        = list(string)
  default     = ["10.30.101.0/24", "10.30.102.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs (one per AZ) - the EKS worker nodes live here and reach the internet via NAT"
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS control plane"
  type        = string
  default     = "1.31"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group (t3.medium = 2 vCPU / 4 GiB, enough for the whole stack plus monitoring)"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_desired_size" {
  description = "Desired number of worker nodes at creation time (two so that every Deployment with 2 replicas can spread across nodes)"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of worker nodes (the cluster autoscaler / HPA can never exceed this, which caps my bill)"
  type        = number
  default     = 3
}

variable "cluster_endpoint_public_access" {
  description = "Expose the EKS API endpoint publicly. true for the demo so I can run kubectl from my laptop; in production I would restrict it with cluster_endpoint_public_access_cidrs or go private-only."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Extra tags merged into the provider default_tags"
  type        = map(string)
  default     = {}
}
