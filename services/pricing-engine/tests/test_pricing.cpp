/**
 * Tests for the PricingEngine
 */

#include <iostream>
#include <cassert>
#include <cmath>
#include "../src/pricing_engine.h"

void test_calculate_price() {
    PricingEngine engine;
    std::string input = R"({"items": [{"price": 10.0, "quantity": 2}, {"price": 5.0, "quantity": 3}]})";
    std::string result = engine.calculate_price(input);

    // subtotal should be 10*2 + 5*3 = 35.0
    // tax at 8% = 2.80
    // total = 37.80
    assert(result.find("\"subtotal\":35") != std::string::npos);
    assert(result.find("\"total\":37.8") != std::string::npos);
    std::cout << "[PASS] test_calculate_price" << std::endl;
}

void test_calculate_discount_gold() {
    PricingEngine engine;
    std::string input = R"({"amount": 1000.0, "customer_tier": "gold"})";
    std::string result = engine.calculate_discount(input);

    // Gold tier = 15%, volume also 10% but gold is higher → 15%
    assert(result.find("\"discount_percentage\":15") != std::string::npos);
    assert(result.find("\"final_amount\":850") != std::string::npos);
    std::cout << "[PASS] test_calculate_discount_gold" << std::endl;
}

void test_calculate_discount_no_tier() {
    PricingEngine engine;
    std::string input = R"({"amount": 50.0, "customer_tier": "none"})";
    std::string result = engine.calculate_discount(input);

    // No tier, under $100 → 0% discount
    assert(result.find("\"discount_percentage\":0") != std::string::npos);
    assert(result.find("\"final_amount\":50") != std::string::npos);
    std::cout << "[PASS] test_calculate_discount_no_tier" << std::endl;
}

void test_convert_currency() {
    PricingEngine engine;
    std::string input = R"({"amount": 100.0, "from": "USD", "to": "EUR"})";
    std::string result = engine.convert_currency(input);

    assert(result.find("\"from\":\"USD\"") != std::string::npos);
    assert(result.find("\"to\":\"EUR\"") != std::string::npos);
    assert(result.find("\"converted_amount\":92") != std::string::npos);
    std::cout << "[PASS] test_convert_currency" << std::endl;
}

void test_list_currencies() {
    PricingEngine engine;
    std::string result = engine.list_currencies();

    assert(result.find("\"USD\"") != std::string::npos);
    assert(result.find("\"EUR\"") != std::string::npos);
    assert(result.find("\"JPY\"") != std::string::npos);
    std::cout << "[PASS] test_list_currencies" << std::endl;
}

int main() {
    std::cout << "Running pricing engine tests..." << std::endl;

    test_calculate_price();
    test_calculate_discount_gold();
    test_calculate_discount_no_tier();
    test_convert_currency();
    test_list_currencies();

    std::cout << "\nAll tests passed!" << std::endl;
    return 0;
}
