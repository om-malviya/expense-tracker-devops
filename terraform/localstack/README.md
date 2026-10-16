# terraform/localstack/ - offline `terraform plan` against LocalStack

> **This folder is only for producing a `terraform plan` on a laptop without an AWS account.**
> It must **never** be used for a real deployment: the override points every AWS API at a local
> emulator with dummy credentials, so an `apply` would create nothing real and a `destroy` would
> clean nothing up. The real workflow is the one in `../README.md`.

## Why it exists

`terraform validate` works fully offline, but `terraform plan` does not: before it can compute the
diff it reads data sources - `aws_caller_identity`, `aws_partition`, `aws_region`,
`aws_iam_session_context` (the EKS module uses it to decide who becomes cluster admin) - and those
are real STS / IAM calls. Without credentials the plan stops at
`Error: No valid credential sources found`. I did not have an AWS account while building this
project, so to prove the configuration plans end-to-end I ran it against
[LocalStack](https://github.com/localstack/localstack), an AWS API emulator in a Docker container.

## Files

| File | Purpose |
|---|---|
| `localstack_provider.tf` | Source of the Terraform `*_override.tf` provider block (named without the `_override` suffix so `../.gitignore` does not swallow it): dummy `test` keys, all `skip_*` checks on, `endpoints {}` for ec2/iam/sts/eks/kms/logs/cloudwatch/autoscaling/s3/... = `http://localhost:4566` |
| `plan.sh` | Copies the override into `../` as `zz_localstack_override.tf`, runs `terraform init -reconfigure` and `terraform plan -var-file=terraform.tfvars.example -out=localstack.tfplan`, then **always** (trap) removes the override and the plan file and restores `.terraform.lock.hcl` |

The copied override is named `zz_localstack_override.tf` on purpose: `../.gitignore` ignores
`*_override.tf`, so even if the trap never runs the file cannot be committed.

## How to run

```bash
# LocalStack 4.x community edition is free and needs no account; the `latest` tag
# (2026.x) exits with "License activation failed" unless LOCALSTACK_AUTH_TOKEN is set.
docker run -d --name localstack -p 4566:4566 localstack/localstack:4.6
curl -s localhost:4566/_localstack/health | head -c 200     # wait until this answers

terraform/localstack/plan.sh                     # full plan   -> Plan: 61 to add, 0 to change, 0 to destroy.
terraform/localstack/plan.sh -target=module.vpc  # VPC-only plan, if the full one is ever blocked

docker rm -f localstack
```

## What LocalStack community does and does not emulate here

| Needed by the plan | LocalStack 4.6 community | Result |
|---|---|---|
| `sts:GetCallerIdentity` (`data.aws_caller_identity`) | yes | account `000000000000` |
| `iam:GetRole` via `data.aws_iam_session_context` | yes | `arn:aws:iam::000000000000:root` |
| `data.aws_partition`, `data.aws_region`, `data.aws_iam_policy_document` | computed locally by the provider | no API call |
| `data.aws_eks_addon_version` (4x) | **no EKS in community** | not needed: the module defers them to apply time (`will be read during apply`) because they depend on the cluster resource |
| EC2 / VPC / NAT / EIP creation | partially (plan does not create anything) | n/a |
| EKS cluster, node group, add-ons, OIDC provider | **not emulated** (Pro only) | n/a for plan |

So the plan output is real Terraform output for this configuration (61 resources: VPC, 4 subnets,
IGW, NAT + EIP, route tables, KMS key, CloudWatch log group, IAM roles and attachments, security
groups and rules, EKS cluster, access entries, OIDC provider, launch template, node group, 4 add-ons,
EBS CSI IRSA role), but **nothing can be applied here**. `terraform apply`, `terraform destroy` and
the AWS console screenshots need a real account - see "Plan evidence without an AWS account" in
`../README.md` for the exact commands to run once one is available.
