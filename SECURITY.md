# Security gates (DevSecOps)

Every push and pull request to `main` runs through the gates below, in this order. The image
build/push job `needs` all of the static jobs, and the deploy job `needs` the image job, so a single
red gate means no image is published and nothing is deployed.

| # | Gate | Tool | What it checks | Fails the pipeline when | Config |
|---|------|------|----------------|-------------------------|--------|
| 1 | Lint + unit tests | ruff, pytest | code style and the API behaviour (SQLite test DB, see `backend/tests/conftest.py`) | any lint error or failing test | `backend/ruff.toml`, `backend/pytest.ini` |
| 2 | Frontend dependency audit | npm audit | the React dependency tree against the npm advisory DB | any HIGH/CRITICAL advisory | - |
| 3 | SAST | Bandit | Python source for insecure patterns (shell injection, weak hashes, hard-coded passwords, `assert` in production code) | any finding | `security/bandit.yaml` |
| 4 | SCA | pip-audit | `backend/requirements.txt` against the PyPI advisory DB (OSV) | any known vulnerability (`--strict`) | - |
| 5 | Secret scanning | Gitleaks | working tree **and** full git history for tokens, keys, connection strings with passwords | any leak that is not explicitly allow-listed | `security/.gitleaks.toml` |
| 6 | Image scanning | Trivy | OS packages and Python/Node libraries inside **both** images, plus embedded secrets and Dockerfile misconfiguration | HIGH/CRITICAL CVE **with a fix available** (`exit-code: 1`) | `security/trivy.yaml`, `security/.trivyignore` |

Gates 1-5 run in parallel (`backend-test`, `frontend-build`, `security-static`); gate 6 runs inside
`build-scan-push` right after `docker build` and before `docker push`. A second Trivy pass produces
SARIF for the GitHub Security tab; that pass is reporting only and never fails the job.

## Why the gates are configured this way

* **`ignore-unfixed: true` for Trivy.** A CVE in Debian's `libc` with no patched package would block
  every build forever. I gate on what I can actually fix (bump the base image, bump a library). The key
  has to live under `vulnerability:` in `trivy.yaml` - at the top level Trivy silently ignores it, which
  is how the first run produced 44 HIGH findings and exit code 1.
* **Severity is limited to HIGH and CRITICAL.** MEDIUM/LOW noise would train everyone to ignore the
  table; the gate should be rare and loud.
* **The ignore list is passed via the action input** (`trivyignores:`), not a relative `ignorefile:` key
  inside the config, because the relative path does not resolve consistently between local runs and CI.
* **Gitleaks uses `fetch-depth: 0`**, so a secret that was committed and removed again is still caught.
  The project rule for `postgresql+psycopg://<user>:<password>@host` uses a non-capturing group and the
  allow-list uses `regexTarget = "line"`; with a capturing group Gitleaks reported `+psycopg` as the
  secret and the allow-list could never match the documented placeholder.
* **Placeholders are allow-listed by value and by path**, not by disabling the rule, so a real password
  pasted into the same file is still reported.
* **Both images run as non-root** (backend uid 10001, nginx-unprivileged uid 101) and the Helm chart
  drops all capabilities and sets a read-only root filesystem, which limits the blast radius of anything
  the scanners miss.

## Running every gate locally

All commands run from the repository root. Python tooling lives in a venv outside the repo so nothing
ends up in git.

```bash
python3 -m venv ~/.venvs/expense-tracker && source ~/.venvs/expense-tracker/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt   # pytest, ruff, bandit, pip-audit

# 1. lint + tests
(cd backend && ruff check app tests && pytest -v)

# 2. frontend audit
(cd frontend && npm ci && npm audit --audit-level=high)

# 3. SAST
bandit -c security/bandit.yaml -r backend/app -f txt

# 4. SCA
pip-audit -r backend/requirements.txt --strict

# 5. secrets (brew install gitleaks)
gitleaks detect --source . --config security/.gitleaks.toml --verbose

# 6. image scan (brew install trivy) - same config and exit code as CI
docker build -t expense-tracker-backend:local ./backend
docker build -t expense-tracker-frontend:local ./frontend
trivy image --config security/trivy.yaml --ignorefile security/.trivyignore --exit-code 1 expense-tracker-backend:local
trivy image --config security/trivy.yaml --ignorefile security/.trivyignore --exit-code 1 expense-tracker-frontend:local
```

## Exceptions policy

A gate is never relaxed to make a build green. The only accepted ways to get past a finding are:

1. **Fix it** - upgrade the package / base image, change the code. This is the default and what the
   gate is for.
2. **Accept the risk, in writing.** Add the id to the matching ignore list with a one-line reason, an
   owner and a re-evaluation date:
   * CVEs: `security/.trivyignore` - `CVE-2025-12345  # false positive: code path not reachable, om, re-evaluate 2026-12-01`
   * Bandit: an inline `# nosec B###  reason` on the exact line (never a global skip in `bandit.yaml`)
   * Gitleaks: a `regexes` or `paths` entry in `security/.gitleaks.toml`, only for values that are
     provably fake (placeholders, examples, local-only compose passwords)
3. Entries without a date are removed at the next review. Severity thresholds and exit codes in the
   workflow are not changed.

Anything that looks like a real credential in the history is rotated first and the commit is cleaned
afterwards - rotating is the part that actually matters.

## What Trivy scanned and what the result means (rubric M6)

Trivy scanned the two images built by the pipeline from this commit - `ghcr.io/om-malviya/expense-tracker-backend`
(Python 3.12 slim on Debian: OS packages plus every library in `requirements.txt`) and
`ghcr.io/om-malviya/expense-tracker-frontend` (nginx-unprivileged on Alpine: OS packages plus the
static bundle) - for known CVEs rated HIGH or CRITICAL, embedded secrets and Dockerfile misconfiguration.

**Result:** Both images came back clean in run
[38919569372](https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372) (commit
`ec416e2b29d120f323c1e0da197c9bed2692f9a9`): Trivy detected `debian 13.7` (87 OS packages) plus the 30
Python packages under `site-packages` in the backend image and `alpine 3.24.2` (70 OS packages) in the
frontend image, and every target in the Report Summary shows `0` vulnerabilities with no secret or
misconfiguration findings, so both gate steps exited 0 and the `docker push` steps that follow them in the
same job ran. "Clean" means no CVE with a fixed package available at scan time (2026-10-16):
`vulnerability.ignore-unfixed: true` drops the Debian/Alpine advisories that have no patch yet, and because
the trivy-action exported its default severity list the scan was in fact evaluated at every severity, not
only HIGH/CRITICAL, so the gate held with margin. The gate matters because a HIGH/CRITICAL fixable CVE
makes the step exit 1, the job goes red and nothing reaches GHCR; it re-runs on every push, so a CVE
published tomorrow is caught on the next build instead of shipping silently.

Evidence from the pipeline run: `docs/screenshots/m6-trivy-scan-output.png` (the two Report Summary
tables and the SARIF uploads) and `docs/screenshots/m6-trivy-config.png` (`security/trivy.yaml` plus the
gate steps from the workflow).
