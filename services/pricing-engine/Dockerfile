# Build stage
FROM gcc:13-bookworm AS builder

RUN apt-get update && apt-get install -y cmake

WORKDIR /app
COPY CMakeLists.txt .
COPY src/ ./src/
COPY tests/ ./tests/

RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc)

# Run tests during build
RUN cd build && ctest --output-on-failure

# Runtime stage — minimal image
FROM debian:bookworm-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

COPY --from=builder /app/build/pricing-engine /pricing-engine

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=3s CMD curl -f http://localhost:8080/healthz || exit 1

ENTRYPOINT ["/pricing-engine"]
