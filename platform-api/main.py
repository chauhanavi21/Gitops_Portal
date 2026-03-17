"""
Platform Control Plane API — FastAPI service managing:
- Service metadata and registration
- Template lifecycle management
- Audit logging for all platform operations
- RBAC enforcement

This is the backend brain of the Backstage portal, providing
data persistence and business logic for platform operations.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest
from starlette.responses import Response

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# ---------- Configuration ----------

SERVICE_NAME = os.getenv("SERVICE_NAME", "platform-api")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
PORT = int(os.getenv("PORT", "8000"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(SERVICE_NAME)

# ---------- Telemetry ----------


def setup_telemetry():
    try:
        resource = Resource.create({"service.name": SERVICE_NAME, "service.version": "1.0.0"})
        exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except Exception as e:
        logger.warning(f"Telemetry init failed: {e}")


# ---------- Metrics ----------

AUDIT_EVENTS = Counter("platform_api_audit_events_total", "Total audit events", ["action", "actor_role"])
API_REQUESTS = Counter("platform_api_requests_total", "API requests", ["method", "endpoint"])

# ---------- Models ----------


class Role(str, Enum):
    PLATFORM_ADMIN = "platform-admin"
    TEAM_OWNER = "team-owner"
    DEVELOPER = "developer"


class ServiceStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PROVISIONING = "provisioning"


class ServiceRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    language: str = Field(default="unknown")
    owner_team: str = Field(...)
    repo_url: str = Field(default="")
    environment: str = Field(default="dev")
    status: ServiceStatus = ServiceStatus.PROVISIONING


class ServiceResponse(BaseModel):
    id: str
    name: str
    description: str
    language: str
    owner_team: str
    repo_url: str
    environment: str
    status: str
    created_at: str
    updated_at: str
    created_by: str


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    language: str
    version: str
    parameters: list[str]
    created_at: str


class AuditEntry(BaseModel):
    id: str
    timestamp: str
    actor: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    details: dict


# ---------- In-Memory Stores ----------

services_db: dict[str, dict] = {}
audit_log: list[dict] = []

# Seed templates (read-only, defined by platform team)
templates_db: dict[str, dict] = {
    "microservice-go": {
        "id": "microservice-go",
        "name": "Go Microservice",
        "description": "Production-ready Go microservice with gRPC, REST, OTel, CI/CD",
        "language": "go",
        "version": "1.0.0",
        "parameters": ["service_name", "owner_team", "description", "port"],
        "created_at": "2024-01-01T00:00:00Z",
    },
    "microservice-python": {
        "id": "microservice-python",
        "name": "Python Microservice",
        "description": "FastAPI microservice with OTel, Prometheus, tests",
        "language": "python",
        "version": "1.0.0",
        "parameters": ["service_name", "owner_team", "description", "port"],
        "created_at": "2024-01-01T00:00:00Z",
    },
    "microservice-node": {
        "id": "microservice-node",
        "name": "Node.js Microservice",
        "description": "Express/TypeScript microservice with OTel, metrics",
        "language": "nodejs",
        "version": "1.0.0",
        "parameters": ["service_name", "owner_team", "description", "port"],
        "created_at": "2024-01-01T00:00:00Z",
    },
    "microservice-cpp": {
        "id": "microservice-cpp",
        "name": "C++ Microservice",
        "description": "High-performance C++ service with embedded HTTP server",
        "language": "cpp",
        "version": "1.0.0",
        "parameters": ["service_name", "owner_team", "description", "port"],
        "created_at": "2024-01-01T00:00:00Z",
    },
}

# Seed demo service
_demo = {
    "id": "svc-demo-001",
    "name": "order-service",
    "description": "Order management microservice",
    "language": "go",
    "owner_team": "platform-engineering",
    "repo_url": "https://github.com/YOUR_ORG/portal-gitop",
    "environment": "dev",
    "status": "active",
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
    "created_by": "platform-admin",
}
services_db[_demo["id"]] = _demo


# ---------- RBAC Helper ----------


def get_actor_role(x_user_role: str = Header(default="developer")) -> str:
    """Extract role from header. Production: validate JWT / OIDC token."""
    if x_user_role not in [r.value for r in Role]:
        raise HTTPException(status_code=403, detail=f"Invalid role: {x_user_role}")
    return x_user_role


def require_admin(role: str = Depends(get_actor_role)):
    if role != Role.PLATFORM_ADMIN:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return role


def record_audit(actor: str, role: str, action: str, resource_type: str, resource_id: str, details: dict = None):
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "actor": actor,
        "actor_role": role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
    }
    audit_log.append(entry)
    AUDIT_EVENTS.labels(action=action, actor_role=role).inc()
    logger.info(f"AUDIT: {action} on {resource_type}/{resource_id} by {actor} ({role})")


# ---------- App Lifecycle ----------


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    logger.info(f"Starting {SERVICE_NAME}")
    yield
    logger.info(f"Shutting down {SERVICE_NAME}")


# ---------- FastAPI App ----------

app = FastAPI(
    title="Platform Control Plane API",
    description="Manages service registry, templates, and audit logs for the developer platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(SERVICE_NAME)

# ---------- Health ----------


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")


# ---------- Services API ----------


@app.get("/api/v1/services", response_model=list[ServiceResponse])
async def list_services(
    environment: Optional[str] = None,
    status: Optional[str] = None,
    role: str = Depends(get_actor_role),
):
    results = list(services_db.values())
    if environment:
        results = [s for s in results if s["environment"] == environment]
    if status:
        results = [s for s in results if s["status"] == status]
    return results


@app.get("/api/v1/services/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: str, role: str = Depends(get_actor_role)):
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    return services_db[service_id]


@app.post("/api/v1/services", response_model=ServiceResponse, status_code=201)
async def register_service(
    svc: ServiceRegistration,
    request: Request,
    role: str = Depends(get_actor_role),
    x_user_name: str = Header(default="unknown"),
):
    svc_id = f"svc-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    service = {
        "id": svc_id,
        **svc.model_dump(),
        "status": svc.status.value,
        "created_at": now,
        "updated_at": now,
        "created_by": x_user_name,
    }
    services_db[svc_id] = service

    record_audit(x_user_name, role, "service.register", "service", svc_id, {"name": svc.name})
    logger.info(f"Service registered: {svc.name} ({svc_id})")

    return service


@app.delete("/api/v1/services/{service_id}")
async def deregister_service(
    service_id: str,
    role: str = Depends(require_admin),
    x_user_name: str = Header(default="unknown"),
):
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")

    svc = services_db.pop(service_id)
    record_audit(x_user_name, role, "service.deregister", "service", service_id, {"name": svc["name"]})
    return {"message": f"Service {service_id} deregistered"}


# ---------- Templates API ----------


@app.get("/api/v1/templates", response_model=list[TemplateInfo])
async def list_templates():
    return list(templates_db.values())


@app.get("/api/v1/templates/{template_id}", response_model=TemplateInfo)
async def get_template(template_id: str):
    if template_id not in templates_db:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates_db[template_id]


@app.post("/api/v1/templates/{template_id}/scaffold", status_code=202)
async def scaffold_from_template(
    template_id: str,
    params: dict,
    role: str = Depends(get_actor_role),
    x_user_name: str = Header(default="unknown"),
):
    """
    Trigger scaffolding a new service from a golden path template.
    In production, this would:
    1. Call Backstage Scaffolder API to create the repo
    2. Register the new service in the catalog
    3. Create the deployment manifests
    4. Trigger initial CI build
    """
    if template_id not in templates_db:
        raise HTTPException(status_code=404, detail="Template not found")

    scaffold_id = f"scaffold-{uuid.uuid4().hex[:8]}"
    record_audit(
        x_user_name, role, "template.scaffold",
        "template", template_id,
        {"scaffold_id": scaffold_id, "params": params},
    )

    # TODO: EXTERNAL DEPENDENCY — Backstage Scaffolder API
    # In production, call: POST {backstage_url}/api/scaffolder/v2/tasks
    # with the template parameters to actually create the repo

    return {
        "scaffold_id": scaffold_id,
        "template_id": template_id,
        "status": "accepted",
        "message": "Scaffolding initiated. Service will be registered upon completion.",
    }


# ---------- Audit API ----------


@app.get("/api/v1/audit", response_model=list[AuditEntry])
async def list_audit_logs(
    action: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    role: str = Depends(get_actor_role),
):
    results = audit_log.copy()
    if action:
        results = [e for e in results if e["action"] == action]
    if actor:
        results = [e for e in results if e["actor"] == actor]
    return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]


# ---------- Platform Stats ----------


@app.get("/api/v1/stats")
async def platform_stats():
    return {
        "total_services": len(services_db),
        "total_templates": len(templates_db),
        "total_audit_events": len(audit_log),
        "services_by_language": _count_by(services_db.values(), "language"),
        "services_by_environment": _count_by(services_db.values(), "environment"),
        "services_by_status": _count_by(services_db.values(), "status"),
    }


def _count_by(items, field):
    counts = {}
    for item in items:
        val = item.get(field, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


# ---------- Entrypoint ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
