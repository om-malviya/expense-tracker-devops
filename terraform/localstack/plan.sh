#!/usr/bin/env bash
# Run `terraform plan` for ../ against a local LocalStack container instead of AWS.
#
# Purpose: produce real plan output on a machine WITHOUT an AWS account. This is
# evidence that the configuration initialises, resolves its data sources and plans;
# it is NOT a deployment path. Never run `terraform apply` with the override in place.
#
# Usage:
#   docker run -d --name localstack -p 4566:4566 localstack/localstack:4.6
#   terraform/localstack/plan.sh                       # full plan
#   terraform/localstack/plan.sh -target=module.vpc    # extra args go to `terraform plan`
#
# What it does:
#   1. copies localstack_provider.tf into ../ as zz_localstack_override.tf
#      (the *_override.tf suffix makes Terraform merge it over providers.tf;
#       the same pattern is git-ignored so it can never be committed by accident)
#   2. terraform init -reconfigure   (no backend is configured, so this is local only)
#   3. terraform plan -var-file=terraform.tfvars.example -out=localstack.tfplan
#   4. ALWAYS removes the override again (trap on EXIT), restores .terraform.lock.hcl
#      from a backup so the committed provider pins stay byte-identical, and deletes
#      the saved plan - a plan made against an emulator must never be applied.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$(cd "$HERE/.." && pwd)"
OVERRIDE="$TF_DIR/zz_localstack_override.tf"
LOCK="$TF_DIR/.terraform.lock.hcl"
LOCK_BAK="$(mktemp)"
ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"

cleanup() {
  rm -f "$OVERRIDE" "$TF_DIR/localstack.tfplan"
  # init -reconfigure may rewrite the lock file (e.g. add hashes for this platform);
  # the committed version is the source of truth, so put it back.
  if [ -s "$LOCK_BAK" ]; then cp "$LOCK_BAK" "$LOCK"; fi
  rm -f "$LOCK_BAK"
  echo "localstack/plan.sh: override and plan file removed, lock file restored"
}
trap cleanup EXIT INT TERM

if ! curl -sf --max-time 5 "$ENDPOINT/_localstack/health" >/dev/null; then
  echo "LocalStack is not reachable at $ENDPOINT - start it first:" >&2
  echo "  docker run -d --name localstack -p 4566:4566 localstack/localstack:4.6" >&2
  exit 1
fi

cp "$LOCK" "$LOCK_BAK"
cp "$HERE/localstack_provider.tf" "$OVERRIDE"
cd "$TF_DIR"

# Belt and braces: even if some code path ignored the provider override, these
# dummy credentials guarantee nothing can reach a real AWS account.
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=ap-south-1
unset AWS_PROFILE AWS_SESSION_TOKEN 2>/dev/null || true

# -no-color: Terraform ignores NO_COLOR, and the output of this script is kept as
# plain-text evidence in docs/screenshots/, so escape codes would only be noise.
echo "\$ terraform init -reconfigure"
terraform init -reconfigure -input=false -no-color
echo
echo "\$ terraform plan -var-file=terraform.tfvars.example -out=localstack.tfplan $*"
terraform plan -input=false -no-color -var-file=terraform.tfvars.example -out=localstack.tfplan "$@"
