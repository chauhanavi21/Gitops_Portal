package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupTestRouter() (*gin.Engine, *Handler) {
	gin.SetMode(gin.TestMode)
	store := NewOrderStore()
	handler := NewHandler(store, nil)

	r := gin.New()
	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})
	r.GET("/api/v1/orders", handler.ListOrders)
	r.GET("/api/v1/orders/:id", handler.GetOrder)
	r.POST("/api/v1/orders", handler.CreateOrder)

	return r, handler
}

func TestHealthCheck(t *testing.T) {
	r, _ := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/healthz", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
}

func TestCreateOrder(t *testing.T) {
	r, _ := setupTestRouter()

	body := CreateOrderRequest{
		UserID: "user-1",
		Items: []Item{
			{ProductID: "prod-1", Name: "Widget", Quantity: 2, Price: 10.0},
		},
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/orders", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var order Order
	json.Unmarshal(w.Body.Bytes(), &order)

	if order.UserID != "user-1" {
		t.Errorf("Expected user_id 'user-1', got '%s'", order.UserID)
	}
	if order.Total != 20.0 {
		t.Errorf("Expected total 20.0, got %f", order.Total)
	}
}

func TestListOrders(t *testing.T) {
	r, _ := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/orders", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
}

func TestGetOrderNotFound(t *testing.T) {
	r, _ := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/orders/nonexistent", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}
