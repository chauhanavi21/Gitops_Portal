# GitOps Workflow — Detailed Guide

## Overview

This platform uses a **pull-based GitOps model** with Argo CD. The Git repository
is the single source of truth for all Kubernetes deployments. No one pushes
directly to the cluster — Argo CD reconciles desired state from Git.

## Flow Diagram

```
Developer → Git Push → GitHub Actions CI → ECR Image → Git Manifest Update
                                                              │
                                                    Argo CD polls Git
                                                              │
                                                    K8s Desired State
                                                              │
                                                    Cluster Reconciled
```

## Environment Promotion

### Development (Auto-Sync)
- **Trigger**: Push to `main` branch
- **CI**: Full lint + test + build + Trivy scan
- **Deploy**: Argo CD auto-syncs `deployments/overlays/dev/`
- **Rollback**: Automatic via Argo CD self-heal

### Staging (Auto-Sync with Approval)
- **Trigger**: Successful dev deployment via promotion workflow
- **CI**: Integration tests + E2E tests
- **Deploy**: Argo CD auto-syncs `deployments/overlays/stage/`
- **Validation**: Smoke tests run post-deployment

### Production (Manual Sync)
- **Trigger**: Manual promotion from staging via GitHub Actions
- **Gate**: Requires PR approval + CI checks passing
- **Deploy**: Argo CD requires manual sync click (sync policy: `manual`)
- **Window**: Sync windows restrict to `Mon-Fri 08:00-17:00 UTC`
- **Rollback**: `argocd app rollback <app> <revision>`

## How Image Tags Flow

```yaml
# 1. GitHub Actions builds and pushes image
#    Image: ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/order-service:sha-abc123

# 2. Reusable workflow updates Kustomize overlay
#    File: deployments/overlays/dev/kustomization.yaml
images:
  - name: order-service
    newName: ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/order-service
    newTag: sha-abc123

# 3. Git commit triggers Argo CD sync
# 4. Argo CD applies the new manifest to the cluster
```

## Argo CD App of Apps Pattern

The platform uses an App of Apps pattern where a root Application manages
child Applications:

```
platform-apps (root)
├── platform-dev      → deployments/overlays/dev/
├── platform-stage    → deployments/overlays/stage/
└── platform-prod     → deployments/overlays/prod/
```

## Rollback Procedures

### Argo CD UI Rollback
1. Open Argo CD dashboard
2. Select the application
3. Click "History and Rollback"
4. Select the previous healthy revision
5. Click "Rollback"

### CLI Rollback
```bash
# List recent revisions
argocd app history platform-prod

# Rollback to specific revision
argocd app rollback platform-prod 42

# Or revert the Git commit and let Argo CD sync
git revert HEAD
git push origin main
```

### Emergency Rollback (kubectl)
```bash
# Direct rollback (bypasses GitOps — use only in emergencies)
kubectl rollout undo deployment/order-service -n platform

# IMPORTANT: After emergency rollback, update Git to match
# to prevent Argo CD from re-syncing the bad version
```

## Sync Policies by Environment

| Environment | Auto-Sync | Self-Heal | Auto-Prune | Sync Window |
|-------------|-----------|-----------|------------|-------------|
| dev         | ✅        | ✅        | ✅         | Always      |
| stage       | ✅        | ✅        | ✅         | Always      |
| prod        | ❌        | ❌        | ❌         | Mon-Fri 08-17 UTC |

## Branch Strategy

```
main ──────────────────────────────────────────▶
  │                                              
  ├── feature/JIRA-123 ──── PR ──── merge ──▶   
  │                                              
  └── hotfix/fix-auth ───── PR ──── merge ──▶   
```

- All changes go through PRs
- CI must pass before merge
- `main` branch always reflects desired state
- Tags trigger production promotions
