/**
 * Pricing Engine — High-performance C++ microservice
 *
 * Provides real-time price calculation, discount computation,
 * and currency conversion with sub-millisecond latency.
 *
 * Features:
 * - Embedded HTTP server (no external deps for demo simplicity)
 * - Prometheus-compatible metrics endpoint
 * - Health check endpoints
 * - JSON request/response
 * - Thread-safe pricing calculations
 */

#include <iostream>
#include <string>
#include <cstdlib>
#include "http_server.h"
#include "pricing_engine.h"
#include "metrics.h"

int main() {
    const int port = std::atoi(
        std::getenv("PORT") ? std::getenv("PORT") : "8080"
    );
    const std::string service_name =
        std::getenv("SERVICE_NAME") ? std::getenv("SERVICE_NAME") : "pricing-engine";

    std::cout << "{\"timestamp\":\"" << get_timestamp()
              << "\",\"level\":\"info\",\"service\":\"" << service_name
              << "\",\"message\":\"Starting " << service_name
              << " on port " << port << "\"}" << std::endl;

    PricingEngine engine;
    Metrics metrics(service_name);

    HttpServer server(port);

    // Health endpoints
    server.route("GET", "/healthz", [](const HttpRequest& req) -> HttpResponse {
        return {200, "{\"status\":\"healthy\"}"};
    });

    server.route("GET", "/readyz", [](const HttpRequest& req) -> HttpResponse {
        return {200, "{\"status\":\"ready\"}"};
    });

    // Metrics endpoint
    server.route("GET", "/metrics", [&metrics](const HttpRequest& req) -> HttpResponse {
        return {200, metrics.serialize(), "text/plain"};
    });

    // Calculate price
    server.route("POST", "/api/v1/pricing/calculate", [&engine, &metrics](const HttpRequest& req) -> HttpResponse {
        metrics.increment_requests("calculate");
        auto start = std::chrono::high_resolution_clock::now();

        try {
            auto result = engine.calculate_price(req.body);
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::high_resolution_clock::now() - start
            ).count();
            metrics.observe_duration("calculate", duration / 1e6);

            return {200, result};
        } catch (const std::exception& e) {
            metrics.increment_errors("calculate");
            return {400, std::string("{\"error\":\"") + e.what() + "\"}"};
        }
    });

    // Get discount
    server.route("POST", "/api/v1/pricing/discount", [&engine, &metrics](const HttpRequest& req) -> HttpResponse {
        metrics.increment_requests("discount");
        auto start = std::chrono::high_resolution_clock::now();

        try {
            auto result = engine.calculate_discount(req.body);
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::high_resolution_clock::now() - start
            ).count();
            metrics.observe_duration("discount", duration / 1e6);

            return {200, result};
        } catch (const std::exception& e) {
            metrics.increment_errors("discount");
            return {400, std::string("{\"error\":\"") + e.what() + "\"}"};
        }
    });

    // Currency conversion
    server.route("POST", "/api/v1/pricing/convert", [&engine, &metrics](const HttpRequest& req) -> HttpResponse {
        metrics.increment_requests("convert");

        try {
            auto result = engine.convert_currency(req.body);
            return {200, result};
        } catch (const std::exception& e) {
            metrics.increment_errors("convert");
            return {400, std::string("{\"error\":\"") + e.what() + "\"}"};
        }
    });

    // List supported currencies
    server.route("GET", "/api/v1/pricing/currencies", [&engine](const HttpRequest& req) -> HttpResponse {
        return {200, engine.list_currencies()};
    });

    server.start();
    return 0;
}
