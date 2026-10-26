#!/usr/bin/env bash
# Install (or upgrade) Argo CD into namespace `argocd` from the upstream manifests.
# Safe to re-run: every step is an apply / wait, nothing is created twice.
#
#   gitops/argocd/install.sh                         # upstream "stable" (what I ran: v3.5.6)
#   ARGOCD_VERSION=v3.5.6 gitops/argocd/install.sh   # pin a release instead of stable
#   ARGOCD_LEAN=1 gitops/argocd/install.sh           # laptop mode: dex (SSO) and notifications scaled to 0
#
# Then register the app:   kubectl apply -f gitops/argocd/application.yaml
# And open the UI:         kubectl port-forward svc/argocd-server -n argocd 18080:443  ->  https://localhost:18080
set -euo pipefail

NAMESPACE=argocd
ARGOCD_VERSION="${ARGOCD_VERSION:-stable}"
MANIFEST="https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
TIMEOUT="${TIMEOUT:-5m}"
ARGOCD_LEAN="${ARGOCD_LEAN:-0}"

echo "==> kube context: $(kubectl config current-context)"

echo "==> namespace ${NAMESPACE}"
# create-or-keep: `create` alone fails on the second run, the dry-run | apply pipe does not.
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "==> Argo CD manifests (${ARGOCD_VERSION})"
# --server-side: the ApplicationSet CRD is larger than the 256 KiB last-applied annotation that
# client-side apply would write, so a plain `kubectl apply` fails on it.
# --force-conflicts: on a re-run/upgrade take back the fields this manifest sets, even if another
# field manager (a hand edit, an older install) changed them since.
kubectl apply --server-side --force-conflicts -n "${NAMESPACE}" -f "${MANIFEST}"

# Neither dex (SSO) nor the notifications controller is used here (local admin login, no Slack or
# e-mail notifications); on a single-node laptop cluster turning them off saves one image pull and
# ~100 MiB of memory. The upstream Deployments have no `replicas` field, so the apply above never
# changes the count - it is set explicitly in both directions to keep re-runs predictable.
OPTIONAL=(deployment/argocd-dex-server deployment/argocd-notifications-controller)
if [ "${ARGOCD_LEAN}" = "1" ]; then
  echo "==> ARGOCD_LEAN=1: scaling dex and notifications to 0"
  kubectl -n "${NAMESPACE}" scale "${OPTIONAL[@]}" --replicas=0
else
  kubectl -n "${NAMESPACE}" scale "${OPTIONAL[@]}" --replicas=1
fi

echo "==> waiting for the rollout (timeout ${TIMEOUT} per workload)"
kubectl -n "${NAMESPACE}" wait --for=condition=Established --timeout=60s \
  crd/applications.argoproj.io crd/appprojects.argoproj.io crd/applicationsets.argoproj.io
for workload in $(kubectl -n "${NAMESPACE}" get deployment,statefulset -o name); do
  kubectl -n "${NAMESPACE}" rollout status "${workload}" --timeout="${TIMEOUT}"
done

echo
kubectl -n "${NAMESPACE}" get pods -o wide
echo
cat <<'EOF'
Argo CD is ready.

  UI:        kubectl port-forward svc/argocd-server -n argocd 18080:443
             then https://localhost:18080 (self-signed certificate), user: admin
  Password:  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
             (generated at install time and never written to the repository; delete the
              secret after changing the password: kubectl -n argocd delete secret argocd-initial-admin-secret)
  App:       kubectl apply -f gitops/argocd/application.yaml
             kubectl get applications -n argocd
EOF
