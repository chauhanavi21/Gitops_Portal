#pragma once

#include <string>
#include <atomic>
#include <sstream>
#include <mutex>
#include <unordered_map>
#include <vector>

/**
 * Prometheus-compatible metrics for the pricing engine.
 * Exposes counters and histograms in Prometheus text format.
 */
class Metrics {
public:
    explicit Metrics(const std::string& service_name) : service_name_(service_name) {}

    void increment_requests(const std::string& operation) {
        std::lock_guard<std::mutex> lock(mutex_);
        request_counts_[operation]++;
    }

    void increment_errors(const std::string& operation) {
        std::lock_guard<std::mutex> lock(mutex_);
        error_counts_[operation]++;
    }

    void observe_duration(const std::string& operation, double seconds) {
        std::lock_guard<std::mutex> lock(mutex_);
        duration_sums_[operation] += seconds;
        duration_counts_[operation]++;
    }

    std::string serialize() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ostringstream oss;

        // Request counts
        oss << "# HELP pricing_engine_requests_total Total pricing requests\n";
        oss << "# TYPE pricing_engine_requests_total counter\n";
        for (const auto& [op, count] : request_counts_) {
            oss << "pricing_engine_requests_total{operation=\"" << op << "\"} " << count << "\n";
        }

        // Error counts
        oss << "# HELP pricing_engine_errors_total Total pricing errors\n";
        oss << "# TYPE pricing_engine_errors_total counter\n";
        for (const auto& [op, count] : error_counts_) {
            oss << "pricing_engine_errors_total{operation=\"" << op << "\"} " << count << "\n";
        }

        // Duration (simplified — sum and count for rate computation)
        oss << "# HELP pricing_engine_duration_seconds Request duration\n";
        oss << "# TYPE pricing_engine_duration_seconds summary\n";
        for (const auto& [op, sum] : duration_sums_) {
            auto it = duration_counts_.find(op);
            int count = it != duration_counts_.end() ? it->second : 0;
            oss << "pricing_engine_duration_seconds_sum{operation=\"" << op << "\"} " << sum << "\n";
            oss << "pricing_engine_duration_seconds_count{operation=\"" << op << "\"} " << count << "\n";
        }

        return oss.str();
    }

private:
    std::string service_name_;
    mutable std::mutex mutex_;
    std::unordered_map<std::string, int> request_counts_;
    std::unordered_map<std::string, int> error_counts_;
    std::unordered_map<std::string, double> duration_sums_;
    std::unordered_map<std::string, int> duration_counts_;
};
