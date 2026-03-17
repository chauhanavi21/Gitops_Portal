cmake_minimum_required(VERSION 3.20)
project(pricing-engine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find packages
find_package(Threads REQUIRED)

# Main executable
add_executable(pricing-engine
    src/main.cpp
    src/http_server.cpp
    src/pricing_engine.cpp
    src/metrics.cpp
)

target_include_directories(pricing-engine PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_link_libraries(pricing-engine PRIVATE Threads::Threads)

# Tests
enable_testing()
add_executable(pricing-tests
    tests/test_pricing.cpp
    src/pricing_engine.cpp
)
target_include_directories(pricing-tests PRIVATE ${CMAKE_SOURCE_DIR}/src)
add_test(NAME PricingTests COMMAND pricing-tests)
