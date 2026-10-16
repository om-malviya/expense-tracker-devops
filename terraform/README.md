# terraform/ - AWS VPC + EKS for the Expense Tracker

> **Cost warning.** This configuration creates an EKS control plane (~0.10 USD/h), one NAT gateway
> (~0.05 USD/h + data) and two `t3.medium` nodes (~0.05 USD/h each) in `ap-south-1`: roughly
> **5-6 USD per day** while it exists, plus a few cents for the EBS volume behind Postgres.
> I run `terraform destroy` as soon as the demo is over and check in the console that no EKS
> cluster, NAT gateway, EIP, load balancer or EBS volume is left behind.
> No AWS credentials are stored in this folder: I authenticate with `aws configure` / `AWS_PROFILE` / SSO.

## What gets created and why

| Resource | Why I need it |
|---|---|
| **VPC** `expense-tracker-dev-eks-vpc` (`10.30.0.0/16`) | Private network for the whole cluster; `terraform-aws-modules/vpc` 5.8.1 wires IGW, NAT, route tables for me |
| **2 public subnets** (`10.30.101.0/24`, `10.30.102.0/24`, one per AZ) | Internet-facing load balancers for the Ingress controller and the NAT gateway. Tagged `kubernetes.io/role/elb=1` so the AWS Load Balancer Controller finds them |
| **2 private subnets** (`10.30.1.0/24`, `10.30.2.0/24`) | Worker nodes live here without public IPs; outbound traffic (image pulls from GHCR, AWS APIs) leaves through the NAT GW. Tagged `kubernetes.io/role/internal-elb=1` |
| **Internet gateway + 1 NAT gateway + EIP** | `single_nat_gateway = true`: one NAT for both AZs - not HA, but it halves the most expensive part of the bill |
| **EKS cluster** `expense-tracker-dev-eks` (Kubernetes 1.31) | Managed control plane; `terraform-aws-modules/eks` 20.37.1 also creates the IAM roles, security groups, OIDC provider, KMS key for secret encryption and the CloudWatch log group |
| **Managed node group** `main` (1..3 x `t3.medium`, desired 2) | Runs the app, Postgres and kube-prometheus-stack. Two nodes so each 2-replica Deployment can spread; max 3 caps the cost |
| **Add-ons** `coredns`, `kube-proxy`, `vpc-cni` | DNS, Service routing and pod networking - the baseline every EKS cluster needs |
| **Add-on** `aws-ebs-csi-driver` + **IRSA role** | Provisions the EBS volume behind the Postgres PVC (`storageClass: gp3` in `helm/expense-tracker/values-prod.yaml`). Since EKS 1.23 PVCs stay `Pending` without it. The driver gets its EC2 permissions through an IAM Role for Service Accounts instead of the node role, so only the CSI pods can create volumes |
| `enable_cluster_creator_admin_permissions = true` | Makes the IAM identity that runs `terraform apply` a cluster admin via EKS access entries; otherwise the first `kubectl` call fails with `Unauthorized` |

## Files

| File | Content |
|---|---|
| `versions.tf` | Terraform >= 1.7, AWS provider `~> 5.0`, commented-out S3/DynamoDB remote state |
| `providers.tf` | region + `default_tags` (Project / Environment / ManagedBy / Owner, merged with `var.tags`) |
| `variables.tf` | region, project name, environment, VPC CIDR, AZs, subnet CIDRs, cluster version, node sizing, endpoint access, extra tags - with validation rules |
| `main.tf` | VPC module, EKS module with one managed node group and the four add-ons, IRSA module for the EBS CSI driver |
| `outputs.tf` | vpc id, subnet ids, cluster name / endpoint / version / SG, node group sizing, EBS CSI role ARN, ready-to-copy `configure_kubectl` command |
| `terraform.tfvars.example` | example values - copy to `terraform.tfvars` (git-ignored) |
| `.gitignore` | `.terraform/`, state files, plans, `terraform.tfvars`, overrides |
| `.terraform.lock.hcl` | provider versions pinned by `terraform init` (committed on purpose for reproducible plans) |

