/**
 * OpenTelemetry instrumentation bootstrap — MUST be imported before any other module.
 * Sets up tracing and exports spans to the OpenTelemetry Collector via OTLP/gRPC.
 */

import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

const SERVICE_NAME = process.env.SERVICE_NAME || 'api-gateway';
const OTEL_ENDPOINT = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'localhost:4317';

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
    environment: process.env.ENVIRONMENT || 'dev',
  }),
  traceExporter: new OTLPTraceExporter({
    url: OTEL_ENDPOINT,
  }),
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
  ],
});

try {
  sdk.start();
  console.log(`[otel] Tracing initialized, exporting to ${OTEL_ENDPOINT}`);
} catch (err) {
  console.warn('[otel] Failed to initialize tracing:', err);
}

// Graceful shutdown
process.on('SIGTERM', () => {
  sdk.shutdown().then(
    () => console.log('[otel] SDK shut down'),
    (err) => console.error('[otel] Shutdown error', err),
  );
});

export { sdk };
