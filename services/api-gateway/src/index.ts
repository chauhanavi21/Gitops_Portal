/**
 * API Gateway — Node.js/TypeScript BFF (Backend for Frontend)
 *
 * Routes requests to downstream microservices:
 * - /api/v1/orders   → order-service (Go)
 * - /api/v1/users    → user-service (Python)
 * - /api/v1/pricing  → pricing-engine (C++)
 *
 * Includes: OpenTelemetry tracing, Prometheus metrics, CORS,
 * rate limiting, health checks, and structured logging.
 */

// Must import tracing before everything else
import './tracing';

import express, { Request, Response, NextFunction } from 'express';
import axios, { AxiosError } from 'axios';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import morgan from 'morgan';
import { createLogger, format, transports } from 'winston';
import { Registry, Counter, Histogram, collectDefaultMetrics } from 'prom-client';
import { trace, SpanStatusCode } from '@opentelemetry/api';

// ---------- Configuration ----------

const config = {
  port: parseInt(process.env.PORT || '3000', 10),
  serviceName: process.env.SERVICE_NAME || 'api-gateway',
  orderServiceUrl: process.env.ORDER_SERVICE_URL || 'http://order-service:8080',
  userServiceUrl: process.env.USER_SERVICE_URL || 'http://user-service:8000',
  pricingServiceUrl: process.env.PRICING_SERVICE_URL || 'http://pricing-engine:8080',
  logLevel: process.env.LOG_LEVEL || 'info',
};

// ---------- Logger ----------

const logger = createLogger({
  level: config.logLevel,
  format: format.combine(
    format.timestamp(),
    format.json(),
  ),
  defaultMeta: { service: config.serviceName },
  transports: [new transports.Console()],
});

// ---------- Prometheus Metrics ----------

const register = new Registry();
collectDefaultMetrics({ register });

const httpRequestsTotal = new Counter({
  name: 'api_gateway_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'path', 'status'] as const,
  registers: [register],
});

const httpRequestDuration = new Histogram({
  name: 'api_gateway_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'path'] as const,
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [register],
});

const upstreamErrors = new Counter({
  name: 'api_gateway_upstream_errors_total',
  help: 'Upstream service errors',
  labelNames: ['service'] as const,
  registers: [register],
});

// ---------- App Setup ----------

const app = express();
const tracer = trace.getTracer(config.serviceName);

// Security & utility middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json());
app.use(morgan('combined', {
  stream: { write: (msg: string) => logger.info(msg.trim()) },
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// Metrics middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestsTotal.labels(req.method, req.route?.path || req.path, String(res.statusCode)).inc();
    httpRequestDuration.labels(req.method, req.route?.path || req.path).observe(duration);
  });
  next();
});

// ---------- Health Endpoints ----------

app.get('/healthz', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', service: config.serviceName });
});

app.get('/readyz', async (_req: Request, res: Response) => {
  // Check downstream service health
  const checks = await Promise.allSettled([
    axios.get(`${config.orderServiceUrl}/healthz`, { timeout: 2000 }),
    axios.get(`${config.userServiceUrl}/healthz`, { timeout: 2000 }),
    axios.get(`${config.pricingServiceUrl}/healthz`, { timeout: 2000 }),
  ]);

  const results = {
    'order-service': checks[0].status === 'fulfilled',
    'user-service': checks[1].status === 'fulfilled',
    'pricing-engine': checks[2].status === 'fulfilled',
  };

  const allHealthy = Object.values(results).every(Boolean);
  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'ready' : 'degraded',
    dependencies: results,
  });
});

// Metrics endpoint
app.get('/metrics', async (_req: Request, res: Response) => {
  res.set('Content-Type', register.contentType);
  res.send(await register.metrics());
});

// ---------- Proxy Routes ----------

// Helper: proxy request to upstream service
async function proxyRequest(
  req: Request,
  res: Response,
  upstream: string,
  serviceName: string,
): Promise<void> {
  const span = tracer.startSpan(`proxy-${serviceName}`);
  span.setAttribute('upstream.service', serviceName);
  span.setAttribute('upstream.url', upstream);

  try {
    const url = `${upstream}${req.path}`;
    const response = await axios({
      method: req.method as any,
      url,
      data: req.body,
      params: req.query,
      headers: {
        'Content-Type': 'application/json',
        // Forward trace context headers
        ...(req.headers['traceparent'] ? { traceparent: req.headers['traceparent'] as string } : {}),
      },
      timeout: 10000,
    });

    span.setStatus({ code: SpanStatusCode.OK });
    res.status(response.status).json(response.data);
  } catch (error) {
    upstreamErrors.labels(serviceName).inc();
    span.setStatus({ code: SpanStatusCode.ERROR });

    if (error instanceof AxiosError) {
      span.recordException(error);
      logger.error(`Upstream error: ${serviceName}`, {
        status: error.response?.status,
        message: error.message,
      });

      if (error.response) {
        res.status(error.response.status).json(error.response.data);
      } else {
        res.status(503).json({
          error: `Service ${serviceName} unavailable`,
          message: error.message,
        });
      }
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  } finally {
    span.end();
  }
}

// Order Service routes
app.all('/api/v1/orders*', (req: Request, res: Response) => {
  proxyRequest(req, res, config.orderServiceUrl, 'order-service');
});

// User Service routes
app.all('/api/v1/users*', (req: Request, res: Response) => {
  proxyRequest(req, res, config.userServiceUrl, 'user-service');
});

// Pricing Engine routes
app.all('/api/v1/pricing*', (req: Request, res: Response) => {
  proxyRequest(req, res, config.pricingServiceUrl, 'pricing-engine');
});

// ---------- Aggregation endpoint ----------

app.get('/api/v1/dashboard', async (_req: Request, res: Response) => {
  const span = tracer.startSpan('dashboard-aggregation');

  try {
    const [orders, users] = await Promise.allSettled([
      axios.get(`${config.orderServiceUrl}/api/v1/orders`, { timeout: 5000 }),
      axios.get(`${config.userServiceUrl}/api/v1/users`, { timeout: 5000 }),
    ]);

    const dashboard = {
      orders: orders.status === 'fulfilled' ? orders.value.data : { error: 'unavailable' },
      users: users.status === 'fulfilled' ? users.value.data : { error: 'unavailable' },
      timestamp: new Date().toISOString(),
    };

    span.setStatus({ code: SpanStatusCode.OK });
    res.json(dashboard);
  } catch (error) {
    span.setStatus({ code: SpanStatusCode.ERROR });
    res.status(500).json({ error: 'Dashboard aggregation failed' });
  } finally {
    span.end();
  }
});

// ---------- 404 handler ----------

app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

// ---------- Error handler ----------

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  logger.error('Unhandled error', { error: err.message, stack: err.stack });
  res.status(500).json({ error: 'Internal server error' });
});

// ---------- Start Server ----------

if (require.main === module) {
  app.listen(config.port, () => {
    logger.info(`${config.serviceName} listening on port ${config.port}`);
  });
}

export { app };