## Workflow

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars      # adjust region / sizes if needed

terraform init                                     # downloads the vpc/eks/iam modules and the AWS provider
terraform fmt -check -recursive                    # canonical formatting (CI fails on a diff)
terraform validate                                 # syntax + type checking, no credentials needed
terraform plan -out=tfplan                         # ~60 resources to add, 0 to change, 0 to destroy
terraform apply tfplan                             # 12-15 minutes (EKS control plane is the slow part)

$(terraform output -raw configure_kubectl)         # aws eks update-kubeconfig --region ap-south-1 --name expense-tracker-dev-eks
kubectl get nodes                                  # two t3.medium nodes Ready

# deploy the app (see k8s/README.md and helm/expense-tracker/)
kubectl apply -f ../k8s/namespace.yaml
helm upgrade --install expense-tracker ../helm/expense-tracker -n expense-tracker -f ../helm/expense-tracker/values-prod.yaml

# tear everything down when done
helm uninstall expense-tracker -n expense-tracker  # removes the Postgres PVC -> EBS volume
helm uninstall ingress-nginx -n ingress-nginx      # if installed: deletes the NLB *before* the VPC is torn down
terraform destroy
```

Order matters on the way down: load balancers and EBS volumes created from inside Kubernetes are not in the
Terraform state, so if they still exist `terraform destroy` fails on the VPC / subnets with "dependency violation".

## Validation on this machine (no AWS credentials)

```text
$ terraform fmt -check -recursive        # exit 0, no diff
$ terraform init -backend=false
Initializing modules...
Downloading registry.terraform.io/terraform-aws-modules/vpc/aws 5.8.1 for vpc...
Downloading registry.terraform.io/terraform-aws-modules/eks/aws 20.37.1 for eks...
Downloading registry.terraform.io/terraform-aws-modules/iam/aws 5.52.2 for ebs_csi_irsa...
Downloading registry.terraform.io/terraform-aws-modules/kms/aws 2.1.0 for eks.kms...
Initializing provider plugins...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)
- Installed hashicorp/tls v4.4.1, hashicorp/time v0.14.2, hashicorp/cloudinit v2.4.1, hashicorp/null v3.3.2
Terraform has been successfully initialized!

$ terraform validate
Success! The configuration is valid.
```

## What `terraform plan` shows

```text
Plan: 6x to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + cluster_endpoint   = (known after apply)
  + cluster_name       = "expense-tracker-dev-eks"
  + cluster_version    = "1.31"
  + configure_kubectl  = "aws eks update-kubeconfig --region ap-south-1 --name expense-tracker-dev-eks"
  + private_subnet_ids = (known after apply)
  + public_subnet_ids  = (known after apply)
  + vpc_id             = (known after apply)
