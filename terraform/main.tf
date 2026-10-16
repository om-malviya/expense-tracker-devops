# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------
locals {
  cluster_name = "${var.project_name}-${var.environment}-eks"
}

# ---------------------------------------------------------------------------
# Network: VPC with 2 public + 2 private subnets across 2 AZs
#
# Public subnets  -> internet gateway, NAT gateway, internet-facing ELBs/ALBs
# Private subnets -> EKS worker nodes (no public IPs; outbound via the NAT GW)
#
# I use the community VPC module instead of hand-written aws_subnet /
# aws_route_table resources because it already encodes the EKS subnet-tagging
# rules and the IGW/NAT/route-table wiring that is easy to get subtly wrong.
# ---------------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "${local.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.azs
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  # One NAT gateway shared by both private subnets. Not highly available, but
  # a second NAT GW would double the most expensive line of this demo bill.
  enable_nat_gateway = true
  single_nat_gateway = true

  # Required by EKS so that nodes can resolve the cluster endpoint and so that
  # the EBS CSI driver / AWS APIs are reachable by DNS name.
  enable_dns_hostnames = true
  enable_dns_support   = true

  # These tags are how the AWS Load Balancer Controller and the in-tree cloud
  # provider discover which subnets to place load balancers in.
  public_subnet_tags = {
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"             = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
}

# ---------------------------------------------------------------------------
# Compute: EKS control plane + one managed node group in the private subnets
# ---------------------------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.37.1"

  cluster_name    = local.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = var.cluster_endpoint_public_access

  # Without this the IAM identity that runs `terraform apply` is NOT a cluster
  # admin (EKS access entries are opt-in), and the very first kubectl command
  # would fail with "Unauthorized".
  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    # The three add-ons every EKS cluster needs for DNS, service routing and pod networking.
    coredns    = {}
    kube-proxy = {}
    vpc-cni    = {}
    # The EBS CSI driver backs the PersistentVolumeClaim of the PostgreSQL
    # StatefulSet (storageClass gp3 in helm/expense-tracker/values-prod.yaml).
    # Since EKS 1.23 PVCs stay Pending forever without it. The driver needs an
    # IAM role to call the EC2 API, which it gets through IRSA (module below).
    aws-ebs-csi-driver = {
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }

  eks_managed_node_groups = {
    main = {
      instance_types = var.node_instance_types
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size

      labels = {
        role = "worker"
      }
    }
  }
}

# ---------------------------------------------------------------------------
# IRSA: IAM Role for the EBS CSI driver's Kubernetes ServiceAccount
#
# The driver runs as pods in kube-system; instead of giving the node role
# ec2:CreateVolume etc. (every pod on the node would inherit it), the pods
# assume this role through the cluster's OIDC provider. Least privilege.
# ---------------------------------------------------------------------------
module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "5.52.2"

  role_name             = "${local.cluster_name}-ebs-csi"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}
