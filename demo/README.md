# Demo – presentation deck and video

Student: Om Malviya | Enrollment No: 24BCS10448

| File | Contents |
|---|---|
| [`presentation.pptx`](presentation.pptx) | Slide deck (11 slides) with speaker notes: project overview, tech stack, architecture, CI/CD flow, security, Terraform infrastructure, Kubernetes + Helm, Argo CD GitOps, observability, key learnings |
| [`presentation.pdf`](presentation.pdf) | The same deck exported to PDF |
| `expense-tracker-demo.mp4` | The recorded presentation: the slides first, then the live walkthrough |

## Order of the video

The walkthrough follows the order required in [`../SUBMISSION.md`](../SUBMISSION.md):

1. Presentation slides – what I built and the architecture
2. Codebase – folder structure and key files
3. CI/CD – a push to `main` and the GitHub Actions run end to end
4. Terraform – `terraform plan` / `apply` output and the AWS Console view of the VPC and EKS cluster
5. Argo CD – the synced application and the GitOps flow
6. Kubernetes – `kubectl get pods`, services and ingress
7. Prometheus – the Targets page with the application `UP`
8. Grafana – the live dashboard with application metrics
