#pragma once

#include <string>
#include <unordered_map>
#include <stdexcept>
#include <sstream>
#include <cmath>
#include <mutex>

/**
 * PricingEngine — Core pricing logic
 * Thread-safe price calculation, discounts, and currency conversion.
 */
class PricingEngine {
public:
    PricingEngine() {
        // Initialize currency rates (relative to USD)
        currency_rates_["USD"] = 1.0;
        currency_rates_["EUR"] = 0.92;
        currency_rates_["GBP"] = 0.79;
        currency_rates_["JPY"] = 148.50;
        currency_rates_["CAD"] = 1.35;
        currency_rates_["AUD"] = 1.53;
        currency_rates_["CHF"] = 0.87;
        currency_rates_["INR"] = 83.10;

        // Discount tiers
        discount_tiers_[100.0]  = 0.00;  // < $100: no discount
        discount_tiers_[500.0]  = 0.05;  // $100-$500: 5%
        discount_tiers_[1000.0] = 0.10;  // $500-$1000: 10%
        discount_tiers_[5000.0] = 0.15;  // $1000-$5000: 15%
    }

    // Calculate total price for items
    // Input JSON: {"items": [{"price": 10.0, "quantity": 2}, ...], "currency": "USD"}
    std::string calculate_price(const std::string& body) {
        // Simple JSON parsing (production would use nlohmann/json or simdjson)
        double total = 0.0;
        std::string currency = "USD";

        // Parse items and sum
        auto items = parse_items(body);
        for (const auto& [price, qty] : items) {
            total += price * qty;
        }

        // Apply tax (configurable per region)
        double tax_rate = 0.08; // 8% default
        double tax = total * tax_rate;
        double grand_total = total + tax;

        // Convert if needed
        if (currency != "USD") {
            grand_total = convert(grand_total, "USD", currency);
        }

        std::ostringstream oss;
        oss << "{\"subtotal\":" << round_2(total)
            << ",\"tax\":" << round_2(tax)
            << ",\"tax_rate\":" << tax_rate
            << ",\"total\":" << round_2(grand_total)
            << ",\"currency\":\"" << currency << "\""
            << ",\"items_count\":" << items.size() << "}";
        return oss.str();
    }

    // Calculate bulk discount
    // Input JSON: {"amount": 500.0, "customer_tier": "gold"}
    std::string calculate_discount(const std::string& body) {
        double amount = parse_double(body, "amount");
        std::string tier = parse_string(body, "customer_tier");

        double discount_pct = 0.0;

        // Tier-based discount
        if (tier == "platinum") discount_pct = 0.20;
        else if (tier == "gold") discount_pct = 0.15;
        else if (tier == "silver") discount_pct = 0.10;
        else if (tier == "bronze") discount_pct = 0.05;

        // Volume-based discount (stacking)
        for (const auto& [threshold, pct] : discount_tiers_) {
            if (amount >= threshold) {
                discount_pct = std::max(discount_pct, pct);
            }
        }

        double discount_amount = amount * discount_pct;
        double final_amount = amount - discount_amount;

        std::ostringstream oss;
        oss << "{\"original_amount\":" << round_2(amount)
            << ",\"discount_percentage\":" << round_2(discount_pct * 100)
            << ",\"discount_amount\":" << round_2(discount_amount)
            << ",\"final_amount\":" << round_2(final_amount)
            << ",\"customer_tier\":\"" << tier << "\"}";
        return oss.str();
    }

    // Convert between currencies
    std::string convert_currency(const std::string& body) {
        double amount = parse_double(body, "amount");
        std::string from = parse_string(body, "from");
        std::string to = parse_string(body, "to");

        double result = convert(amount, from, to);

        std::ostringstream oss;
        oss << "{\"original_amount\":" << round_2(amount)
            << ",\"converted_amount\":" << round_2(result)
            << ",\"from\":\"" << from << "\""
            << ",\"to\":\"" << to << "\""
            << ",\"rate\":" << round_6(get_rate(from, to)) << "}";
        return oss.str();
    }

    std::string list_currencies() {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ostringstream oss;
        oss << "{\"currencies\":[";
        bool first = true;
        for (const auto& [code, rate] : currency_rates_) {
            if (!first) oss << ",";
            oss << "{\"code\":\"" << code << "\",\"rate_to_usd\":" << rate << "}";
            first = false;
        }
        oss << "]}";
        return oss.str();
    }

private:
    std::unordered_map<std::string, double> currency_rates_;
    std::map<double, double> discount_tiers_;
    mutable std::mutex mutex_;

    double convert(double amount, const std::string& from, const std::string& to) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (currency_rates_.find(from) == currency_rates_.end())
            throw std::runtime_error("Unknown currency: " + from);
        if (currency_rates_.find(to) == currency_rates_.end())
            throw std::runtime_error("Unknown currency: " + to);

        double usd_amount = amount / currency_rates_[from];
        return usd_amount * currency_rates_[to];
    }

    double get_rate(const std::string& from, const std::string& to) {
        std::lock_guard<std::mutex> lock(mutex_);
        return currency_rates_[to] / currency_rates_[from];
    }

    // Minimal JSON parsing helpers (production: use a proper JSON library)
    double parse_double(const std::string& json, const std::string& key) {
        auto pos = json.find("\"" + key + "\"");
        if (pos == std::string::npos) throw std::runtime_error("Missing field: " + key);
        pos = json.find(":", pos);
        return std::stod(json.substr(pos + 1));
    }

    std::string parse_string(const std::string& json, const std::string& key) {
        auto pos = json.find("\"" + key + "\"");
        if (pos == std::string::npos) return "";
        pos = json.find("\"", json.find(":", pos) + 1);
        auto end = json.find("\"", pos + 1);
        return json.substr(pos + 1, end - pos - 1);
    }

    std::vector<std::pair<double, int>> parse_items(const std::string& json) {
        std::vector<std::pair<double, int>> items;
        // Simple parsing: find all "price":X,"quantity":Y patterns
        size_t pos = 0;
        while ((pos = json.find("\"price\"", pos)) != std::string::npos) {
            double price = parse_double(json.substr(pos), "price");
            auto qty_pos = json.find("\"quantity\"", pos);
            int qty = 1;
            if (qty_pos != std::string::npos && qty_pos < json.find("}", pos)) {
                qty = static_cast<int>(parse_double(json.substr(qty_pos), "quantity"));
            }
            items.emplace_back(price, qty);
            pos = json.find("}", pos) + 1;
        }
        if (items.empty()) {
            items.emplace_back(0.0, 1); // default
        }
        return items;
    }

    static double round_2(double val) { return std::round(val * 100.0) / 100.0; }
    static double round_6(double val) { return std::round(val * 1000000.0) / 1000000.0; }
};
