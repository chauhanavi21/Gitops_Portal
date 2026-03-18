cmake_minimum_required(VERSION 3.20)
project(${{ values.name }} VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD ${{ values.cppStandard }})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(${PROJECT_NAME}
    src/main.cpp
)

target_include_directories(${PROJECT_NAME} PRIVATE src)

# Tests
enable_testing()
add_executable(${PROJECT_NAME}_tests tests/test_main.cpp)
target_include_directories(${PROJECT_NAME}_tests PRIVATE src)
add_test(NAME ${PROJECT_NAME}_tests COMMAND ${PROJECT_NAME}_tests)
