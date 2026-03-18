module github.com/your-org/${{ values.name }}

go ${{ values.goVersion }}

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/google/uuid v1.5.0
	github.com/prometheus/client_golang v1.18.0
	go.opentelemetry.io/otel v1.21.0
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.21.0
	go.opentelemetry.io/otel/sdk v1.21.0
	go.uber.org/zap v1.26.0
)
