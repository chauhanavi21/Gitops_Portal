"""
User Service — Python/FastAPI microservice with OpenTelemetry instrumentation.

Provides user management CRUD operations with:
- REST API endpoints
- OpenTelemetry distributed tracing
- Prometheus metrics
- Health check endpoints
- Structured JSON logging
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

# ---------- Configuration ----------

SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "8000"))

# ---------- Logging ----------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"' + SERVICE_NAME + '","message":"%(message)s"}',
)
logger = logging.getLogger(SERVICE_NAME)

# ---------- OpenTelemetry Setup ----------


def setup_telemetry():
    """Initialize OpenTelemetry tracing with OTLP gRPC exporter."""
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: SERVICE_NAME,
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "dev"),
    })

    try:
        exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry initialized, exporting to {OTEL_ENDPOINT}")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")


# ---------- Prometheus Metrics ----------

REQUEST_COUNT = Counter(
    "user_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "user_service_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)
USERS_CREATED = Counter(
    "user_service_users_created_total",
    "Total users created",
)

# ---------- Domain Models ----------


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5)
    role: str = Field(default="developer", pattern="^(admin|developer|viewer)$")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str
    updated_at: str


# ---------- In-Memory Store ----------

users_db: dict[str, dict] = {}

# Seed demo data
_demo_id = "user-demo-001"
users_db[_demo_id] = {
    "id": _demo_id,
    "name": "Alice Engineer",
    "email": "alice@company.com",
    "role": "developer",
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}

# ---------- App Lifecycle ----------


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    yield
    logger.info(f"Shutting down {SERVICE_NAME}")


# ---------- FastAPI App ----------

app = FastAPI(
    title="User Service",
    description="User management microservice with OpenTelemetry",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrument with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(SERVICE_NAME)

# ---------- Middleware ----------


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response


# ---------- Health Endpoints ----------


@app.get("/healthz")
async def health():
    return {"status": "healthy"}


@app.get("/readyz")
async def ready():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")


# ---------- API Endpoints ----------


@app.get("/api/v1/users", response_model=list[User])
async def list_users():
    with tracer.start_as_current_span("list_users") as span:
        span.set_attribute("user.count", len(users_db))
        return list(users_db.values())


@app.get("/api/v1/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)
        if user_id not in users_db:
            raise HTTPException(status_code=404, detail="User not found")
        return users_db[user_id]


@app.post("/api/v1/users", response_model=User, status_code=201)
async def create_user(user_data: UserCreate):
    with tracer.start_as_current_span("create_user") as span:
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        user = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": user_data.role,
            "created_at": now,
            "updated_at": now,
        }
        users_db[user_id] = user
        USERS_CREATED.inc()

        span.set_attribute("user.id", user_id)
        span.set_attribute("user.role", user_data.role)
        logger.info(f"User created: {user_id} ({user_data.name})")

        return user


@app.put("/api/v1/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: UserUpdate):
    with tracer.start_as_current_span("update_user") as span:
        span.set_attribute("user.id", user_id)
        if user_id not in users_db:
            raise HTTPException(status_code=404, detail="User not found")

        user = users_db[user_id]
        if user_data.name is not None:
            user["name"] = user_data.name
        if user_data.email is not None:
            user["email"] = user_data.email
        if user_data.role is not None:
            user["role"] = user_data.role
        user["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"User updated: {user_id}")
        return user


@app.delete("/api/v1/users/{user_id}")
async def delete_user(user_id: str):
    with tracer.start_as_current_span("delete_user") as span:
        span.set_attribute("user.id", user_id)
        if user_id not in users_db:
            raise HTTPException(status_code=404, detail="User not found")

        del users_db[user_id]
        logger.info(f"User deleted: {user_id}")
        return {"message": "User deleted"}


# ---------- Entrypoint ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
