# gitops/ - Argo CD (pull-based deployment from Git)

GitOps here means: **the `main` branch of this repository is the desired state of the cluster, and a
controller inside the cluster keeps the cluster equal to it.** Nobody runs `helm upgrade` or
`kubectl apply` against the app namespace; to change what runs, I change a file in Git.

The controller is [Argo CD](https://argo-cd.readthedocs.io/). One `Application` object
(`argocd/application.yaml`) tells it:

| Field | Value | Meaning |
|---|---|---|
| source | `https://github.com/om-malviya/expense-tracker-devops.git`, `main`, `helm/expense-tracker` | the same Helm chart CI deploys |
| values | `values-gitops.yaml` (on top of the chart's `values.yaml`) | 1 backend + 1 frontend replica, no HPA, ServiceMonitor on, host `gitops.expense.local`, images pinned to a full git SHA |
| destination | in-cluster, namespace `expense-tracker-gitops` (release `expense-tracker-gitops`) | a second copy next to the CI/manual release in `expense-tracker`, which Argo CD does not touch |
| sync policy | automated, `prune: true`, `selfHeal: true`, `CreateNamespace=true`, `ServerSideApply=true` | Git changes are applied without a click, deleted manifests are removed, manual drift is reverted |
| namespace metadata | `pod-security.kubernetes.io/enforce: restricted` (+ warn) | the same Pod Security labels as `k8s/namespace.yaml`, set by Argo CD when it creates the namespace |

## Flow

```text
  developer                  GitHub                         k3s cluster
 ───────────            ─────────────────            ────────────────────────────────────────────────
  edit values-gitops.yaml
  (e.g. replicaCount,      main @ <sha>             argocd namespace
   image tag)                   │                    ┌──────────────────────────────────────────────┐
     │  git commit              │                    │ repo-server: git fetch main, helm template   │
     └──── git push ───────────►│◄──── poll ─────────│   helm/expense-tracker -f values-gitops.yaml │
                                │   (every ~3 min,   │ application-controller: diff rendered        │
                                │    or "Refresh")   │   manifests vs. live objects                 │
                                                     │   OutOfSync -> sync (server-side apply)      │
                                                     └───────────────────────┬──────────────────────┘
                                                                             │ apply / prune
                                                                             ▼
                                                     namespace expense-tracker-gitops
                                                     Deployments backend + frontend, StatefulSet postgres,
                                                     Services, ConfigMap, Secret, Ingress, ServiceMonitor
                                                                             ▲
                                     kubectl scale / edit / delete ──────────┘ drift -> selfHeal puts Git back
```

### How this differs from the CI `helm upgrade` path

| | CI path (`.github/workflows/ci-cd.yml`, job `deploy`) | GitOps path (this folder) |
|---|---|---|
| Direction | **push**: the GitHub runner connects to the cluster | **pull**: Argo CD inside the cluster fetches from GitHub |
| Credentials | a kubeconfig stored as the `KUBE_CONFIG_DATA` repository secret | none outside the cluster (public repo, read-only clone) |
| Trigger | each pipeline run on `main` | every commit on `main` that changes the rendered manifests |
| Image tag | `--set backend.image.tag=$GITHUB_SHA` on the command line, never stored in Git | `backend.image.tag` / `frontend.image.tag` in `values-gitops.yaml`, so the running version is a line in Git |
| Drift | a manual `kubectl scale` stays until the next pipeline run | reverted by the controller (`selfHeal`), normally within seconds - see the back-off note in the demo |
| Rollback | re-run an old pipeline or `helm rollback` | `git revert` the commit |
| State | Helm release secrets in the namespace | the rendered chart in Git; no Helm release object (Argo CD runs `helm template` and applies the output) |

The CI pipeline still builds, scans and pushes the images; for this environment its last step
would be a commit (or PR) that bumps the two tags in `values-gitops.yaml` instead of a `helm upgrade`.

### Why `values-gitops.yaml` is standalone

It is layered on the chart's `values.yaml` only, so the Application has a single value file and the
whole environment is visible in one file. It also renders identically when layered after
`values-dev.yaml`, because it sets again every key from that file that matters here:

```bash
helm lint helm/expense-tracker -f helm/expense-tracker/values-gitops.yaml
helm lint helm/expense-tracker -f helm/expense-tracker/values-dev.yaml -f helm/expense-tracker/values-gitops.yaml
diff <(helm template expense-tracker-gitops helm/expense-tracker -n expense-tracker-gitops -f helm/expense-tracker/values-gitops.yaml) \
     <(helm template expense-tracker-gitops helm/expense-tracker -n expense-tracker-gitops -f helm/expense-tracker/values-dev.yaml -f helm/expense-tracker/values-gitops.yaml) \
  && echo identical
```

The HPA is off in this environment on purpose: with an HPA, the autoscaler owns `spec.replicas`, so a
`kubectl scale` would not be drift that Argo CD can show and undo.

## Setup

```bash
# 1. Argo CD (namespace argocd, upstream "stable" manifests; idempotent). ARGOCD_LEAN=1 scales dex
#    (SSO) and the notifications controller to 0 - neither is used here, and the single-node
#    Colima VM also runs kube-prometheus-stack. That is how it runs on my cluster.
ARGOCD_LEAN=1 gitops/argocd/install.sh

# 2. Register the application
kubectl apply -f gitops/argocd/application.yaml
kubectl get applications -n argocd            # SYNC STATUS Synced, HEALTH STATUS Healthy

# 3. UI
kubectl port-forward svc/argocd-server -n argocd 18080:443
#    https://localhost:18080  (self-signed certificate), user admin, password:
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

# 4. The app through Traefik (Host-header routing)
curl -s -H 'Host: gitops.expense.local' http://localhost/api/expenses/summary
#    or add "127.0.0.1 gitops.expense.local" to /etc/hosts and open http://gitops.expense.local/
```

The `kube-prometheus-stack` Prometheus in `monitoring` selects every ServiceMonitor, so the backend of
this copy shows up as a second target (`namespace="expense-tracker-gitops"`).

## Demo

1. **Synced / Healthy.** Open the UI, show the `expense-tracker-gitops` tile (Synced, Healthy, the commit
   SHA it is on) and the resource tree: Deployments -> ReplicaSets -> Pods, StatefulSet, Services,
   Ingress, ServiceMonitor. In the terminal:
   ```bash
   kubectl get applications -n argocd
   kubectl get all -n expense-tracker-gitops
   ```
2. **Change Git, not the cluster.** Edit `helm/expense-tracker/values-gitops.yaml`, set
   `frontend.replicaCount: 2` (or `backend.replicaCount`), then
   ```bash
   git commit -am "Scale the GitOps frontend to 2 replicas" && git push
   ```
   Argo CD polls GitHub about every 3 minutes; click **Refresh** in the UI (or run the line below) to
   fetch now. The app goes OutOfSync, syncs automatically and a second frontend pod appears; the tile
   shows the new commit SHA.
   ```bash
   kubectl -n argocd annotate application expense-tracker-gitops argocd.argoproj.io/refresh=normal --overwrite
   kubectl get pods -n expense-tracker-gitops -w
   ```
3. **Self-heal.** Change the cluster by hand and watch Argo CD put Git back:
   ```bash
   kubectl -n expense-tracker-gitops delete pod -l app.kubernetes.io/component=backend   # ReplicaSet replaces it
   kubectl -n expense-tracker-gitops scale deploy expense-tracker-gitops-backend --replicas=3
   kubectl -n expense-tracker-gitops get deploy expense-tracker-gitops-backend -w        # 3 -> back to 1 in seconds
   ```
   The scale is drift (live `replicas: 3`, Git says 1); with `selfHeal: true` the controller re-applies
   the Git version. Deleting a Service or the Ingress is recreated the same way.

   Timing: Argo CD 3.x backs off when it keeps healing the *same* commit, so a hand edit is never fought
   in a tight loop. The first heal of a commit is immediate; each further heal of the same commit waits
   longer - 2 s, 6 s, 18 s, ... (x3), capped at 5 minutes, counted from the end of the previous sync
   (controller flags `--self-heal-backoff-*`). Once the cap is reached, drift is still undone, but up to
   5 minutes later. For a demo, scale once per commit, or push a commit first, which resets the counter.
   I hit exactly this while testing: after a few heals the next one came 5 minutes after the last sync,
   and a scale done more than 5 minutes after the last sync was reverted at once.
4. **Rollback** is `git revert <sha> && git push`, followed by the same automatic sync.

## Tear-down

```bash
kubectl delete -f gitops/argocd/application.yaml   # the finalizer deletes everything the app created
kubectl delete namespace expense-tracker-gitops    # namespace (and the Postgres PVC) last
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl delete namespace argocd
```

## Notes from running it

- **Server-side diff.** The Application carries `argocd.argoproj.io/compare-options: ServerSideDiff=true`.
  Without it, Argo CD's client-side diff compares the rendered Postgres StatefulSet with the live one,
  sees the fields the API server defaults inside `spec.volumeClaimTemplates`, reports the StatefulSet
  as OutOfSync forever and re-syncs it every few seconds. With the API server computing the diff
  (a dry-run server-side apply, matching `ServerSideApply=true`), the app settles at Synced.
- **Images on a slow link.** The first install hit `ImagePullBackOff` (TLS handshake timeouts to quay.io);
  `docker pull quay.io/argoproj/argocd:<version>` against Colima's Docker daemon (the runtime k3s uses) and
  deleting the stuck pods fixed it.
  Re-running `install.sh` afterwards is harmless.

## Evidence

`docs/screenshots/m10-argocd-*`: `m10-argocd-install` (a run of `install.sh` and the Argo CD pods Running),
`m10-argocd-app-synced` (`kubectl get applications`, the key lines of `kubectl describe application` -
source path and value file, destination, sync policy, health, synced revision -, `kubectl get all` in the
namespace, its Pod Security labels and a request through Traefik), `m10-argocd-self-heal` (a backend pod
deleted and replaced by its ReplicaSet, then `kubectl scale --replicas=3` reverted to Git's 1 by an
automated sync, polled every second with timestamps, plus the Application's last operation and events),
`m10-argocd-ui.png` (the application's resource tree, Synced + Healthy) and `m10-argocd-ui-apps.png`
(the application list).

All of them show the committed Application `expense-tracker-gitops` (`argocd/application.yaml`), which
syncs `helm/expense-tracker` + `values-gitops.yaml` from `main` on GitHub (commit `fa508af` at capture
time). Before `values-gitops.yaml` was pushed, the same Application showed `Unknown` with
"values-gitops.yaml: no such file or directory" - Argo CD only deploys what is in Git.
