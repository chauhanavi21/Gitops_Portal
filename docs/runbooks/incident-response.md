# Incident Runbooks

## Table of Contents

1. [Service Down](#1-service-down)
2. [High Error Rate](#2-high-error-rate)
3. [High Latency](#3-high-latency)
4. [Pod Crash Loop](#4-pod-crash-loop)
5. [Argo CD Out of Sync](#5-argo-cd-out-of-sync)
6. [Node Not Ready](#6-node-not-ready)
7. [SLO Budget Burn](#7-slo-budget-burn)
8. [Production Rollback](#8-production-rollback)

---

## 1. Service Down

**Alert**: `ServiceDown` — service unreachable for > 2 minutes

**Severity**: Critical

**Triage Steps**:

```bash
# 1. Check pod status
kubectl get pods -n platform -l app=<service-name>

# 2. Check recent events
kubectl describe pod <pod-name> -n platform

# 3. Check logs
kubectl logs <pod-name> -n platform --tail=100

# 4. Check if deployment exists and is scaled
kubectl get deployment <service-name> -n platform

# 5. Check node status
kubectl get nodes
kubectl describe node <node-name>
```

**Common Causes & Fixes**:

| Cause | Fix |
|-------|-----|
| OOMKilled | Increase memory limits in Kustomize overlay |
| ImagePullBackOff | Check ECR image tag, verify IRSA permissions |
| CrashLoopBackOff | Check application logs, recent deployment changes |
| Pending (no nodes) | Check Karpenter/ASG scaling, node resource usage |
| Readiness probe failed | Check probe endpoint, increase `initialDelaySeconds` |

**Escalation**: If not resolved in 15 minutes → Page platform-admin on-call

---

## 2. High Error Rate

**Alert**: `HighErrorRate` — > 5% 5xx responses over 5 minutes

**Severity**: Warning (escalates to Critical at > 15%)

**Triage Steps**:

```bash
# 1. Identify which endpoints are failing
# Check Grafana dashboard: Platform Services → Error Rate panel

# 2. Check application logs for errors
kubectl logs -n platform -l app=<service-name> --tail=200 | grep -i error

# 3. Check if recent deployment happened
argocd app history platform-<env>

# 4. Check downstream dependencies
kubectl exec -n platform <api-gateway-pod> -- curl -s http://order-service:8080/healthz
kubectl exec -n platform <api-gateway-pod> -- curl -s http://user-service:8000/healthz
kubectl exec -n platform <api-gateway-pod> -- curl -s http://pricing-engine:8080/healthz

# 5. Check Jaeger for error traces
# Open Jaeger UI → Search by service → Filter by error=true
```

**Common Causes & Fixes**:

| Cause | Fix |
|-------|-----|
| Bad deployment | Rollback: `argocd app rollback platform-<env> <revision>` |
| Downstream service down | Restart downstream service, check its runbook |
| Database connection pool exhausted | Scale DB or increase pool size |
| Rate limiting triggered | Check rate limit config in api-gateway |

---

## 3. High Latency

**Alert**: `HighP99Latency` — P99 > 2 seconds

**Triage Steps**:

```bash
# 1. Check Grafana latency dashboard for pattern
# Is it gradual or sudden?

# 2. Check resource utilization
kubectl top pods -n platform

# 3. Look for slow traces in Jaeger
# Sort by duration, look for bottleneck spans

# 4. Check HPA status (is it scaling?)
kubectl get hpa -n platform

# 5. Check for resource throttling
kubectl describe pod <pod-name> -n platform | grep -A5 "Resources"
```

**Common Causes & Fixes**:

| Cause | Fix |
|-------|-----|
| CPU throttling | Increase CPU limits or add replicas |
| Slow downstream calls | Check inter-service latency in Jaeger |
| Database slow queries | Check DB metrics, add indexes |
| Memory pressure (GC) | Increase memory limits, tune GC |
| Network policy blocking | Verify NetworkPolicy allows the traffic path |

---

## 4. Pod Crash Loop

**Alert**: `PodRestartLoop` — > 5 restarts in 1 hour

**Triage Steps**:

```bash
# 1. Check pod status and restart count
kubectl get pods -n platform -l app=<service-name>

# 2. Check previous container logs (crash logs)
kubectl logs <pod-name> -n platform --previous --tail=100

# 3. Check pod events
kubectl describe pod <pod-name> -n platform

# 4. Check if it's OOMKilled
kubectl get pod <pod-name> -n platform -o jsonpath='{.status.containerStatuses[0].lastState}'

# 5. Check recent config/secret changes
kubectl get events -n platform --sort-by='.metadata.creationTimestamp' | tail -20
```

**Recovery**:

```bash
# If caused by bad config:
kubectl rollout undo deployment/<service-name> -n platform

# If caused by bad image:
# Revert the image tag in Git and let Argo CD sync

# If caused by resource limits:
# Update limits in deployments/overlays/<env>/kustomization.yaml
```

---

## 5. Argo CD Out of Sync

**Alert**: `ArgoCDAppOutOfSync` — app not synced for > 15 minutes

**Triage Steps**:

```bash
# 1. Check sync status in Argo CD
argocd app get platform-<env>

# 2. Check for sync errors
argocd app get platform-<env> --show-operation

# 3. Check if there are sync windows blocking
argocd proj windows list platform-services

# 4. Try manual sync with dry-run
argocd app sync platform-<env> --dry-run

# 5. Check if Git repo is accessible
argocd repo get https://github.com/<org>/<repo>.git
```

**Common Causes & Fixes**:

| Cause | Fix |
|-------|-----|
| Sync window blocking | Wait for window or override for emergency |
| Resource validation error | Fix the manifest in Git |
| Permission denied | Check Argo CD RBAC and K8s RBAC |
| Git auth failure | Rotate Sealed Secret for repo credentials |
| Resource already exists | Use `argocd app sync --force` |

---

## 6. Node Not Ready

**Triage Steps**:

```bash
# 1. Check node status
kubectl get nodes
kubectl describe node <node-name>

# 2. Check node conditions
kubectl get node <node-name> -o jsonpath='{.status.conditions}' | jq .

# 3. Check if Karpenter is provisioning replacements
kubectl get provisioners
kubectl get machines

# 4. Check AWS console for EC2 instance status
# Look for instance health checks, spot interruptions

# 5. Cordon and drain if needed
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

---

## 7. SLO Budget Burn

**Alert**: `SLOBurnRateHigh` — error budget depleting at 14.4x rate

**This is the most critical alert — act immediately.**

**Triage Steps**:

1. **Identify the service** from the alert label
2. **Check the error rate dashboard** — what's the actual error %?
3. **Check recent changes** — was there a deployment in the last hour?
4. **If recent deployment**: Roll back immediately
5. **If no recent deployment**: Follow the [High Error Rate](#2-high-error-rate) runbook
6. **Notify stakeholders** — SLO breach likely if not resolved

**SLO Budget Calculation**:
- **SLO**: 99.9% availability (monthly)
- **Error budget**: 43.2 minutes of downtime per month
- **14.4x burn rate**: Budget exhausted in < 1 day
- **6x burn rate**: Budget exhausted in < 5 days

---

## 8. Production Rollback

**Step-by-step production rollback procedure**:

```bash
# 1. Confirm the issue (check dashboards, logs, alerts)

# 2. Get the last known good revision
argocd app history platform-prod

# 3. Rollback via Argo CD
argocd app rollback platform-prod <good-revision>

# 4. Verify the rollback
argocd app get platform-prod
kubectl rollout status deployment/<service-name> -n platform

# 5. Verify health endpoints
kubectl exec -n platform <pod> -- curl -s localhost:<port>/healthz

# 6. Update Git to match rolled-back state
git revert <bad-commit-sha>
git push origin main

# 7. Create incident ticket and post-mortem
```

**If Argo CD is unavailable**:

```bash
# Emergency kubectl rollback
kubectl rollout undo deployment/<service-name> -n platform

# Pause Argo CD auto-sync (if applicable) to prevent re-sync
argocd app set platform-<env> --sync-policy none
```

---

## Escalation Matrix

| Severity | Response Time | Escalation After | Contact |
|----------|--------------|-------------------|---------|
| Critical | 5 min | 15 min | Platform Admin on-call |
| Warning  | 15 min | 1 hour | Team Owner |
| Info     | Next business day | — | Team channel |

## Communication Templates

**Incident Start**:
```
🔴 INCIDENT: [Service] [Issue]
Impact: [Customer-facing impact]
Status: Investigating
ETA: TBD
```

**Incident Update**:
```
🟡 UPDATE: [Service] [Issue]
Root Cause: [Identified/Investigating]
Mitigation: [Actions taken]
ETA: [Time estimate]
```

**Incident Resolved**:
```
🟢 RESOLVED: [Service] [Issue]
Duration: [Time]
Root Cause: [Summary]
Post-mortem: [Link]
```
