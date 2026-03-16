module github.com/platform-portal/order-service

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/google/uuid v1.5.0
	github.com/prometheus/client_golang v1.18.0
	go.opentelemetry.io/otel v1.21.0
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.21.0
	go.opentelemetry.io/otel/sdk v1.21.0
	go.opentelemetry.io/otel/trace v1.21.0
	go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin v0.46.0
	go.uber.org/zap v1.26.0
	google.golang.org/grpc v1.60.1
)
