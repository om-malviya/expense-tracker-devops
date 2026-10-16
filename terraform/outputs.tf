output "vpc_id" {
  description = "ID of the VPC that hosts the cluster"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (load balancers, NAT gateway)"
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private subnet IDs (worker nodes)"
  value       = module.vpc.private_subnets
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes version running on the control plane"
  value       = module.eks.cluster_version
}

output "cluster_security_group_id" {
  description = "Security group attached to the control plane ENIs"
  value       = module.eks.cluster_security_group_id
}

output "node_group" {
  description = "Managed node group name and sizing (what `kubectl get nodes` should reflect)"
  value = {
    name         = one(values(module.eks.eks_managed_node_groups)).node_group_id
    min_size     = var.node_min_size
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
    instances    = var.node_instance_types
  }
}

output "ebs_csi_role_arn" {
  description = "IAM role the EBS CSI driver assumes through IRSA"
  value       = module.ebs_csi_irsa.iam_role_arn
}

output "configure_kubectl" {
  description = "Run this once to point kubectl at the new cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}
