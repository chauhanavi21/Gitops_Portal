// Package main — Order Service
// A production-grade order management microservice with OpenTelemetry
// instrumentation, Prometheus metrics, health checks, and structured logging.
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.uber.org/zap"
)

// ---------- Configuration ----------

type Config struct {
	Port              string
	ServiceName       string
	OTelEndpoint      string
	LogLevel          string
	UserServiceURL    string
	PricingServiceURL string
}

func loadConfig() Config {
	return Config{
		Port:              getEnv("PORT", "8080"),
		ServiceName:       getEnv("SERVICE_NAME", "order-service"),
		OTelEndpoint:      getEnv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
		LogLevel:          getEnv("LOG_LEVEL", "info"),
		UserServiceURL:    getEnv("USER_SERVICE_URL", "http://user-service:8000"),
		PricingServiceURL: getEnv("PRICING_SERVICE_URL", "http://pricing-engine:8080"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// ---------- Metrics ----------

var (
	requestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "order_service_requests_total",
			Help: "Total number of requests by method and status",
		},
		[]string{"method", "endpoint", "status"},
	)
	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "order_service_request_duration_seconds",
			Help:    "Request duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "endpoint"},
	)
	ordersCreated = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "order_service_orders_created_total",
			Help: "Total number of orders created",
		},
	)
)

func init() {
	prometheus.MustRegister(requestsTotal, requestDuration, ordersCreated)
}

// ---------- Domain Models ----------

type Order struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Items     []Item    `json:"items"`
	Total     float64   `json:"total"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Item struct {
	ProductID string  `json:"product_id"`
	Name      string  `json:"name"`
	Quantity  int     `json:"quantity"`
	Price     float64 `json:"price"`
}

type CreateOrderRequest struct {
	UserID string `json:"user_id" binding:"required"`
	Items  []Item `json:"items" binding:"required,min=1"`
}

// ---------- In-Memory Store ----------

type OrderStore struct {
	mu     sync.RWMutex
	orders map[string]*Order
}

func NewOrderStore() *OrderStore {
	return &OrderStore{
		orders: make(map[string]*Order),
	}
}

func (s *OrderStore) Create(order *Order) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.orders[order.ID] = order
}

func (s *OrderStore) Get(id string) (*Order, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	o, ok := s.orders[id]
	return o, ok
}

func (s *OrderStore) List() []*Order {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*Order, 0, len(s.orders))
	for _, o := range s.orders {
		result = append(result, o)
	}
	return result
}

// ---------- OpenTelemetry Setup ----------

func initTracer(ctx context.Context, cfg Config) (*sdktrace.TracerProvider, error) {
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(cfg.OTelEndpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create OTLP exporter: %w", err)
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceNameKey.String(cfg.ServiceName),
			semconv.ServiceVersionKey.String("1.0.0"),
			attribute.String("environment", getEnv("ENVIRONMENT", "dev")),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	otel.SetTracerProvider(tp)
	return tp, nil
}

// ---------- Handlers ----------

type Handler struct {
	store  *OrderStore
	logger *zap.Logger
	tracer trace.Tracer
}

func NewHandler(store *OrderStore, logger *zap.Logger) *Handler {
	return &Handler{
		store:  store,
		logger: logger,
		tracer: otel.Tracer("order-service"),
	}
}

func (h *Handler) ListOrders(c *gin.Context) {
	ctx := c.Request.Context()
	_, span := h.tracer.Start(ctx, "ListOrders")
	defer span.End()

	orders := h.store.List()
	span.SetAttributes(attribute.Int("order.count", len(orders)))

	c.JSON(http.StatusOK, gin.H{
		"orders": orders,
		"count":  len(orders),
	})
}

func (h *Handler) GetOrder(c *gin.Context) {
	ctx := c.Request.Context()
	_, span := h.tracer.Start(ctx, "GetOrder")
	defer span.End()

	id := c.Param("id")
	span.SetAttributes(attribute.String("order.id", id))

	order, ok := h.store.Get(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "order not found"})
		return
	}

	c.JSON(http.StatusOK, order)
}

func (h *Handler) CreateOrder(c *gin.Context) {
	ctx := c.Request.Context()
	_, span := h.tracer.Start(ctx, "CreateOrder")
	defer span.End()

	var req CreateOrderRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		span.RecordError(err)
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Calculate total
	var total float64
	for _, item := range req.Items {
		total += item.Price * float64(item.Quantity)
	}

	order := &Order{
		ID:        uuid.New().String(),
		UserID:    req.UserID,
		Items:     req.Items,
		Total:     total,
		Status:    "pending",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	h.store.Create(order)
	ordersCreated.Inc()

	span.SetAttributes(
		attribute.String("order.id", order.ID),
		attribute.Float64("order.total", order.Total),
		attribute.Int("order.items_count", len(order.Items)),
	)

	h.logger.Info("Order created",
		zap.String("order_id", order.ID),
		zap.String("user_id", order.UserID),
		zap.Float64("total", order.Total),
	)

	c.JSON(http.StatusCreated, order)
}

// ---------- Middleware ----------

func metricsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		c.Next()
		duration := time.Since(start).Seconds()

		status := fmt.Sprintf("%d", c.Writer.Status())
		requestsTotal.WithLabelValues(c.Request.Method, c.FullPath(), status).Inc()
		requestDuration.WithLabelValues(c.Request.Method, c.FullPath()).Observe(duration)
	}
}

// ---------- Main ----------

func main() {
	cfg := loadConfig()

	// Logger
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Sync()

	// OpenTelemetry
	ctx := context.Background()
	tp, err := initTracer(ctx, cfg)
	if err != nil {
		logger.Warn("Failed to initialize tracer, continuing without tracing", zap.Error(err))
	} else {
		defer func() {
			if err := tp.Shutdown(ctx); err != nil {
				logger.Error("Error shutting down tracer", zap.Error(err))
			}
		}()
	}

	// Store and handlers
	store := NewOrderStore()
	handler := NewHandler(store, logger)

	// Seed demo data
	store.Create(&Order{
		ID:     "demo-001",
		UserID: "user-1",
		Items: []Item{
			{ProductID: "prod-1", Name: "Widget", Quantity: 2, Price: 19.99},
		},
		Total:     39.98,
		Status:    "completed",
		CreatedAt: time.Now().Add(-24 * time.Hour),
		UpdatedAt: time.Now(),
	})

	// Router
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(metricsMiddleware())
	r.Use(otelgin.Middleware(cfg.ServiceName))

	// Health endpoints
	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})
	r.GET("/readyz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ready"})
	})

	// Metrics endpoint
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// API routes
	api := r.Group("/api/v1")
	{
		api.GET("/orders", handler.ListOrders)
		api.GET("/orders/:id", handler.GetOrder)
		api.POST("/orders", handler.CreateOrder)
	}

	// Server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown
	go func() {
		logger.Info("Starting order-service", zap.String("port", cfg.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server failed", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Fatal("Server forced shutdown", zap.Error(err))
	}
	logger.Info("Server exited gracefully")
}