```

Main resources in the plan: `aws_vpc`, 2x public + 2x private `aws_subnet`, `aws_internet_gateway`,
`aws_nat_gateway` + `aws_eip`, route tables and associations, `aws_eks_cluster`, cluster and node IAM roles
and policy attachments, 2x `aws_security_group`, `aws_eks_node_group`, `aws_launch_template`,
4x `aws_eks_addon`, `aws_iam_openid_connect_provider`, the EBS CSI `aws_iam_role`, `aws_kms_key`
(secrets encryption) and `aws_cloudwatch_log_group`.

`terraform destroy` reverses the same list (`Plan: 0 to add, 0 to change, 6x to destroy`); the node group
and the control plane take the longest (~4 and ~2 minutes).

## Plan evidence without an AWS account

I did not have an AWS account while building this project, so I could not run `terraform apply`
or `terraform destroy`. Everything that *can* be proven without one is captured in `docs/screenshots/`:

| Evidence | What I ran | Where |
|---|---|---|
| init + fmt + validate | `terraform init -backend=false`, `terraform fmt -check -recursive`, `terraform validate` (real downloads of the vpc/eks/iam/kms modules and the 5 providers; exit 0) | `docs/screenshots/m7-terraform-init-validate.{txt,png}` |
| full `terraform plan` | `terraform/localstack/plan.sh` -> `terraform init -reconfigure` + `terraform plan -var-file=terraform.tfvars.example -out=localstack.tfplan` against a **LocalStack 4.6 community** container (`docker run -d --name localstack -p 4566:4566 localstack/localstack:4.6`) | `docs/screenshots/m7-terraform-plan.txt` (all 1830 lines), `m7-terraform-plan.png` (first 60 lines + result), `m7-terraform-plan-summary.{txt,png}` (the 61 resource addresses + the `Plan:` line) |

Result of the plan:

```text
Plan: 61 to add, 0 to change, 0 to destroy.
```

### How the plan works without credentials

`terraform plan` has to read data sources before it can compute the diff, and some of those are real
API calls (`sts:GetCallerIdentity`, and `iam:GetRole` through `aws_iam_session_context`, which the EKS
module uses to make the caller the cluster admin). Without credentials the plan stops at
`No valid credential sources found`. `terraform/localstack/plan.sh` therefore drops a temporary
`zz_localstack_override.tf` next to `providers.tf` (dummy `test` keys, `skip_*` checks on, every
`endpoints { ... }` entry pointing at `http://localhost:4566`), runs init + plan, and removes the
override, the saved plan and any lock-file change again through an `EXIT` trap. The committed
`.terraform.lock.hcl` was byte-identical before and after (`git diff --stat` empty), and `*_override.tf`
is git-ignored so the override can never be committed by accident. Details: `terraform/localstack/README.md`.

### What LocalStack can and cannot emulate

| | LocalStack 4.6 community |
|---|---|
| **Emulated and used by the plan** | STS (`aws_caller_identity` -> account `000000000000`), IAM (`aws_iam_session_context` -> `arn:aws:iam::000000000000:root`) |
| **Computed locally, no API** | `aws_partition`, `aws_region`, `aws_iam_policy_document` |
| **Not emulated** | EKS (cluster, node group, add-ons, access entries, OIDC provider) is Pro-only. The plan does not need it: the four `aws_eks_addon_version` reads depend on the cluster resource and are deferred (`will be read during apply`) |
| **Why apply is impossible** | Even the services LocalStack has (EC2, KMS, IAM) are only partially emulated, and EKS is missing entirely, so `apply` would either fail or create fake resources. The override exists for `plan` only |

The `latest` LocalStack image (2026.x) exits with `License activation failed` unless `LOCALSTACK_AUTH_TOKEN`
is set; the 4.x tags are the last licence-free community builds, which is why `plan.sh` documents `4.6`.

### What still requires a real account (and the exact commands)

`terraform apply`, `terraform destroy` and the AWS console screenshots (VPC, EKS cluster, node group,
NAT gateway) cannot be faked and are not included. When an account is available this is the complete
sequence, each line producing one piece of evidence via `scripts/capture-evidence.sh`:

```bash
aws configure                                           # or AWS_PROFILE=... / aws sso login
cd terraform && cp terraform.tfvars.example terraform.tfvars

scripts/capture-evidence.sh m7-terraform-plan-aws  "cd terraform && terraform init && terraform plan -no-color -out=tfplan"
scripts/capture-evidence.sh m7-terraform-apply     "cd terraform && terraform apply -no-color tfplan"          # 12-15 min
scripts/capture-evidence.sh m7-terraform-outputs   "cd terraform && terraform output"
scripts/capture-evidence.sh m7-kubectl-get-nodes   "aws eks update-kubeconfig --region ap-south-1 --name expense-tracker-dev-eks && kubectl get nodes -o wide"
# console screenshots: VPC -> Your VPCs / Subnets / NAT gateways, EKS -> Clusters -> expense-tracker-dev-eks -> Compute
scripts/capture-evidence.sh m7-terraform-destroy   "cd terraform && terraform destroy -no-color -auto-approve"  # Plan: 0 to add, 0 to change, 61 to destroy.
```

After the destroy I would check the console (EKS, EC2 > NAT gateways, Elastic IPs, Load balancers,
EBS volumes) and Cost Explorer to make sure nothing billable is left behind.
