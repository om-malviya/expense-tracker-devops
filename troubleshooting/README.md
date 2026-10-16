# troubleshooting/ - two faults I break on purpose, and how I find them

Both scenarios assume the healthy release is installed (`helm upgrade --install expense-tracker helm/expense-tracker -n expense-tracker -f helm/expense-tracker/values-dev.yaml`). Each broken manifest overwrites one object of that release; the fix is always the same command, because Helm is my source of truth and re-applying the chart restores whatever I changed by hand:

```bash
helm upgrade --install expense-tracker helm/expense-tracker -n expense-tracker -f helm/expense-tracker/values-dev.yaml --force-conflicts
```

`--force-conflicts` matters on Helm 4: it applies server-side, and the `kubectl apply` that broke the object made
`kubectl-client-side-apply` the *field manager* of the fields I changed. Without the flag Helm refuses to touch
them (`Apply failed with N conflicts: conflicts with "kubectl-client-side-apply"`) and marks the release `failed`;
with it Helm takes the fields back and the next revision is `deployed`. On Helm 3 the flag does not exist and the
plain command is enough.

The triage order I follow every time, before I guess at anything:

```bash
kubectl -n expense-tracker get pods -o wide                        # which pod, which state, how many restarts?
kubectl -n expense-tracker describe pod <pod> | sed -n '/Events/,$p' # events: pull errors, probe failures, config errors
kubectl -n expense-tracker logs <pod> --previous                   # what the crashed container printed
kubectl -n expense-tracker get endpoints,svc                       # does traffic have somewhere to go?
kubectl -n expense-tracker describe ingress expense-tracker        # which Service each path resolves to
kubectl -n expense-tracker get events --sort-by=.lastTimestamp | tail -20
```

---

## Scenario 1 - wrong image tag (`broken-image.yaml`) -> `ImagePullBackOff`

```bash
kubectl apply -f troubleshooting/broken-image.yaml
```

### Symptom

`kubectl get pods` shows one or two new backend pods in `ErrImagePull`, then `ImagePullBackOff`. The old pods are still `1/1 Running`, so the UI keeps working - the only visible sign is `rollout status` never finishing and a pod count that is higher than the HPA minimum.

```text
NAME                                        READY   STATUS             RESTARTS   AGE
expense-tracker-backend-6db658b5f-bw4kk     1/1     Running            0          8m    <- old ReplicaSet, kept by maxUnavailable: 0
expense-tracker-backend-7b5498f9c4-2g2bw    0/1     ImagePullBackOff   0          27s
```

### Commands

```bash
kubectl -n expense-tracker get pods -l app.kubernetes.io/component=backend
kubectl -n expense-tracker describe pod -l app.kubernetes.io/component=backend | grep -A3 -E 'Failed|BackOff'
kubectl -n expense-tracker get deploy expense-tracker-backend -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
kubectl -n expense-tracker rollout status deploy/expense-tracker-backend --timeout=30s
```

The `describe` events say it all: `Failed to pull image "ghcr.io/om-malviya/expense-tracker-backend:v9.9.9-does-not-exist": ... manifest unknown` (containerd) / `... not found` (docker runtime), or `403 Forbidden` / `unauthorized` when the package is private and no `imagePullSecret` is configured). `BackOff` means the kubelet is retrying with exponential back-off - it will never succeed on its own because the tag does not exist.

### Root cause

The Deployment references a tag that CI never pushed. My pipeline only publishes `<git-sha>` and `latest`; anything typed by hand is a guess. Because the chart uses `maxUnavailable: 0`, Kubernetes refuses to kill the healthy old pods until a new one becomes Ready, which is exactly the protection I wanted - a bad tag cannot take the API down.

### Fix

```bash
# the real fix: re-apply the chart with a tag that exists (--force-conflicts: see the top of this file)
helm upgrade --install expense-tracker helm/expense-tracker -n expense-tracker -f helm/expense-tracker/values-dev.yaml --force-conflicts
# emergency alternative while the pipeline is being fixed
kubectl -n expense-tracker set image deploy/expense-tracker-backend backend=ghcr.io/om-malviya/expense-tracker-backend:latest
kubectl -n expense-tracker rollout status deploy/expense-tracker-backend
```

Lesson: deploy the immutable tag the pipeline produced (`--set backend.image.tag=$GITHUB_SHA`), and let the CD step fail loudly if the push failed. `kubectl get pods` + `describe` finds this in under a minute.

---

## Scenario 2 - Service selector mismatch (`broken-service.yaml`) -> empty Endpoints, 503 on `/api`

```bash
kubectl apply -f troubleshooting/broken-service.yaml
```

### Symptom

Every pod is `Running` and `1/1 Ready`, the HPA is happy, there are no restarts - and still the UI shows "could not reach the API" and `curl http://expense.local/api/expenses/summary` returns `503 Service Unavailable` (Traefik) or `502 Bad Gateway` (ingress-nginx). The frontend nginx logs say `connect() failed (111: Connection refused) while connecting to upstream`.

### Commands

```bash
kubectl -n expense-tracker get endpoints expense-tracker-backend
kubectl -n expense-tracker get svc expense-tracker-backend -o jsonpath='{.spec.selector}'; echo
kubectl -n expense-tracker get pods -l app.kubernetes.io/component=backend --show-labels
curl -si -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary | head -1
```

```text
NAME                        ENDPOINTS   AGE
expense-tracker-backend     <none>      5m
{"app.kubernetes.io/component":"api","app.kubernetes.io/name":"expense-tracker"}
... LABELS: app=expense-tracker-backend,app.kubernetes.io/component=backend,...
```

### Root cause

A Service only forwards to pods whose labels satisfy *every* key in `spec.selector`. The Service asks for `app.kubernetes.io/component=api`, the pods carry `component=backend`, so the Endpoints list is empty and the ClusterIP refuses connections. Nothing is wrong with the application, which is why logs and probes look perfect - this is a wiring bug, not a code bug.

### Fix

```bash
helm upgrade --install expense-tracker helm/expense-tracker -n expense-tracker -f helm/expense-tracker/values-dev.yaml --force-conflicts
# or patch in place
kubectl -n expense-tracker patch svc expense-tracker-backend -p '{"spec":{"selector":{"app.kubernetes.io/component":"backend"}}}'
kubectl -n expense-tracker get endpoints expense-tracker-backend      # must now list <pod-ip>:8000 per pod
```

Lesson: `kubectl get endpoints` is the fastest way to separate a networking problem from an application problem. Empty endpoints with Ready pods = selector/label mismatch; empty endpoints with NotReady pods = failing readiness probe. In the chart both the Deployment and the Service take their labels from the same `_helpers.tpl` include, so this mistake cannot happen through Helm - only through a hand-edited manifest like this one.

---

## Summary

| Scenario | Symptom | First command that reveals it | Root cause | Fix |
|---|---|---|---|---|
| `broken-image.yaml` | new pods `ImagePullBackOff`, rollout stuck, old pods still serve | `kubectl describe pod` -> `manifest unknown` | tag never pushed to GHCR | `helm upgrade --install ...` (or `kubectl set image` with a real tag) |
| `broken-service.yaml` | pods Ready, `/api` returns 502/503 | `kubectl get endpoints` -> `<none>` | Service selector does not match pod labels | `helm upgrade --install ...` (or `kubectl patch svc`) |
