# Developer Onboarding Guide

## Welcome to the Developer Platform! 🚀

This guide will get you up and running with the platform in under 30 minutes.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| kubectl | 1.28+ | https://kubernetes.io/docs/tasks/tools/ |
| Node.js | 18+ | https://nodejs.org/ |
| Go | 1.21+ | https://go.dev/dl/ |
| Python | 3.11+ | https://www.python.org/downloads/ |
| Terraform | 1.5+ | https://developer.hashicorp.com/terraform/downloads |
| Argo CD CLI | 2.9+ | https://argo-cd.readthedocs.io/en/stable/cli_installation/ |

## Step 1: Clone the Repository

```bash
git clone https://github.com/<YOUR-ORG>/portal_gitop.git
cd portal_gitop
```

## Step 2: Start Local Development Stack

```bash
# Start all services + observability with Docker Compose
docker-compose up -d

# Verify everything is running
docker-compose ps
```

**Accessible Services**:
| Service | URL |
|---------|-----|
| API Gateway | http://localhost:3000 |
| Order Service | http://localhost:8080 |
| User Service | http://localhost:8001 |
| Pricing Engine | http://localhost:8082 |
| Platform API | http://localhost:8000 |
| Backstage Portal | http://localhost:7007 |
| Grafana | http://localhost:3001 (admin/admin) |
| Jaeger UI | http://localhost:16686 |
| Prometheus | http://localhost:9090 |

## Step 3: Explore the Backstage Portal

1. Open http://localhost:7007
2. Browse the **Software Catalog** — see all registered services
3. Check **TechDocs** — auto-generated documentation
4. Try **Create** — scaffold a new service from golden path templates

## Step 4: Make Your First Change

### Example: Add an endpoint to the Order Service

```bash
cd services/order-service

# Edit main.go — add your endpoint

# Run tests
go test ./...

# Build locally
go build -o order-service .

# Or use Docker
docker build -t order-service:dev .
```

### Example: Add a feature to the User Service

```bash
cd services/user-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest

# Run locally
uvicorn src.main:app --reload --port 8001
```

## Step 5: Create a New Service (Golden Path)

Use Backstage to scaffold a new service:

1. Go to http://localhost:7007/create
2. Choose a template (e.g., "Microservice — Go")
3. Fill in the parameters (name, team, description)
4. Backstage creates the repo with:
   - Service code with OTel instrumentation
   - Dockerfile
   - Kustomize manifests
   - CI/CD pipeline
   - Catalog entry

Or use the CLI approach:
```bash
# Copy a golden path template
cp -r backstage/templates/microservice-go/skeleton my-new-service

# Update go.mod, catalog-info.yaml, etc. with your service name
```

## Step 6: Understanding the GitOps Flow

```
You push code → CI runs → Image built → Manifest updated → Argo CD syncs → Live in cluster
```

1. **Push to `main`** — CI/CD pipeline triggers automatically
2. **CI checks**: Lint → Test → Build → Security scan (Trivy)
3. **Image pushed** to ECR with SHA tag
4. **Manifest updated** in `deployments/overlays/dev/kustomization.yaml`
5. **Argo CD** detects the change and syncs to the dev cluster
6. To promote to **staging**: Trigger the promotion workflow in GitHub Actions
7. To promote to **production**: Manual approval + PR + Argo CD manual sync

## Step 7: Observability

### View Traces
1. Open Jaeger UI (http://localhost:16686)
2. Select your service from the dropdown
3. Click "Find Traces"
4. Click on a trace to see the full request flow across services

### View Metrics
1. Open Grafana (http://localhost:3001, login: admin/admin)
2. Go to Dashboards → Platform folder
3. "Service Overview" — request rates, error rates, latency
4. "GitOps Pipeline" — Argo CD sync status, deployment frequency

### View Logs
```bash
# Real-time logs for a service
kubectl logs -f -n platform -l app=order-service

# Search logs in Grafana → Explore → Loki datasource
```

## RBAC Roles

| Role | What You Can Do |
|------|----------------|
| **Developer** | View pods/logs, port-forward, read deployments |
| **Team Owner** | Full control in your namespace, manage RBAC |
| **Platform Admin** | Full cluster access, manage infrastructure |

Your role is assigned based on your identity provider group membership.

## Troubleshooting

### "My pod won't start"
```bash
kubectl describe pod <pod-name> -n platform
kubectl logs <pod-name> -n platform
```

### "Argo CD shows OutOfSync"
```bash
argocd app get platform-dev
argocd app diff platform-dev
argocd app sync platform-dev
```

### "My CI pipeline failed"
- Check the GitHub Actions tab in your repository
- Look at the failed step's logs
- Common issues: lint errors, test failures, Trivy vulnerabilities

### "I can't access a service"
- Check NetworkPolicies: only API Gateway accepts external traffic
- Use `kubectl port-forward` to access internal services directly:
  ```bash
  kubectl port-forward svc/order-service -n platform 8080:8080
  ```

## Useful Commands

```bash
# Check all platform pods
kubectl get pods -n platform

# Check Argo CD apps
argocd app list

# Run Terraform plan for dev
cd terraform/environments/dev && terraform plan

# Run all Go tests
cd services/order-service && go test -v ./...

# Run all Python tests
cd services/user-service && pytest -v

# Build all services locally
docker-compose build
```

## Getting Help

- **#platform-engineering** Slack channel
- **Backstage TechDocs** for service documentation
- **docs/** folder for architecture and runbooks
- **Platform API** at http://localhost:8000/docs for API reference
