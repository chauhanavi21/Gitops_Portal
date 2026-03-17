#pragma once

#include <string>
#include <functional>
#include <unordered_map>
#include <sstream>
#include <thread>
#include <iostream>
#include <cstring>
#include <chrono>
#include <csignal>

#ifdef _WIN32
  #include <winsock2.h>
  #pragma comment(lib, "ws2_32.lib")
#else
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <unistd.h>
#endif

struct HttpRequest {
    std::string method;
    std::string path;
    std::string body;
    std::unordered_map<std::string, std::string> headers;
};

struct HttpResponse {
    int status = 200;
    std::string body;
    std::string content_type = "application/json";
};

std::string get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    char buf[64];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&time));
    return buf;
}

using RouteHandler = std::function<HttpResponse(const HttpRequest&)>;

/**
 * Minimal embedded HTTP server for the pricing engine.
 * Production would use a proper HTTP library (Crow, Drogon, cpp-httplib).
 */
class HttpServer {
public:
    explicit HttpServer(int port) : port_(port), running_(false) {}

    void route(const std::string& method, const std::string& path, RouteHandler handler) {
        routes_[method + " " + path] = std::move(handler);
    }

    void start() {
        running_ = true;

        int server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd < 0) {
            std::cerr << "Failed to create socket" << std::endl;
            return;
        }

        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port_);

        if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
            std::cerr << "Failed to bind to port " << port_ << std::endl;
            return;
        }

        listen(server_fd, 128);
        std::cout << "{\"timestamp\":\"" << get_timestamp()
                  << "\",\"level\":\"info\",\"message\":\"Server listening on port "
                  << port_ << "\"}" << std::endl;

        while (running_) {
            struct sockaddr_in client_addr{};
            socklen_t client_len = sizeof(client_addr);
            int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);

            if (client_fd < 0) continue;

            // Handle in a new thread (production: use thread pool)
            std::thread([this, client_fd]() {
                handle_connection(client_fd);
            }).detach();
        }

        close(server_fd);
    }

    void stop() { running_ = false; }

private:
    int port_;
    bool running_;
    std::unordered_map<std::string, RouteHandler> routes_;

    void handle_connection(int client_fd) {
        char buffer[8192] = {0};
        int bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);
        if (bytes_read <= 0) {
            close(client_fd);
            return;
        }

        auto request = parse_request(std::string(buffer, bytes_read));
        auto response = route_request(request);

        std::string http_response = build_response(response);
        write(client_fd, http_response.c_str(), http_response.size());
        close(client_fd);
    }

    HttpRequest parse_request(const std::string& raw) {
        HttpRequest req;
        std::istringstream stream(raw);
        stream >> req.method >> req.path;

        // Find body (after double newline)
        auto body_start = raw.find("\r\n\r\n");
        if (body_start != std::string::npos) {
            req.body = raw.substr(body_start + 4);
        }

        return req;
    }

    HttpResponse route_request(const HttpRequest& req) {
        std::string key = req.method + " " + req.path;
        auto it = routes_.find(key);
        if (it != routes_.end()) {
            return it->second(req);
        }
        return {404, "{\"error\":\"Not Found\"}"};
    }

    std::string build_response(const HttpResponse& resp) {
        std::string status_text;
        switch (resp.status) {
            case 200: status_text = "OK"; break;
            case 201: status_text = "Created"; break;
            case 400: status_text = "Bad Request"; break;
            case 404: status_text = "Not Found"; break;
            case 500: status_text = "Internal Server Error"; break;
            default: status_text = "Unknown"; break;
        }

        std::ostringstream oss;
        oss << "HTTP/1.1 " << resp.status << " " << status_text << "\r\n"
            << "Content-Type: " << resp.content_type << "\r\n"
            << "Content-Length: " << resp.body.size() << "\r\n"
            << "Connection: close\r\n"
            << "\r\n"
            << resp.body;
        return oss.str();
    }
};
